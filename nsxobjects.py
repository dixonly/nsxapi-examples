from __future__ import print_function
import connections
import uuid
import json
import ssl
import OpenSSL
import re
import vcenter

class Nsx_object(object):
    '''
    Base class for all NSX resources
    '''
    def __init__(self, mp, listApi=None,
                 domain='default',
                 site='default',
                 enforcementPoint='default'):
        self.mp=mp
        self.listApi = listApi
        # switch to mp values for these in GC
        self.domain=mp.domain
        self.site=mp.site
        self.ep=mp.enforcement
            
    def __pageHandler(self, api):
        '''
        Handle multipage results by merging them into one dictionary
        '''
        firstLoop=True
        cursor = None
        result={}

        while firstLoop or cursor:
            fistLoop = False
            if '?' in api:
                url = '%s&cursor=%s' % (api,cursor) if cursor else api
            else:
                url = '%s?cursor=%s' % (api,cursor) if cursor else api

            r = self.mp.get(api=url, verbose=False,trial=False)
            if result:
                result['results'].extend(r['results'])
            else:
                result = r
            if 'cursor' not in r:
                return result
            elif int(r['cursor']) == r['result_count']:
                return result
            else:
                cursor=r['cursor']
                
    def jsonPrint(self, data, header=None, indent=4, brief=False):
        '''
        Takes dictionary and print output to stdout
        '''
        if data and not isinstance(data,dict):
            print("Data not a valid dictionary")
            return
        if header and not brief:
            print(header)
        if data:
            if 'results' not in data.keys() or not brief:
                print(json.dumps(data,indent=indent))
            else:
                if header:
                    print("%30s %30s %-s" %("name","id","path"))
                    print("%30s %30s %-s" %("----------","----------", "----------"))
                for i in data['results']:
                    print("%30s %30s %-s" %(i['display_name'],
                                            i['id'],
                                            i['path'] if 'path' in i.keys() else "-"))


    def removeStatusFromSearchList(self, data, fields=["status"]):
        if 'results' not in data:
            return data
        for d in data['results']:
            for f in fields:
                if f in d:
                    del d[f]
        return data
    
    def list(self, api=None, brief=False, display=True, 
             removeSearch=False, searchFields=['status'],
             header=None):
        '''
        Returns of a list of NSX objects with api.  The return result will combine
        multipage results into one
        '''
        if not api:
            if self.listApi:
                api = self.listApi
            else:
                print("Calling list() without providing API")
                return None
        r = self.__pageHandler(api=api)
        if removeSearch and '/search/query' in api:
            r = self.removeStatusFromSearchList(data=r, fields=searchFields)
        if display:
            print("API: GET %s" %self.mp.normalizeGmLmApi(api))
            self.jsonPrint(data=r, brief=brief, header=header)
        return r
        
    def findByName(self, name, field='display_name', removeSearch=True,
                   api=None, data=None, display=True,brief=False):
        '''
        Find an nsxobject by display_name
        '''
        if not data:
            if not api:
                if self.listApi:
                    api=self.listApi
            if not api:
                print ("Calling list with no API specified")
                return None
            data = self.list(api=api,display=False, removeSearch=removeSearch)
        obj = None
        for o in data['results']:
            if o[field] == name:
                obj = o
                break
        if obj and display:
            if brief:
                print("%d. Name: %s" %(i,obj[field]))
                print("    Id: %s" %(obj['id']))
            else:
                self.jsonPrint(data=obj)
        return obj
    
    def findById(self, id, api=None, data=None, display=True,brief=False, removeSearch=True):
        '''
        Find an nsxobject by id
        '''
        if not data:
            if not api:
                if self.listApi:
                    api=self.listApi
            if not api:
                print ("Calling list with no API specified")
                return None
        data = self.list(api=api,display=False, removeSearch=removeSearch)
        obj = None

        for o in data['results']:
            if o['id'] == id:
                obj = o
                break
        if obj and display:
            if brief:
                print("%d. Name: %s" %(i,obj['display_name']))
                print("   Id: %s" %(obj['id']))
            else:
                self.jsonPrint(data=obj)
        return obj

    def getFederationSpan(self, name, api=None,display=True):
        r = self.getPathByName(name=name, api=api, display=False)
        if not r:
            print("Object %s not found" %name)
            return None
        r = self.mp.get(api='/policy/api/v1/global-infra/span?intent_path='+r)
        if display:
            self.jsonPrint(r)
        return r
        
    def getIdByName(self, name, api=None,data=None,display=True):
        '''
        Return the ID of an object found by display_name
        '''
        r = self.findByName(name=name, api=api,data=data,display=False)
        if r:
            return r['id']
        
    def getPathByName(self, name, api=None, data=None, display=True):
        '''
        Return the Policy Path of an object found by display_name
        '''
        if not api:
            api=self.listApi

        obj = self.findByName(api=api,name=name, data=data, display=False)
        if obj:
            if display:
                print(obj['path'])
            return obj['path']
        return None

    def getPathById(self, id, api=None, data=None, display=True):
        '''
        Return the Policy path of an object found by id
        '''
        if not api:
            api=self.listApi

        obj = self.findById(api=api,id=id,data=data, display=False)
        if obj:
            if display:
                print(obj['path'])
            return obj['path']
        return None

    def delete(self, name, force=False, display=True):
        '''
        Delete an nsxojbect found by display_name
        '''
        if self.listApi.startswith('/policy'):
            oPath=self.getPathByName(name=name, display=False)
            if not oPath:
                print("%s not found for delete" % name)
                return
            api='/policy/api/v1%s' % oPath
            if force:
                api="%s?force=true" %(api)
            self.mp.delete(api=api,verbose=True, codes=[200])
        else:
            obj = self.findByName(name=name, display=False)
            if not obj:
                print("%s not found for delete" % name)
                return
            api="%s/%s" % (self.listApi, obj['id'])
            if force:
                api="%s?force=true" %(api)
            self.mp.delete(api=api, verbose=True,codes=[200])

    def addTag(self, name, tags, replace=False):
        T=Tags(mp=self.mp)
        newTags = T.createFromSpec(spec=tags)
        if not newTags:
            print("New tags failed from spec: %s" %tags)
            return False
        
        obj = self.findByName(name=name, display=False)
        if not obj:
            print("%s not found" %name)
            return False
        if 'path' not in obj:
            print("%s is not a Policy object" %name)
            return False
        
        if replace or 'tags' not in obj:
            obj['tags'] = newTags
        else:
            if 'tags' in obj:
                obj['tags'].extend(newTags)

        api='/policy/api/v1%s'%obj['path']
        # Let's use PUT just in case we run into collisions, espec
        # since this is a generic implementation
        return self.mp.put(api=api, data=obj, verbose=True,codes=[200])

    def delTag(self, name, tags, wipe=False):
        obj = self.findByName(name=name, display=False)
        if not obj:
            print("%s not found" %name)
            return False
        if 'path' not in obj:
            print("%s is not a Policy object" %name)
            return False

        T=Tags(mp=self.mp)
        newTags=T.createFromSpec(spec=tags)
        if wipe or 'tags' not in obj:
            obj['tags'] = []
        else:
            obj['tags'] = T.removeTags(obj['tags'], newTags)

        api='/policy/api/v1%s'%obj['path']
        # Let's use PUT just in case we run into collisions, espec
        # since this is a generic implementation
        return self.mp.put(api=api, data=obj, verbose=True,codes=[200])
            
    def getRealizationEntities(self, name=None,path=None,display=True):
        '''
        Display/return the list of realized entities for a Policy object
        '''
        if not path and not name:
            print("Must either supply entity path or name to get realization status")
            return None


        if not path and name:
            path=self.getPathByName(name=name,display=False)
            if not path:
                print("Entity with name %s not found to retrieve realization" %name)
                return None

        api="/policy/api/v1/infra/realized-state/realized-entities?intent_path=%s"%path
        r = self.mp.get(api=api, verbose=display, display=display)
        return r

    def getRealizationStatus(self, name=None, path=None,display=True):
        '''
        Display/return the realization state of a Policy object
        '''
        if not path and not name:
            print("Must either supply entity path or name to get realization status")
            return None


        if not path and name:
            path=self.getPathByName(name=name,display=False)
            if not path:
                print("Entity with name %s not found to retrieve realization" %name)
                return None

        api="/policy/api/v1/infra/realized-state/status?intent_path=%s"%path
        r = self.mp.get(api=api)
        if display:
            self.jsonPrint(r)
        return r

    def getPathByTypeAndName(self, name, types, display=True):
        '''
        Return the Policy path of an object found by display_name, iterating
           through a list ob nsxobject types for the search
        name = name of the object
        types = list of types to search through
        '''

        for t in types:
            obj=t(mp=self.mp)
            p = obj.getPathByName(name=name, display=display)
            if p:
                return p
        
        return None


class Cluster(Nsx_object):
    '''
    NSX Manager cluster
    '''
    
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi = '/api/v1/cluster/nodes'
        if not self.mp.global_gm:
            self.clusterid = self.info(display=False)['cluster_id']

    def info(self, display=True):
        restUrl = '/api/v1/cluster'
        r= self.mp.get(restUrl,verbose=False)
        if display: self.jsonPrint(r)
        return r

    def listIn(self, brief=False,display=True):
        return self.info(display=display)

    def findByNameIn(self, name, data=None,display=True, api=None):
        cluster=self.listIn(display=False)
        found=None
        for i in cluster['nodes']:
            if i['fqdn'] == name:
                found=i
                break
            dn = i['fqdn'].split('.')
            if dn[0] == name:
                found=i
                break
        if found and display:
            self.jsonPrint(i)
        return found
    
    def detachNode(self, name, graceful=False, force=False, ignoreRepo=False):
        n = self.findByNameIn(name=name, display=False)
        if not n:
            print("Node %s not found" %name)
            return False
        api='/api/v1/cluster/%s?action=remove_node' % n['node_uuid']
        if graceful:
            api=api.join('&graceful-shutdown=true')
        if force:
            api=api.join('&force=true')
        if ignoreRepo:
            api=api.join('&ignore-repository-ip-check=true')

        self.mp.post(api=api,data=None, verbose=True,codes=[200])
        
            
            
        
    def getFqdnMode(self,display=False):
        r =  self.mp.get(api='/api/v1/configs/management')
        if display:
            self.jsonPrint(r)
        return r
    
    def setFqdnMode(self):
        fmode=self.getFqdnMode(display=False)
        fmode['publish_fqdns'] = True
        self.mp.put(api='/api/v1/configs/management',
                    data=fmode,
                    verbose=True)

    def unsetFqdnMode(self):
        fmode=self.getFqdnMode(display=False)
        fmode['publish_fqdns'] = False
        self.mp.put(api='/api/v1/configs/management',
                    data=fmode,
                    verbose=True)

    def createCluster(self,primary,secondaries):
        primary.getThumbprint(refresh=True)
        primary.getClusterInfo()
        for s in secondaries:
            s.getClusterInfo()
            data={}
            data['certficate_sha256_thumbprint'] = primary.getThumbprint()
            data['cluster_id']=primary.getClusterId()
            data['ip_address'] = primary.getIpAddress()
            #data['port'] = 443
            data['username'] = primary.getAdminUser()
            data['password'] = primary.getAdminPassword()

            restUrl='/api/v1/cluster?action=join_cluster'
            r = s.mp.post(api=restUrl,data=data, verbose=True,codes=[200])

    def nodes(self,display=True):
        restUrl = '/api/v1/cluster/nodes'
        cluster=self.mp.get(restUrl, verbose=True)

        for i in cluster['results']:
            '''
            self.walk_and_replace_dict_keyval(d=i,
                    name='certificate', val='_snipped_')
            '''
            self.jsonPrint(i,indent=4)

    def health(self,display=True):
        r = self.mp.get(api='/api/v1/reverse-proxy/node/health',codes=[200])
        if display:
            self.jsonPrint(r)
        return r
        
    def status(self):
        restUrl = '/api/v1/cluster/status'
        r = self.mp.get(api=restUrl, verbose=True)
        self.jsonPrint(r,indent=4)
    def cbmStatus(self):
        restUrl='/api/v1/cluster-manager/status'
        r = self.mp.get(api=restUrl)
        self.jsonPrint(r,indent=4)
    def getClusterIp(self):
        restUrl='/api/v1/cluster/api-virtual-ip'
        r=self.mp.get(api=restUrl)
        self.jsonPrint(r,indent=4)

    def clearClusterIp(self):
        restUrl='/api/v1/cluster/api-virtual-ip?action=clear_virtual_ip'
        r = self.mp.post(api=restUrl)
        self.jsonPrint(r,indent=4)

    def setClusterIp(self,addr):
        restUrl='/api/v1/cluster/api-virtual-ip?action=set_virtual_ip&ip_address=%s' %addr
        r = self.mp.post(api=restUrl)
        self.jsonPrint(r,indent=4)


    def setCertificate(self, certName):
        certObj = Certificate(mp=self.mp)
        cert = certObj.findByName(api='/api/v1/trust-management/certificates',
                                  name=certName, display=False)
        if not cert:
            print("Certificate %s not found" %certName)
        else:
            restUrl='/api/v1/cluster/api-certificate?action=set_cluster_certificate&certificate_id=%s' %cert['id']
            r = self.mp.post(api=restUrl,verbose=True, codes=[200])


    def getCertificate(self, display=True):
        r = self.mp.get(api='/api/v1/cluster/api-certificate')
        if display:
            self.jsonPrint(r)

    def clearCertificate(self, certName):
        cert = self.findByName(restUrl='/api/v1/trust-management/certificates',
                               name=certName, display=False)
        if not cert:
            print("Certificate %s not found" %certName)
        else:
            restUrl='/api/v1/cluster/api-certificate?action=clear_cluster_certificate&certificateId=%s' %cert['id']
            r = self.mp.post(api=restUrl,verbose=True, codes=[200])

    def getPartialPatch(self):
        self.mp.get(api='/policy/api/v1/system-config/nsx-partial-patch-config',
                    verbose=True, display=True)
        
    def setPartialPatch(self, val):
        api="/policy/api/v1/system-config/nsx-partial-patch-config"
        data=self.mp.get(api=api)

        if val:
            data['enable_partial_patch'] = True
        else:
            data['enable_partial_patch'] = False

        self.mp.patch(api=api, data=data, verbose=True, codes=[200])


    def setPassword(self, username, oldpassword, newpassword, node=None, expiry=None, display=True):

        tn = self.findByName(name=node, display=False)
        if not tn:
            print("Node %s not found" %node)
            return False
        uapi = '/api/v1/cluster/%s/node/users' %tn[' id']
        user = self.findByName(name=username, field='username',
                               api=uapi, display=False)
        if not user:
            print("Username %s not found on TN %s" % (username, node))
            return False
        userid=user['userid']
        user['old_password'] = oldpassword
        user['password'] = newpassword

        api="%s/%d" %(uapi,userid)
        r = self.mp.put(api=api, data=user, codes=[200])
        if display:
            self.jsonPrint(r)
        return r
            
        
        
class GlobalConfigs(Nsx_object):
    '''
    Class for switch and routing GlobalConfigs
    '''
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/api/v1/global-configs'
        self.listPolicyApi='/policy/api/v1/infra/global-config'
            
    def updateSwitchingConfig(self, name=None,desc=None,mtu=None,replication=None):
        self.listApi ='/api/v1/global-configs/SwitchingGlobalConfig'
        data=self.list(display=False)


        changed = False
        if name:
            data['display_name'] = name
            changed = True
        if desc:
            data['description'] = desc
            changed = True
        if mtu:
            data['physical_uplink_mtu'] = mtu
            changed = True
            if 'remote_tunnel_physical_mtu' in data.keys():
                # this check should make this valid for pre-GC
                data['remote_tunnel_physical_mtu'] = mtu
        if replication != None and replication != data['global_replication_mode_enabled']:
            data['global_replication_mode_enabled'] = replication
            changed = True

        if changed:
            r = self.mp.put(api=self.listApi, data=data, verbose=True, codes=[200])
        else:
            print("No change submitted, no-op")

    def updateGlobalConfigs(self, name=None, desc=None,
                            arp_limit=None,
                            fips=None,
                            l3mode=None,
                            mtu=None,
                            uplink_threshold_mtu=None,
                            allow_vdr_change=None,
                            vdrMac=None,
                            vdrNested=None):
        self.listApi="/policy/api/v1/infra/global-config"
        data=self.list(display=False)

        changed = False
        if name:
            data['display_name'] = name
            changed = True
        if desc:
            data['description'] = desc
            changed = True

        if arp_limit:
            data['arp_limit_per_gateway'] = arp_limit
            changed = True

        if fips:
            if not 'fips' in data.keys():
                data['fips'] = {}
            fipsData=data['fips']
            if 'lb_fips_enabled' in fipsData.keys():
                if fipsData['lb_fips_enabled']:
                    fipsData['lb_fips_enabled'] = False
                else:
                    fipsData['lb_fips_enabled'] = True
            changed=True

        if l3mode:
            data['lw_forwarding_mode'] = l3mode
            changed=True

        if mtu:
            data['mtu'] = mtu
            changed=True
            
        if uplink_threshold_mtu:
            data['uplink_mtu_threshold'] = uplink_threshold_mtu
            changed=True

        if allow_vdr_change:
            if data['allow_changing_vdr_mac_in_use']:
                data['allow_changing_vdr_mac_in_use'] = False
            else:
                data['allow_changing_vdr_mac_in_use'] = True
            changed = True

        if vdrMac:
            data['vdr_mac'] = vdrMac
            changed=True
        if vdrNested:
            data['vdr_mac_nested'] = vdrNested
            changed = True

        if changed:
            r = self.mp.patch(api=self.listApi, data=data, verbose=True, codes=[200])
        else:
            print("No changes submitted, here's current config")
            self.jsonPrint(data)
        
                            

    def updateRoutingConfig(self, name=None, desc=None, mtu=None, l3mode=None):
        self.listApi ='/api/v1/global-configs/RoutingGlobalConfig'
        data=self.list(display=False)


        changed = False
        if name:
            data['display_name'] = name
            changed = True
        if desc:
            data['description'] = desc
            changed = True
        if mtu:
            data['logical_uplink_mtu'] = mtu
            changed = True
        if l3mode:
            data['l3_forwarding_mode'] = l3mode
            changed = True


        if changed:
            r = self.mp.put(api=self.listApi, data=data,verbose=True, codes=[200])
        else:
            print("No change submitted, no-op")
        

class TransportZone(Nsx_object):
    '''
    Read only class to search TZs.  CRUD on TZ is done via MP API
    '''
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        # use MP APIs for now, because the Policy just lists policy
        # entities without them really being useful
        #self.listApi=('/policy/api/v1/infra/sites/%s/enforcement-points/%s/transport-zones'
        #              %(self.site, self.ep))
        self.listApi='/api/v1/transport-zones'
   
    def config(self,name,transportType,isdefault, teaming=None,hswname=None,desc=None):
        # hswname is being marked deprecated in G. defaults to nsxDefaultHostSwitch
        # this was always optional - but G UI now doesn't even show this anymore
        api='/api/v1/transport-zones'
        tz = self.findByName(name=name, display=False)
        if tz:
            data=tz
            api="%s/%s" %(api, tz['id'])
        else:
            data={}
        data['display_name'] = name
        if desc:
            data['description'] = desc
        if hswname:
            data['host_switch_name'] = hswname
        data['is_default'] = isdefault
        data['transport_type'] = transportType
        if teaming:
            data['uplink_teaming_policy_names'] = teaming
        if not tz:
            self.mp.post(api, data=data,verbose=True, codes=[201])
        else:
            self.mp.put(api, data=data, verbose=True, codes=[200])

    def setNested(self, name, enable, disable):
        api='/api/v1/transport-zones'
        tz = self.findByName(name=name, display=False)
        if not tz:
            print("Transport Zone %s not found" % name)
            return False
        api="%s/%s" %(api, tz['id'])
        if enable:
            tz['nested_nsx'] = True
        if disable:
            tz['nested_nsx'] = False
        self.mp.put(api, data=tz, verbose=True, codes=[200])
            
    def getTransportNodeStatusReport(self):
        api='/api/v1/transport-zones/transport-node-status-report'
        self.mp.setHeader('Accept', 'application/octet-stream')
        r=self.mp.get(api=api)
        self.print(r)
        
class EnforcementPoints(Nsx_object):
    '''
    Read only class to search enforcement points.  There's currently only
    one enforcement point called 'default' per NSX deployment
    '''
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/infra/sites/%s/enforcement-points' %self.site

    def fullSync(self, site='default', ep='default'):
        ePath=self.getPathByName(name=ep, display=False)
        if not ePath:
            print("Enforcement point %s not found" % ep)
            return False
        api='/policy/api/v1' + ePath + '?action=full-sync'
        self.mp.post(api=api, data=None,verbose=True, codes=[200])
    def reload(self, site='default', ep='default'):
        ePath=self.getPathByName(name=ep, display=False)
        if not ePath:
            print("Enforcement point %s not found" % ep)
            return False
        api='/policy/api/v1' + ePath + '?action=reload'
        self.mp.post(api=api, data=None,verbose=True, codes=[200])

class Sites(Nsx_object):
    '''
    Read only class to search sites.  For 2.4, use only 'default'
    '''
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/infra/sites'

class EdgeCluster(Nsx_object):
    '''
    Read only class to search Edge Clusters.  CRUD is via MP API
    '''
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi=('/policy/api/v1/infra/sites/%s/enforcement-points/%s/edge-clusters'
                      % (self.site, self.ep))
    def setInterSite(self, name, value):
        ec=self.findByName(name=name, api='/api/v1/edge-clusters', display=False)
        if not ec:
            print("Edgecluster %s not found" %name)
            return None
        ec['enable_inter_site_forwarding'] = value
        api='/api/v1/edge-clusters/%s' % ec['id']
        self.mp.put(api=api,data=ec,verbose=True, codes=[200])

    def getInterSiteStatus(self, name, display=True):
        ec=self.findByName(name=name, api='/api/v1/edge-clusters', display=False)
        if not ec:
            print("Edgecluster %s not found" %name)
            return None

        api='/api/v1/edge-clusters/%s/inter-site/status' % ec['id']
        return self.mp.get(api=api, verbose=display, display=display)
    
    def enableFD(self, name):
        ec=self.findByName(name=name, api='/api/v1/edge-clusters')
        if not ec:
            print("Edgecluster %s not found" %name)
            return None
        fdrule={}
        fdrule['action'] = {'action_type': 'AllocationBasedOnFailureDomain', 'enabled': True}
        ec['allocation_rules'] = [fdrule]
        self.mp.put(api='/api/v1/edge-clusters/%s'%ec['id'],
                    data=ec, verbose=True, codes=[200])
        
            

    def configEdgeClusterProfile(self, name, realloc=30,
                                 bfdint=1000, bfddead=3,bfdhop=1):
        data={}
        data['display_name'] = name
        data['resource_type'] = 'EdgeHighAvailabilityProfile'
        data['bfd_probe_interval'] = bfdint
        data['bfd_declare_dead_multiple'] = bfddead
        data['bfd_allowed_hops'] = bfdhop
        data['standby_relocation_config'] = {'standby_relocation_threshold': realloc}
        self.mp.post(api='/api/v1/cluster-profiles', data=data,
                     verbose=True,codes=[201])

    def setHaProfile(self, cluster, ha):
        ec=self.findByName(name=cluster, api='/api/v1/edge-clusters', display=False)
        if not ec:
            print("EdgeCluster %s not found" %cluster)

        if ha:
            ec['cluster_profile_bindings'] = []
            for h in ha:
                p = self.findByName(api='/api/v1/cluster-profiles', name=h, display=False)
                if not p:
                    print("Edge Cluster profile %s not found" % h)
                    return None
                else:
                    prof = {}
                    prof['profile_id'] = p['id']
                    prof['resource_type'] = p['resource_type']
                    
                    ec['cluster_profile_bindings'].append(prof)
        self.mp.put(api='/api/v1/edge-clusters/%s'%ec['id'],
                    data=ec, verbose=True, codes=[200])
        
    def config(self, name, members, fd = False, inter=False, ha = None, display=True):
        data={}
        data['display_name'] = name
        T = TransportNode(mp=self.mp)
        print("Inter is %s" %inter)
        data['enable_inter_site_forwarding'] = inter
        data['members'] = []
        for m in members:
            tn = T.findByName(name=m, display=False)
            if not tn:
                print("Transport node %s not found" % tn)
                return None
            em = {}
            em['transport_node_id'] = tn['id']
            data['members'].append(em)
        if fd:
            data['allocation_rules'] = [{'action': {'action_type': 'AllocationBasedOnFailureDomain', 'enabled': True}}]

        if ha:
            data['cluster_profile_bindings'] = []
            for h in ha:
                p = self.findByName(api='/api/v1/cluster-profiles', name=h, display=False)
                if not p:
                    print("Edge Cluster profile %s not found" % h)
                    return None
                else:
                    prof = {}
                    prof['profile_id'] = p['id']
                    prof['resource_type'] = p['resource_type']
                    
                    data['cluster_profile_bindings'].append(prof)
        api='/api/v1/edge-clusters'
        self.mp.post(api=api,data=data,verbose=True,codes=[201])
          
    def getDetail(self, name=False, display=True):
        if name:
            self.findByName(api='/api/v1/edge-clusters', name=name, display=display)
        else:
            self.list(api='/api/v1/edge-clusters', display=display)
            
            
class Edge(Nsx_object):
    '''
    Class to list/find edge nodes, within an edgecluster ec if specified
    '''
    def __init__(self, mp, site='default', enforcementPoint='default', ec=None):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/search/query?query=resource_type:PolicyEdgeNode'
        # This doesn't work for GM
        #self.listApi='/policy/api/v1/search/query?query=resource_type:PolicyEdgeNode AND path:\/infra\/sites\/default\/enforcement\-points\/default\/edge\-clusters\/*'
        
    def listOld(self, ec=None, display=True):
        # Old list function - deprecating in favor of search
        # Note that the search API returns two nodes currently (early days of 3.0.2
        # so saving this for uniqueness instead of making another wrapper around search
        # ***still leaving in place...the default list with additional path query now
        # doesn't return duplicates anymore
        if ec:
            E = EdgeCluster(mp=self.mp)
            #print("edgecluster name is %s" %ec)
            ecPath = E.getPathByName(name=ec, display=False)
            if not ecPath:
                raise ValueError("EdgeCluster %s not vallid" %ec)
            api='/policy/api/v1%s/edge-nodes' % ecPath
            return super(self.__class__, self).list(api=api,display=display)
        else:
            edges={}
            edges['results'] = []
            edges['result_count'] = 0
            ec = EdgeCluster(mp=self.mp)
            ecList = ec.list(display=False)
            for e in ecList['results']:
                r = self.listOld(ec=e['display_name'],display=False)
                if r['result_count'] > 0:
                    edges['result_count']+=r['result_count']
                    edges['results']+=r['results']
            if display:
                self.jsonPrint(edges)
            return edges
    def getNamefromPath(self, path, ec=None):
        edges=self.list(ec=ec, display=False)
        for e in edges['results']:
            if e['path'] == path:
                return e['display_name']

    def getTeps(self, name=None, display=True):
        TN=TransportNode(mp=self.mp, tntype='EdgeNode')
        TN.getTeps(name=name,display=display)

            
    def getRTeps(self, names=None, display=True):
        edges=self.list(api='/api/v1/transport-nodes?node_types=EdgeNode', display=False)
        for e in edges['results']:
            if names and e['display_name'] not in names:
                continue
            print("Edge %s:" %e['display_name'])
            api='/api/v1/transport-nodes/%s/state' % e['id']
            data=self.mp.get(api=api, verbose=False, display=False)
            if not 'remote_tunnel_endpoint_state' in data:
                print("   None")
                continue
            for i in data['remote_tunnel_endpoint_state']['endpoints']:
                print("   %s / %s gw: %s mac: %s" % (i['ip'],
                                                     i['subnet_mask'],
                                                     i['default_gateway'],
                                                     i['mac']))
        

    def getInterSiteBgpNeighbors(self, name, display=True):
        e = self.findByName(name=name,display=False)
        api='/api/v1/transport-nodes/%s/inter-site/bgp/neighbors' %e['nsx_id']
        return self.mp.get(api=api,verbose=display,display=display)
    
    def getInterSiteBgpSummary(self, name, display=True):
        e = self.findByName(name=name,display=False)
        api='/api/v1/transport-nodes/%s/inter-site/bgp/summary' %e['nsx_id']
        return self.mp.get(api=api,verbose=display,display=display)

    def getInterSiteStats(self, name, display=True):
        e = self.findByName(name=name,display=False)
        api='/api/v1/transport-nodes/%s/inter-site/statistics' %e['nsx_id']
        return self.mp.get(api=api,verbose=display,display=display)
    
    
    def getState(self, name, display=True):
        TN=TransportNode(mp=self.mp, tntype='EdgeNode')
        TN.getState(name=name, display=display)
        
    def deployEdge(self, name, size, tznames, enableSsh, allowRootSsh,
                   dns, hostname, ntp, domains, rootpw, clipw, auditpw,
                   vc, cluster, storage, fpe0, fpe1, fpe2, mgmtNet, gateway,
                   mgmtIp,mgmtMask, uplink, ippool, nics,
                   ntype="vc",
                   lldp=None, host=None, display=True):

        CM = ComputeManager(mp=self.mp)
        vcObj = CM.findByName(name=vc, display=False)
        if not vcObj:
            print("VCenter %s not found" %vc)
            return None
        
        cId = CM.findClusterId(cluster=cluster, vc=vc, display=False)
        if not cId:
            print("Cluster %s not found on vc %s" %(cluster, vc))
            return None

        sObj = CM.findStorage(cluster=cluster, name=storage, vc=vc, display=False)
        if not sObj:
            print("Storage %s not found on cluster %s on vc %s"%(storage, cluster, vc))
            return None
        else:
            sId = sObj['target_id']

        dataNets=[]

        if ntype != 'opaque':
            #fp-eth0
            eObj = CM.findNetwork(cluster=cluster, name=fpe0, vc=vc,
                                  storage=sId, display=False)
            if not eObj:
                print("Network %s not found on cluster %s on vc %s" %(fpe0, cluster, vc))
                return None
            else:
                dataNets.append(eObj['network_resource']['target_id'])

            # fp-eth1
            eObj = CM.findNetwork(cluster=cluster, name=fpe1, vc=vc,
                                  storage=sId, display=False)
            if not eObj:
                print("Network %s not found on cluster %s on vc %s" %(fpe1, cluster, vc))
                return None
            else:
                dataNets.append(eObj['network_resource']['target_id'])

            # fp-eth2
            eObj = CM.findNetwork(cluster=cluster, name=fpe2, vc=vc,
                                  storage=sId, display=False)
            if not eObj:
                print("Network %s not found on cluster %s on vc %s" %(fpe2, cluster, vc))
                return None
            else:
                dataNets.append(eObj['network_resource']['target_id'])
        else:
            S=Segments(mp=self.mp)
            eObj = S.findByName(name=fpe0, api='/api/v1/logical-switches', display=False)
            if not eObj:
                print("Network %s not found on cluster %s on vc %s" %(fpe0, cluster, vc))
                return None
            else:
                dataNets.append(eObj['id'])

            # fp-eth1
            eObj = S.findByName(name=fpe1, api='/api/v1/logical-switches', display=False)
            if not eObj:
                print("Network %s not found on cluster %s on vc %s" %(fpe1, cluster, vc))
                return None
            else:
                dataNets.append(eObj['id'])

            # fp-eth2
            eObj = S.findByName(name=fpe2, api='/api/v1/logical-switches', display=False)
            if not eObj:
                print("Network %s not found on cluster %s on vc %s" %(fpe2, cluster, vc))
                return None
            else:
                dataNets.append(eObj['id'])
    
                
            
        tzids = []
        TZ=TransportZone(mp=self.mp)
        swname=None
        for t in tznames:
            zid = TZ.findByName(name=t, display=False)
            if not zid:
                print("Transport zone %s not found" % zid)
                return None
            else:
                tzids.append({'transport_zone_id': zid['id']})
                if not swname:
                    swname=zid['host_switch_name']
                elif swname != zid['host_switch_name']:
                    print("Host switch name between TZs are not the same")
                    return
                    
        #swname="nvds2"
        data={}
        data['display_name'] = name
        # data['transport_zone_endpoints'] = tzids
        
        enode = {}
        data['node_deployment_info'] = enode
        enode['resource_type'] = 'EdgeNode'

        enodesettings={}
        enode['node_settings'] = enodesettings
        enodesettings['allow_ssh_root_login'] = allowRootSsh
        enodesettings['dns_servers'] = dns
        enodesettings['enable_ssh'] = enableSsh
        enodesettings['hostname'] = hostname
        enodesettings['ntp_servers'] = ntp
        enodesettings['search_domains'] = domains

        
        eDeploymentCfg={}
        eDeploymentCfg['form_factor'] = size
        enode['deployment_config'] = eDeploymentCfg
        
        user_settings={}
        eDeploymentCfg['node_user_settings'] = user_settings
        user_settings['cli_password'] = clipw
        user_settings['audit_password'] = auditpw
        user_settings['audit_username'] = 'audit'
        user_settings['root_password'] = rootpw

        vmCfg={}
        eDeploymentCfg['vm_deployment_config'] = vmCfg
        vmCfg['compute_id'] = cId.split(':')[1]
        vmCfg['vc_id'] = vcObj['id']
        vmCfg['storage_id'] = sId
        vmCfg['data_network_ids'] = dataNets
        vmCfg['default_gateway_addresses'] = gateway


        # mgmtNet
        if ntype != 'opaque':
            mgmtObj = CM.findNetwork(cluster=cluster, name=mgmtNet, vc=vc,
                                     storage=sId, display=False)
            if not mgmtObj:
                print("Network %s not found on cluster %s on vc %s" %(mgmtNet, cluster, vc))
                return None
            else:
                vmCfg['management_network_id'] = mgmtObj['network_resource']['target_id']
        else:
            S=Segments(mp=self.mp)
            mgmtObj = S.findByName(name=mgmtNet, api='/api/v1/logical-switches', display=False)
            if not mgmtObj:
                print("Network %s not found on cluster %s on vc %s" %(mgmtNet, cluster, vc))
                return None
            else:
                vmCfg['management_network_id'] = mgmtObj['id']
    
        vmCfg['management_port_subnets'] = [{'ip_addresses': [mgmtIp],
                                             'prefix_length': mgmtMask}]
        vmCfg['placement_type'] = 'VsphereDeploymentConfig'

        upprofiles = HostSwitchProfile(mp=self.mp)
        profile = upprofiles.findByName(name=uplink,display=False)
        if not profile:
            print( "Can't find uplink profile with name: %s" %uplink)
            return

        profiles = []
        profItem={}
        profItem['key'] = profile['resource_type']
        profItem['value'] = profile['id']
        profiles.append(profItem)

        #find LLDP profile
        lldpProfile=None
        if lldp:
            lldpProfile = upprofiles.findByName(name=lldp,display=False)
            if not lldpProfile:
                print ("Can't find the lldp profile with name: %s" %lldp)
                return


        if lldpProfile:
            profItem={}
            profItem['key'] = lldpProfile['resource_type']
            profItem['value'] = lldpProfile['id']
            profiles.append(profItem)

        #find the ippooln
        poolProfile=None
        if ippool:
            pools=IpPool(mp=self.mp)
            poolProfile=pools.getPoolId(name=ippool)
            if not poolProfile:
                print ("Can't find the IP pool with name: %s" %ippool)
                return

        team = profile['teaming']
        if 'standby_list' in team:
            uplinkList = team['active_list'] + team['standby_list']
        else:
            uplinkList = team['active_list']

        pnics = []
        upIndex = 0
        vIndex = 0
        vlanNics=[]
        if uplinkList[0]['uplink_type'] == 'PNIC':
            if len(uplinkList) < len(nics):
                print ("You have more nics than defined in the profile")
                return
            for n in nics:
                pnic={}
                pnic['device_name'] = n
                pnic['uplink_name'] = uplinkList[upIndex]['uplink_name']
                pnics.append(pnic)
                upIndex +=1
        else:
            if profile['lags'][0]['number_of_uplinks'] < len(nics):
                print ("You have more nics than defined in the LAG profile")
                return
            for n in nics:
                pnic={}
                pnic['device_name'] = n
                pnic['uplink_name'] = profile['lags'][0]['uplinks'][upIndex]['uplink_name']
                pnics.append(pnic)
                upIndex +=1

        switchSpec = {}
        switchSpec['resource_type'] = "StandardHostSwitchSpec"
        switchSpec['host_switches'] = []

        hsw = HostSwitch(mp=self.mp,pnics=pnics, profiles = profiles,
                         ippool=poolProfile, tz=tznames, name=swname)
        hswDict=hsw.getDict()

        switchSpec['host_switches'].append(hswDict)

        #if tzname:
        #    data['transport_zone_endpoints'] = hsw.transportzones

        vlansw=None
        if vlansw:
            vsw = HostSwitch(mp=self.mp, name=vlansw,pnics=vlanNics,profiles=profiles)
            vswDict = vsw.getDict()
            switchSpec['host_switches'].append(vswDict)

        data['host_switch_spec'] = switchSpec
        
        
        api='/api/v1/transport-nodes'
        return self.mp.post(api=api, data=data, verbose=True, codes=[201])

        
class Tier0(Nsx_object):
    '''
    Class to manage Tier0 Gateways
    '''
    def __init__(self, mp, site='default'):
        super(self.__class__, self).__init__(mp=mp, site=site)
        self.listApi='/policy/api/v1/search/query?query=resource_type:Tier0'
        #self.listApi='/policy/api/v1/infra/tier-0s'
        self.objApi='/policy/api/v1/infra/tier-0s'

    def setEdgeCluster(self, name, clustername, clusterid=None,
                       clusterpath=None, locale='default'):
        ec = EdgeCluster(mp=self.mp)
        if clustername:
            path = ec.getPathByName(name=clustername,display=False)
        else:
            print("EdgeCluster path, id, or name must be provided")
            return None
                                
        data={}
        data['edge_cluster_path'] = path
        t0 = self.findByName(name=name, display=False)
        if not t0:
            print("Can't find Tier0 %s" %name)
            return False

        if self.mp.global_gm:
            e = ec.findByName(name=clustername, display=False)
            api='/policy/api/v1'+t0['path']+'/locale-services/' + e['id']
        else:
            api='/policy/api/v1'+t0['path']+'/locale-services/' + locale
        print("source api is %s" %api)
        self.mp.patch(api=api, data=data, codes=[200], verbose=True)

    def setRouteDistribution(self, name, redist=None, locale='default', rm=None, ec=None):

        t0 = self.getPathByName(name=name, display=False)
        if not t0:
            print("Can't find Tier0 %s" %name)
            return False

        if self.mp.global_gm:
            if not ec:
                print("EdgeCluster must be provided for GM")
                return False
            EC = EdgeCluster(mp=self.mp)
            ec = EC.findByName(name=ec, display=False)
            api='/global-manager/api/v1'+t0+'/locale-services/'+ec['id']
            data=self.mp.get(api=api,display=False)
        else:
            api='/policy/api/v1'+ t0 + '/locale-services/' + locale
            data = self.mp.get(api=api, display=False)

        # deprecated and replaced with route_redistribution_config
        #data['route_redistribution_types'] = redist

            
        data['route_redistribution_config'] = {'bgp_enabled': True,
                                               'redistribution_rules': [{'route_redistribution_types': redist}]}
        if rm:
            R = RouteMap(mp=self.mp, tier0=None, t0Path=t0)
            r = R.getPathByName(name=rm, display=False)
            if not r:
                print("Route map %s not found" %rm)
                return False
            data['route_redistribution_config']['redistribution_rules'][0]['route_map_path'] = r
            
        self.mp.patch(api=api, data=data, codes=[200], verbose=True)

    def setPreferredEdges(self, name, cluster=None, edges=None, locale='default'):
        t0 = self.getPathByName(name=name, display=False)
        if not t0:
            print("Can't find Tier0 %s" %name)
            return False

        api='/policy/api/v1/'+ t0 + '/locale-services/' + locale

        if not edges:
            print("No edges specified, nothing changed")
            return False
        ec = None
        if cluster:
            c = EdgeCluster(mp=self.mp)
            ec = c.getPathByName(name=cluster, display=False)
            
        edge=Edge(mp=self.mp)
        edgeList = edge.list(display=False)
        preferred=[]
        for e in edges:
            t = edge.findByName(name=e, data=edgeList, display=False)
            if not t:
                print("Edge %s not found" % e)
                return False
            if ec:
                if t['parent_path'] != ec:
                    print("EdgeCluster path %s not same as edge's parent: %s"
                          %ec, t['parent_path'])
                    return False
            preferred.append(t['path'])
        if len(preferred) == 0:
            print("No valid edges specified")
            return None

        data={}
        data['preferred_edge_paths'] = preferred
                
        self.mp.patch(api=api, data=data, codes=[200], verbose=True)
            
    
    def getAllInterfaceStats(self, t0, display=False):
        interfaces = self.getInterfaces(name=t0, display=False)
        
        data={}
        data['results'] = []
        E = Edge(mp=self.mp)
        for i in interfaces['results']:
            d = self.getInterfaces(name=t0, interface=i['display_name'],
                                   stats=True, display=False) 

            output={}
            output['interface'] = i
            output['stats'] = d
            data['results'].append(output)
        if display:
            self.jsonPrint(data)
        return data

    def getInterfaceByName(self, t0, name):
        allInts = self.getInterfaces(name=t0, display=False)
        for i in allInts['results']:
           if i['display_name'] == name:
               return i
        return None


    def getInterfaces(self, name, locale='default', interface=None,
                      stats=False, node=None,display=True):

        t0=self.getPathByName(name=name, display=False)
        if not t0:
            print("Tier0 with name %s not found" %name)
            return None
            
        api='/policy/api/v1' + t0 + '/locale-services/' + locale + '/interfaces'
        if interface:
            E=EnforcementPoints(mp=self.mp)
            epath=E.getPathByName(name='default', display=False)
            uplink = self.getInterfaceByName(t0=name, name=interface)
            if not uplink:
                print("Interface %s not found on T0 %s" %(interface, name))
                return None
            
            api=api + '/' + uplink['relative_path']
            if stats:
                api=(api+'/statistics?enforcement_point_path=%s&edge_path=%s'
                     %(epath, uplink['edge_path']))

        r = self.mp.get(api=api, verbose=display, codes=[200])
        if display:
            self.jsonPrint(r)
        return r

    def createInterface(self, name, interface, 
                        segment, cidr, mtu=1500, intType='EXTERNAL',
                        pim=False, pimHello=30, pimHold=105,
                        ec=None,edge=None, desc=None, locale='default'):
        
        t0=self.getPathByName(name=name, display=False)
        if not t0:
            print("Tier0 with name %s not found" %name)
            return None

        if self.mp.global_gm:
            if not ec:
                print("Edge cluster must be provided for GM config")
                return None
            E = EdgeCluster(mp=self.mp)
            e = E.findByName(name=ec, display=False)
            if not e:
                print("Edge cluster %s not found" %ec)
                return None
            api='/policy/api/v1' + t0 + '/locale-services/' \
                + e['nsx_id'] + '/interfaces/' + interface
        else:
            api='/policy/api/v1' + t0 + '/locale-services/' \
                + locale + '/interfaces/' + interface
        s = Segments(mp=self.mp)
        ls = s.getPathByName(name=segment,display=False)
        if not ls:
            print("Segment %s not found" %segment)
            return None
        e=Edge(mp=self.mp)
        eList=e.listOld(display=False)
        self.jsonPrint(eList)
        edgePath = e.getPathByName(name=edge, data=eList,display=False)
        if intType=="EXTERNAL" and not edgePath:
            print("Edge %s not found" %edge)
            return False

        subnets=[]
        for n in cidr:
            if '/' not in n:
                print("IP address must be in CIDR format")
                return None
            p,m = n.split('/')
            subnet={}
            subnet['ip_addresses'] = [p]
            subnet['prefix_len'] = m
            subnets.append(subnet)

        if len(subnets) == 0:
            print("Must provide atleast one CIDR for interface address")
            return None

        
        cur = self.mp.get(api=api, display=False)
        if cur:
            data=cur
        else:
            data={}
        data={}
        data['display_name'] = interface
        data['mtu'] = mtu
        if edgePath:
            data['edge_path'] = edgePath
        data['segment_path'] = ls
        data['type'] = intType
        data['description'] = desc
        data['subnets'] = subnets
        data['resource_type'] = 'Tier0Interface'
        if pim:
            pimData={}
            pimData['enabled'] = True
            pimData['hello_interval'] = pimHello
            pimData['hold_interval'] = pimHold
            data['multicast'] = pimData
    
        self.mp.patch(api=api, data=data, codes=[200], verbose=True)
        
    def deleteInterface(self, name, interface, locale='default', display=True):
        t0=self.getPathByName(name=name, display=False)
        if not t0:
            print("Tier0 with name %s not found" %name)
            return None

        api='/policy/api/v1' + t0 + '/locale-services/' \
            + locale + '/interfaces/' + interface
        self.delete(api=api,verbose=display,codes=[200])


    def config(self, name, failover=None, ha=None,
               transit=None, dhcprelay=None, desc=None):
        data={}
        data['display_name'] = name

        if failover:
            data['failover_mode'] = failover
        if ha:
            data['ha_mode'] = ha
        if transit:
            data['transit_subnets'] = [transit]
        if desc:
            data['description'] = desc
        if dhcprelay:
            ds=DhcpRelay(mp=self.mp)
            dhcp=ds.getPathByName(name=dhcprelay, display=False)
            if not dhcp:
                print("DHCP relay service %s not found." %dhcprelay)
                return False
            data['dhcp_config_paths'] = [dhcp]

        api='/policy/api/v1/infra/tier-0s/%s' % name
        self.mp.patch(api=api,data=data,verbose=True,codes=[200])

    def getLocale(self,name,ec=None,display=True):
        url=self.objApi + "/" + name + "/locale-services"
        if self.mp.global_gm and ec:
            EC=EdgeCluster(mp=self.mp)
            ec=EC.findbyName(name=ec, display=False)
            url=url+ec['id']
        return self.list(api=url,display=display)
        

    def setDhcpRelayService(self, name, relay, display=True):
        t0=self.getPathByName(name=name, display=False)
        if not t0:
            print("Tier0 with name %s not found" %name)
            return None

        api='/policy/api/v1' + t0
        ds=DhcpRelay(mp=self.mp)
        dhcp = ds.getPathByName(name=relay)
        if not dhcp:
            print("DHCP Relay service %s not found" %relay)
            return None
        data={}
        data['dhcp_config_paths'] = [dhcp]
        self.mp.patch(api=api, data=data, verbose=display, codes=[200])

    def getBgpConfig(self, name, locale='default', display=True):
        t0=self.getPathByName(name=name, display=False)
        if not t0:
            print("Tier0 with name %s not found" %name)
            return None
        
        api='/policy/api/v1' + t0 + '/locale-services/' + locale + '/bgp'
        r = self.mp.get(api=api,verbose=display,codes=[200])
        self.jsonPrint(r)

    def configBgp(self, name,
                  localas,
                  routeagg=None,
                  enable_multipathrelax=False,
                  disable_multipathrelax=False,
                  enable_intersr=False,
                  disable_intersr=False,
                  disable_gr=False,
                  enable_gr=False,
                  enable_ecmp=False,
                  disable_ecmp=False,
                  desc=None,
                  locale='default',
                  grmode="NONE",
                  gr_restart_timer=180,
                  gr_stale_timer=600,
                  display=True):

        '''
        Have to let each config flag to be specified individually because
        patch will toggle previous config.  If user specifies a flag, it
        means we want a config change.  
        '''
        
        t0=self.getPathByName(name=name, display=False)
        if not t0:
            print("Tier0 with name %s not found" %name)
            return None

        locales = self.getLocale(name=name, display=False)['results']
        for locale in locales:
            api='/policy/api/v1' + t0 + '/locale-services/' + locale['id'] + '/bgp'

            data={}
            data['local_as_num'] = localas
            if enable_multipathrelax:
                data['multipath_relax'] = enable_multipathrelax
            if disable_multipathrelax:
                data['multipath_relax'] = False
            if enable_intersr:
                data['inter_sr_ibgp'] = enable_intersr
            if disable_intersr:
                data['inter_sr_ibgp'] = False
            if enable_ecmp:
                data['ecmp'] = enable_ecmp
            if disable_ecmp:
                data['ecmp'] = False

            # this is legacy GR config mode
            if enable_gr:
                data['graceful_restart'] = True
            if disable_gr:
                data['graceful_restart'] = False
            # this is new GR config mode
            if grmode != 'NONE':
                grdata={}
                grdata['mode'] = grmode
                grdata['timer'] = {}
                grdata['timer']['restart_timer'] = gr_restart_timer
                grdata['timer']['stale_route_timer'] = gr_stale_timer
                data['graceful_restart_config'] = grdata
            if desc:
                data['description'] = desc
            if routeagg:
                for r in routeagg:
                    route={}
                    if ':' in r:
                        prefix,summary=r.split(':')
                        summary=summary.lower()
                        if summary not in ['true', 'false']:
                            print("Route summary must be true or false for prefix %s but is (%s)"
                            %(prefix, summary))
                            return False
                        if summary == 'true':
                            route['summary_only'] = True
                        else:
                            route['summary_only'] = False
                            
                    else:
                        prefix=r
                    if '/' not in prefix:
                        print("Prefix must be in CIDR format, missing /: %s" %prefix)
                        return False
                    route['prefix'] = prefix
                    if 'route_aggregations' in data.keys():
                        data['route_aggregations'].append(route)
                    else:
                        data['route_aggregations'] = [route]
            data['resource_type'] = 'BgpRoutingConfig'
            self.mp.patch(api=api, data=data, verbose=display, codes=[200])

    def parseNextHops(self, hops):
        data=[]
        for i in hops:
            hop={}
            vals=i.split(':')
            hop['ip_address'] = vals[0]
            if len(vals) > 1:
                if vals[1].isdigit():
                    hop['admin_distance'] = vals[1]
            data.append(hop)
        return data
                
    def configNatRule(self, t0,
                   natrulename,
                   action,
                   natid="USER",
                   translatedip=None,
                   sourceip=None,
                   destinationip=None,
                   desc=None,
                   service=None,
                   appliedto=None,
                   ruleenabled=True,
                   logging=False,
                   translatedports=None,
                   firewall=None,
                   priority="100",
                   display=True):
        t0=self.getPathByName(name=t0, display=False)
        if not t0:
            print("Tier0 with name %s not found" %t0)
            return None

        data={}
        data['display_name'] = natrulename
        if action:
            if action not in ['DNAT', 'SNAT', 'REFLEXIVE', 'NO_SNAT', 'NO_DNAT']:
                print("action %s not valid.", action)
                return
            data['action'] = action
        if natid:
            if natid not in ['USER', 'DEFAULT', 'INTERNAL']:
                print("natid %s not valid.", natid)
                return
            natid = natid
        if translatedip:
            data['translated_network'] = translatedip
        if sourceip:
             data['source_network'] = sourceip
        if destinationip:
            data['destination_network'] = destinationip
        if desc:
            data['description'] = desc
        if service:
            data['service'] = '/infra/services/%s' %service
        if appliedto:
            data['scope'] = []
            at = appliedto.split()
            for s in at:
                s =  t0 + '/locale-services/default/interfaces/' + s
                data['scope'].append(s)
        if ruleenabled:
            data['enabled'] = ruleenabled.lower()
        if logging:
            data['logging'] = logging.lower()
        if translatedports:
            data['translated_ports'] = translatedports
        if firewall:
            if firewall not in ['MATCH_INTERNAL_ADDRESS', 'MATCH_EXTERNAL_ADDRESS', 'BYPASS']:
                print("firewall setting %s is not valid", firewall)
            data['firewall_match'] = firewall
        if priority:
            data['sequence_number'] = priority

        api = '/policy/api/v1' + t0 + '/nat/' + natid + '/nat-rules/' + natrulename
        r = self.mp.patch(api=api, data=data, verbose=True, codes=[200])

    def deleteNatRule(self, t0, natrulename, natid="USER", display=True):
        api = '/policy/api/v1/infra/tier-0s/' + t0 + '/nat/' + natid + '/nat-rules/' + natrulename
        self.mp.delete(api=api, verbose=display, codes=[200])

    def getNatRule(self, t0, natrulename, natid="USER", display=True):
        api = '/policy/api/v1/infra/tier-0s/' + t0 + '/nat/' + natid + '/nat-rules/' + natrulename
        g=self.mp.get(api=api, verbose=display, codes=[200])
        self.jsonPrint(g)

    def listTier0NatRules(self, t0, natid="USER", display=True):
        api = '/policy/api/v1/infra/tier-0s/' + t0 + '/nat/' + natid + '/nat-rules/'
        l=self.mp.get(api=api, verbose=display, codes=[200])
        self.jsonPrint(l)

    def addStaticRoute(self, name, routename, cidr, hops, desc=None,display=True):
        t0=self.getPathByName(name=name, display=False)
        if not t0:
            print("Tier0 with name %s not found" %name)
            return None
        
        hdata=self.parseNextHops(hops)
        data={}
        data['display_name'] = routename
        if desc:
            data['description'] = desc
        data['network'] = cidr
        data['next_hops'] = hdata

        api='/policy/api/v1' + t0 + '/static-routes/' + routename
        r = self.mp.patch(api=api,data=data,verbose=True, codes=[200])

    def getBgpNeighbors(self, name, locale='default', display=True):
        
        t0=self.getPathByName(name=name, display=False)
        if not t0:
            print("Tier0 with name %s not found" %name)
            return None
        
        api='/policy/api/v1' + t0 + '/locale-services/' + locale + '/bgp/neighbors'
        self.mp.get(api=api,verbose=True,codes=[200], display=True)
    

    def configBgpNeighbor(self, name,
                          neighborAddr,
                          remoteAs,
                          neighborName,
                          neighborDesc=None,
                          holdtime=None,
                          keepalive=None,
                          password=None,
                          enablebfd=False,
                          disablebfd=False,
                          bfdInterval=None,
                          bfdMultiple=None,
                          sourceIp=None,
                          gr=None,
                          ipv6=False,
                          inPrefixList=None,
                          inRouteMap=None,
                          outPrefixList=None,
                          outRouteMap=None,
                          ec = None,
                          locale='default', display=True):

        t0=self.getPathByName(name=name, display=False)
        if not t0:
            print("Tier0 with name %s not found" %name)
            return None

        if self.mp.global_gm:
            if not ec:
                print("Edge cluster must be provided for GM config")
                return None
            E = EdgeCluster(mp=self.mp)
            e = E.findByName(name=ec, display=False)
            if not e:
                print("Edge cluster %s not found" %ec)
                return None
            api='/policy/api/v1' + t0 + '/locale-services/' \
                + e['id'] + '/bgp/neighbors/' + neighborName

        else:
            api='/policy/api/v1' + t0 + '/locale-services/' + locale + '/bgp/neighbors/'+neighborName

        data={}
        data['display_name'] = neighborName
        data['neighbor_address'] = neighborAddr
        data['remote_as_num'] = remoteAs
        if neighborDesc:
            data['description'] = neighborDesc
        if holdtime:
            data['hold_down_time'] = holdtime
        if keepalive:
            data['keep_alive_time'] = keepalive
        if password:
            data['password'] = password

        if enablebfd or disablebfd or bfdInterval or bfdMultiple:
            bfdData={}
            if enablebfd:
                bfdData['enabled'] = enablebfd
            if disablebfd:
                bfdData['enabled'] = disablebfd
            if bfdInterval:
                bfdData['interval'] = bfdInterval
            if bfdMultiple:
                bfdData['multiple'] = bfdMultiple
            data['bfd'] = bfdData

        if sourceIp:
            data['source_addresses'] = sourceIp
        if gr:
            # DISABLE, GR_AND_HELPER, HELPER_ONLY
            if gr not in ['DISABLE', 'GR_AND_HELPER', 'HELPER_ONLY']:
                print("Graceful Restart mode of %s not supported." %gr)
                return
            data['graceful_restart_mode'] = gr

        routefilter = {}
        if ipv6:
            routefilter['address_family'] = 'IPV6'
        else:
            routefilter['address_family'] = 'IPV4'

        data['route_filtering']=[routefilter]
        pfx=PrefixList(mp=self.mp, tier0=None,t0Path=t0)
        rmp=RouteMap(mp=self.mp, tier0=None,t0Path=t0)
        if inPrefixList or inRouteMap:
            routefilter['in_route_filters'] = []
            for i in  (inPrefixList or []):
                pfxPath=pfx.getPathByName(name=i,display=False)
                if pfxPath:
                    routefilter['in_route_filters'].append(pfxPath)
                else:
                    print("Invalid inbound prefixlist: %s" %i)
                    return

            for i in (inRouteMap or []):
                rmPath=rmp.getPathByName(name=i,display=False)
                if rmPath:
                    routefilter['in_route_filters'].append(rmPath)
                else:
                    print("Invalid inbound routemap: %s" %i)
                    return
        if outPrefixList or outRouteMap:
            routefilter['out_route_filters'] = []
            for i in (outPrefixList or []):
                pfxPath=pfx.getPathByName(name=i,display=False)
                if pfxPath:
                    routefilter['out_route_filters'].append(pfxPath)
                else:
                    print("Invalid outbound prefixlist: %s" %i)
                    return
            for i in (outRouteMap or []):
                rmPath=rmp.getPathByName(name=i,display=False)
                if rmPath:
                    routefilter['out_route_filters'].append(rmPath)
                else:
                    print("Invalid outbound routemap: %s" %i)
                    return
            
        data['resource_type'] = 'BgpNeighborConfig'
        
        r = self.mp.patch(api=api,data=data,verbose=True, codes=[200])


    def deleteBgpNeighbor(self, name, neighborName, locale='default', display=True):
        t0=self.getPathByName(name=name, display=False)
        if not t0:
            print("Tier0 with name %s not found" %name)
            return None
        
        api='/policy/api/v1' + t0 + '/locale-services/' + locale + '/bgp/neighbors/'+neighborName

        self.delete(api=api, verbose=display)

    def getLogicalRouterInfo(self, name, info='id'):
        '''
        Get the realized ID or api for the gateway
        info can be 'id' or 'api'
        '''
        data=self.getRealizationEntities(name=name, display=False)
        for d in data['results']:
            if d['entity_type'] == 'RealizedLogicalRouter':
                if info == 'id':
                    return d['realization_specific_identifier']
                elif info == 'api':
                    return d['realization_api']
                else:
                    raise ValueError("Invalid info %s, must be id or api" %info)
        return None
                        
    def getBgpNeighborStatus(self, name, display=True):
        mpApi=self.getLogicalRouterInfo(name=name, info='api')
        if not mpApi:
            print("Invalid Tier0 Gateway or realization error: %s" %name)
            return
        api=mpApi+'/routing/bgp/neighbors/status?source=realtime'
        r = self.mp.get(api=api,verbose=True)
        if display:
            self.jsonPrint(r)
        return r

    def getLrStatus(self, name, display=False):
        mpApi=self.getLogicalRouterInfo(name=name, info='api')
        if not mpApi:
            print("Invalid Tier0 Gateway or realization error: %s" %name)
            return None
        api=mpApi+'/status'
        r = self.mp.get(api=api,verbose=False)
        if display:
            self.jsonPrint(r)
        return r
        
    def getRouteTable(self, name, node=None, rtype='routing-table'):
        '''
        rtype can be 'routing-table' or 'forwarding-table'
        '''
        status = self.getLrStatus(name=name, display=False)
        if not status:
            print("Tier0 %s not found" %name)
            return None
        
        mpApi=self.getLogicalRouterInfo(name=name, info='api')
        if not mpApi:
            print("Invalid Tier0 Gateway or realization error: %s" %name)
            return None

        for n in status['per_node_status']:
            print("==>Output for Edge TN %s" %n['transport_node_id'])
            api=mpApi+'/routing/'+rtype+'?transport_node_id=%s&source=realtime' %n['transport_node_id']
            r = self.mp.get(api=api,verbose=True)
            self.jsonPrint(r)
            
    def getPim(self, t0, locale='default', display=True):
        locales=self.getLocale(name=t0,display=False)
        loc=self.getPathByName(name=locale, data=locales, display=False)
        if not loc:
            print("Locale %s not found for Tier0 %s" %(locale, t0))
            return False
        data={}
        api='/policy/api/v1'+loc+'/multicast'
        print(api)
        self.mp.get(api=api, verbose=display, display=display)

    def configurePim(self, t0, enable, repRange,
                     pimProfile, igmpProfile='default',
                     locale='default'):
        locales=self.getLocale(name=t0,display=False)
        loc=self.getPathByName(name=locale, data=locales, display=False)
        if not loc:
            print("Locale %s not found for Tier0 %s" %(locale, t0))
            return False
        api='/policy/api/v1'+loc+'/multicast'
        data={}
        data['enabled'] = enable
        data['replication_multicast_range'] = repRange
        I = IgmpProfile(mp=self.mp)
        igmp=I.getPathByName(name=igmpProfile, display=False)
        if not igmp:
            print("IGMP profile %s not found" %igmpProfile)
            return False
        P = PimProfile(mp=self.mp)
        pim = P.getPathByName(name=pimProfile, display=False)
        if not pim:
            print("PIM profile %s not found" %pimProfile)
            return False

        data['igmp_profile_path']=igmp
        data['pim_profile_path']=pim
        self.mp.patch(api=api, data=data, verbose=True, codes=[200])

class PimProfile(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/infra/pim-profiles'

    def config(self, name, bsm, rps, desc=None):
        p = self.getPathByName(name=name, display=False)
        if p:
            api='/policy/api/v1'+p
            data=self.findByName(name=name, display=True)
        else:
            api='/policy/api/v1/infra/pim-profiles/%s' % name
            data={}

        data['display_name'] = name
        data['bsm_enabled'] = bsm
        data['rp_address_multicast_ranges'] = []
        for i in rps:
            rp,ranges=i.split('|')
            groups=ranges.split(',')
            rdata={}
            rdata['rp_address'] = rp
            rdata['multicast_ranges'] = groups
            data['rp_address_multicast_ranges'].append(rdata)

        self.mp.patch(api=api,data=data,codes=[200])
        

class IgmpProfile(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/infra/igmp-profiles'

                  
            


        



        
        
        
class PrefixList(Nsx_object):
    def __init__(self, mp, tier0, t0Path=None):
        super(self.__class__, self).__init__(mp=mp)
        if not t0Path:
            T0=Tier0(mp=self.mp)
            t0Path=T0.getPathByName(name=tier0, display=False)
        self.listApi='/policy/api/v1' + t0Path + '/prefix-lists'


    def config(self, t0, name, prefix, desc=None,display=True):
        api='/policy/api/v1/infra/tier-0s/' + t0 + '/prefix-lists/' + name

        data={}
        data['display_name'] = name
        if desc:
            data['description'] = desc

        data['prefixes'] = []
        
        for p in prefix:
            '''
            format CIDR,GE bits,LE bits:action
            action can be PERMIT, DENY
            GE and LE can be blank
            the CIDR could also be "ANY"
            '''
            prefix = p.split(',')
            pdata={}
            if len(prefix) != 4:
                print("Prefix format: CIDR,GE,LE,<PERMIT,DENY>")
                return None

            subnet = prefix[0].strip()
            if not '/' in subnet and subnet.upper()!='ANY':
                print("Prefix %s not in CIDR format" %subnet)
                return None
            else:
                pdata['network'] = subnet.upper()
                
            ge = prefix[1].strip()
            if ge == '':
                ge = None
            else:
                pdata['ge'] = ge
                
            le = prefix[2].strip()
            if le == '':
                le = None
            else:
                pdata['le'] = le
                
            action = prefix[3].strip().upper()
            if action not in ["DENY", "PERMIT"]:
                print("action must be DENY or PERMIT")
                return None
            else:
                pdata['action'] = action

            data['prefixes'].append(pdata)

        if len(data['prefixes']) ==  0:
            print("No prefix specified.")
            return None

        self.mp.patch(api=api, data=data, codes=[200], verbose=True)
                  
    def deletePrefixList(self, t0, name, display=True):
        api='/policy/api/v1/infra/tier-0s/' + t0 + '/prefix-lists/' + name
        self.delete(api=api,verbose=display,codes=[200])

class BgpCommunity(Nsx_object):
    '''
    *****This implementation is not complete
    '''
    def __init__(self, mp, tier0, t0Path=None):
        super(self.__class__, self).__init__(mp=mp)
        if not t0Path:
            T0=Tier0(mp=self.mp)
            t0Path=T0.getPathByName(name=tier0, display=False)
        self.listApi='/policy/api/v1' + t0Path + '/community-lists'


    def config(self, t0, name, communities, desc=None,display=True):
        api=self.listApi + '/' + name

        data={}
        data['display_name'] = name
        if desc:
            data['description'] = desc

        data['communities'] = []
        
        for p in communities:
            '''
            value types: NO_EXPORT, NO_ADVERTISE, NO_EXPORT_SUBCONFED, <x:y>
            '''
         
            if p.upper() in ["NO_EXPORT", "NO_ADVERTISE", "NO_EXPORT_SUBCONFED"]:
                data['communities'].append(p.upper())
            elif ':' in p:
                data['communities'].append(p)
            else:
                print("Community %s not valid")
                return None
                
        if len(data['communities']) ==  0:
            print("No communities specified.")
            return None

        self.mp.patch(api=api, data=data, codes=[200], verbose=True)
                  
    def deleteBgpCommunity(self, t0, name, display=True):
        api='/policy/api/v1/infra/tier-0s/' + t0 + '/community-liss/' + name
        self.delete(api=api,verbose=display,codes=[200])
            
class RouteMap(Nsx_object):
    def __init__(self, mp, tier0, t0Path=None):
        super(self.__class__, self).__init__(mp=mp)
        self.t0Path=t0Path
        if not self.t0Path:
            T0=Tier0(mp=self.mp)
            self.t0Path=T0.getPathByName(name=tier0, display=False)
        self.listApi='/policy/api/v1' + self.t0Path + '/route-maps'
            

    def config(self, name, community, comAction,
               prefix, prefixAction,
               asprepend=None, setcomm=None,
               localpref=None, med=None,
               preferv6nh=None, weight=None, append=True,
               desc=None,display=True):
        current=self.findByName(name=name,display=False)
        if append:
            if current:
                data=current
            else:
                data={}
        else:
            data={}
        data['display_name'] = name
        if desc:
            data['description'] = desc
            
        P = PrefixList(mp=self.mp, tier0=None, t0Path=self.t0Path)
        C = BgpCommunity(mp=self.mp, tier0=None, t0Path=self.t0Path)
        if not append or 'entries' not in data:
            data['entries'] = []

        if community:
            if comAction.upper() not in ['PERMIT', 'DENY']:
                print("Community string action of %s not PERMIT or DENY" %comAction)
                return False
            cdata={}
            cdata['action'] = comAction.upper()
            cdata['community_list_matches'] = []
            sets = self.createRMSet(asprepend=asprepend,
                                    setcomm=setcomm,
                                    localpref=localpref,
                                    med=med,
                                    preferv6nh=preferv6nh,
                                    weight=weight)
            if sets:
                cdata['set'] = sets
            for c in community:
                cm = C.getPathByName(name=c, display=False)
                if not cm:
                    print("Community list %s not found" % c)
                    return False
                cdata['community_list_matches'].append(cm)
            
            data['entries'].append(cdata)
            
        if prefix:
            if prefixAction.upper() not in ['PERMIT', 'DENY']:
                print("Prefix List action of %s not PERMIT or DENY" %prefixAction)
                return False
            pdata={}
            pdata['action'] = prefixAction.upper()
            pdata['prefix_list_matches'] = []
            sets = self.createRMSet(asprepend=asprepend,
                                    setcomm=setcomm,
                                    localpref=localpref,
                                    med=med,
                                    preferv6nh=preferv6nh,
                                    weight=weight)
            if sets:
                pdata['set'] = sets
            for p in prefix:
                px = P.getPathByName(name=p, display=False)
                if not px:
                    print("Prefix List %s not found" %p)
                    return False
                pdata['prefix_list_matches'].append(px)
            data['entries'].append(pdata)

        if current:
            api='/policy/api/v1'+current['path']
        else:
            api=self.listApi+'/'+name
        self.mp.patch(api=api, data=data, codes=[200], verbose=True)
                  
    def createRMSet(self,asprepend, setcomm, localpref, med, preferv6nh, weight):
        data={}
        d=False
        if asprepend:
            data['as_path_prepend'] = asprepend
            d=True
        if setcomm:
            data['community'] = setcomm
            d=True
        if localpref:
            data['local_preference'] = localpref
            d=True
        if med:
            data['med'] = med
            d=True
        if preferv6nh:
            data['prefer_global_v6_next_hop'] = True
            d=True
        if weight:
            data['weight'] = weight
            d=True
        if d:
            return data
        else:
            return None
        
class Tier1(Nsx_object):
    '''
    Class to manage Tier1 Gateways
    '''
    def __init__(self, mp, site='default'):
        super(self.__class__, self).__init__(mp=mp, site=site)
        self.listApi='/policy/api/v1/search/query?query=resource_type:Tier1'
        #self.listApi='/policy/api/v1/infra/tier-1s'
        self.objectApi='/policy/api/v1/infra/tier-1s'

    def deleteT1(self, name):
        t1 = self.findByName(name=name, display=False)
        if not t1:
            print("Tier1 %s not found" %name)
            return None

        locales = self.getLocale(name=name, display=False)['results']
        for locale in locales:
            api='/policy/api/v1%s' %locale['path']
            self.mp.delete(api=api,verbose=True, codes=[200])

        api='/policy/api/v1%s' %t1['path']
        self.mp.delete(api=api,verbose=True, codes=[200])

    def setMulticast(self, name, enable=False, log=None, locale="default"):
        locales=self.getLocale(name=name,display=False)
        loc=self.getPathByName(name=locale, data=locales, display=False)
        if not loc:
            print("Locale %s not found for Tier1 %s" %(locale, name))
            return False
        api='/policy/api/v1'+loc+'/multicast'
        data={}
        if log:
            data['display_name'] = log
        data['enabled'] = enable
        self.mp.patch(api=api,data=data,verbose=True, codes=[200])
        
    def getMulticast(self, name, display=True, locale='default'):
        locales=self.getLocale(name=name,display=False)
        loc=self.getPathByName(name=locale, data=locales, display=False)
        if not loc:
            if display:
                print("Locale %s not found for Tier1 %s" %(locale, name))
            return None
        api='/policy/api/v1'+loc+'/multicast'
        r = self.mp.get(api=api, verbose=True, display=True)
        
    def config(self, name, preempt="NON_PREEMPTIVE", tier0=None, dhcprelay=None,
               standby_relocate=False,
               advertisements=None):
        data={}
        data['display_name'] = name
        data['failover_mode'] = preempt
        if tier0:
            T = Tier0(mp=self.mp, site=self.site)
            t0Path=T.getPathByName(name=tier0, display=False)
            if not t0Path:
                print("Tier0 %s not found" %tier0)
                return
            data['tier0_path']=t0Path
        if advertisements:
            data['route_advertisement_types'] = advertisements

        if standby_relocate:
            data['enable_standby_relocation'] = True
        if dhcprelay:
            ds=DhcpRelay(mp=self.mp)
            dhcp=ds.getPathByName(name=dhcprelay, display=False)
            if not dhcp:
                print("DHCP relay service %s not found." %dhcprelay)
                return False
            data['dhcp_config_paths'] = [dhcp]

        api='/policy/api/v1/infra/tier-1s/%s' %name
        self.mp.patch(api=api,data=data,verbose=True,codes=[200])


    def setPrimarySite(self, name, primary):
        t1=self.findByName(name=name,
                           api='/global-manager/api/v1/global-infra/tier-1s',
                           display=False)
        if not t1:
            print("Tier1 %s not found" %name)
            return None
        S = Sites(mp=self.mp)
        site = S.getPathByName(name=primary, display=False)
        if not site:
            print("Site %s not found" %primary)
            return None
        if 'intersite_config' in t1.keys():
            t1['intersite_config']['primary_site_path'] = site
        else:
            t1['intersite_config'] = {'primary_site_path': site}
        api='/global-manager/api/v1%s' % t1['path']
        self.mp.patch(api=api, data=t1, verbose=True, codes=[200])
        
    def setEdgeCluster(self, name=None, clustername=None, clusterid=None,
                       clusterpath=None, edges=None, locale='default'):
        ec = EdgeCluster(mp=self.mp)
        if not clusterpath:
            if not clusterid:
                if clustername:
                    path = ec.getPathByName(name=clustername,display=False)
                else:
                    print("EdgeCluster path, id, or name must be provided")
                    return None
            else:
                path = ec.getPathById(id=clusterid, display=False)
        if not path:
            print("EdgeCluster path, id, or name must be provided")
            return None
        
        t1 = self.getPathByName(name=name, display=False)
        if not t1:
            print("Can't find Tier1 %s" %name)
            return False
        api='/policy/api/v1'+t1+'/locale-services/' + locale
        data={}
        data['edge_cluster_path'] = path
        if edges:
            preferred=[]
            edge=Edge(mp=self.mp)
            edgeList = edge.list(ec=clustername,display=False)
            for e in edges:
                epath = edge.getPathByName(name=e, data=edgeList, display=False)
                if not epath:
                    print('Edge %s not found in cluster %s' %(e, clustername))
                    return
                preferred.append(epath)
            data['preferred_edge_paths']=preferred

        self.mp.patch(api=api, data=data, codes=[200], verbose=True)


    def getInterfaces(self, tier1, locale='default', display=True):
        t1path=self.getPathByName(name=tier1, display=False)
        if not t1path:
            print("No Tier1 with name %s found" %tier1)
            return None

        api='/policy/api/v1%s/locale-services/%s/interfaces' %(t1path,locale)
        r = self.list(api=api,display=display)
        return r

    def configInterface(self, tier1, intName, segment,
                        addrs, mask, locale='default'):
        t1path=self.getPathByName(name=tier1, display=False)
        if not t1path:
            print("No Tier1 with name %s found" %tier1)
            return None
        S = Segments(mp=self.mp)
        spath = S.getPathByName(name=segment, display=False)
        if not spath:
            print("Segment %s not found" % segment)
            return None
        
        data={}
        data['display_name'] = intName
        data['segment_path'] = spath
        data['subnets'] = []
        intIP = {}
        intIP['prefix_len'] = mask
        intIP['ip_addresses'] = []
        for n in addrs:
            intIP['ip_addresses'].append(n)
        data['subnets'].append(intIP)
        
        api='/policy/api/v1%s/locale-services/%s/interfaces/%s' %(t1path,locale,intName)
        self.mp.patch(api=api,verbose=True,data=data)
    def parseNextHops(self, hops):
        data=[]
        for i in hops:
            hop={}
            vals=i.split(':')
            hop['ip_address'] = vals[0]
            if len(vals) > 1:
                if vals[1].isdigit():
                    hop['admin_distance'] = vals[1]
            data.append(hop)
        return data

    def addStaticRoute(self, t1, routename, cidr, hops, desc=None,display=True):
        t1r=self.getPathByName(name=t1, display=False)
        if not t1r:
            print("Tier with name %s not found" %t1)
            return None
        
        hdata=self.parseNextHops(hops)
        data={}
        data['display_name'] = routename
        if desc:
            data['description'] = desc
        data['network'] = cidr
        data['next_hops'] = hdata

        api='/policy/api/v1' + t1r + '/static-routes/' + routename
        r = self.mp.patch(api=api,data=data,verbose=True, codes=[200])

    def getLocale(self,name,display=True):
        path=self.getPathByName(name=name,display=False)
        if not path:
            if display:
                print("%s not found" %name)
            return None
        url='/policy/api/v1'+path+"/locale-services"

        return self.list(api=url,display=display)

    def deleteLocales(self, name, locales=None):
        locs = self.getLocale(name=name,display=False)
        if not locs:
            print("No locales to delete for %s" %name)
            return None
        if locales:
            for c in locales:
                for i in locs['results']:
                    if i['display_name'] == c:
                        api='/policy/api/v1'+i['path']
                        self.mp.delete(api==api, verbose=True, codes=[200])
        else:
            for i in locs['results']:
                if i['display_name'] == c:
                    api='/policy/api/v1'+i['path']
                    self.mp.delete(api==api, verbose=True, codes=[200])
        
    def configNatRule(self, t1,
                  natrulename,
                  action,
                  natid="USER",
                  translatedip=None,
                  sourceip=None,
                  destinationip=None,
                  desc=None,
                  service=None,
                  appliedto=None,
                  ruleenabled=True,
                  logging=False,
                  translatedports=None,
                  firewall=None,
                  priority="100",
                  display=True):
        t1 = self.getPathByName(name=t1, display=False)
        if not t1:
            print("Tier1 with name %s not found" % t1)
            return None

        data = {}
        data['display_name'] = natrulename
        if action:
            if action not in ['DNAT', 'SNAT', 'REFLEXIVE', 'NO_SNAT', 'NO_DNAT']:
                print("action %s not valid.", action)
                return
            data['action'] = action
        if natid:
            if natid not in ['USER', 'DEFAULT', 'INTERNAL']:
                print("natid %s not valid.", natid)
                return
            natid = natid
        if translatedip:
            data['translated_network'] = translatedip
        if sourceip:
            data['source_network'] = sourceip
        if destinationip:
            data['destination_network'] = destinationip
        if desc:
            data['description'] = desc
        if service:
            data['service'] = '/infra/services/%s' % service
        if appliedto:
            data['scope'] = []
            at = appliedto.split()
            for s in at:
                s = t1 + '/locale-services/default/interfaces/' + s
                data['scope'].append(s)
        if ruleenabled:
            data['enabled'] = ruleenabled.lower()
        if logging:
            data['logging'] = logging.lower()
        if translatedports:
            data['translated_ports'] = translatedports
        if firewall:
            if firewall not in ['MATCH_INTERNAL_ADDRESS', 'MATCH_EXTERNAL_ADDRESS', 'BYPASS']:
                print("firewall setting %s is not valid", firewall)
            data['firewall_match'] = firewall
        if priority:
            data['sequence_number'] = priority

        api = '/policy/api/v1' + t1 + '/nat/' + natid + '/nat-rules/' + natrulename
        r = self.mp.patch(api=api, data=data, verbose=True, codes=[200])

    def deleteNatRule(self, t1, natrulename, natid="USER", display=True):
        api = '/policy/api/v1/infra/tier-1s/' + t1 + '/nat/' + natid + '/nat-rules/' + natrulename
        self.mp.delete(api=api, verbose=display, codes=[200])

    def getNatRule(self, t1, natrulename, natid="USER", display=True):
        api = '/policy/api/v1/infra/tier-1s/' + t1 + '/nat/' + natid + '/nat-rules/' + natrulename
        g = self.mp.get(api=api, verbose=display, codes=[200])
        self.jsonPrint(g)

    def listTier1NatRules(self, t1, natid="USER", display=True):
        api = '/policy/api/v1/infra/tier-1s/' + t1 + '/nat/' + natid + '/nat-rules/'
        l = self.mp.get(api=api, verbose=display, codes=[200])
        self.jsonPrint(l)

class Segments(Nsx_object):
    '''
    Class to manage Segments
    '''
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/search/query?query=resource_type:Segment'
        #self.listApi='/policy/api/v1/infra/segments'

    def getRealizedSwitch(self, name=None,path=None, display=True):
        sw = self.getRealizationEntities(name=name, path=path,display=False)
        if not sw:
            print("Segment not found")
            return None
        for s in sw['results']:
            if s['entity_type'] == 'RealizedLogicalSwitch':
                if display:
                    print(s['realization_specific_identifier'])
                return s['realization_specific_identifier']
        return None
    
    def config(self, name, tz, force, connectPath=None, admin=None, teaming=None, connect="ON",
               gw=None, dhcp=None, vlans=None, mcast=False,vni=None,desc=None):
        '''
        name - name of the segment, will be used as ID for path
        tz = name of the transportzone
        connectPath = name of the logical router if connecting upstream
        gw = Gateway IP address in CIDR
        dhcp = **Grindcore - this is name of dhcp server instead of range*
        '''

        if force:
            api='/policy/api/v1/infra/segments/%s?force=true' %name
        else:
            api='/policy/api/v1/infra/segments/%s' %name
            

        preExisting = self.findByName(name=name)
        if not preExisting:
            data={}
        else:
            data = preExisting
            api='/policy/api/v1%s' % data['path']
            
        data['display_name'] = name
        if admin:
            data['admin_state'] = admin
        if tz:
            # only vlan segments require TZ.  Otherwise, default is used for overlay
            t = TransportZone(mp=self.mp)
            tzapi = ('/policy/api/v1/infra/sites/%s/enforcement-points/default/transport-zones' %
                   self.site)
            
            myTz = t.getPathByName(name=tz,
                                   api=tzapi,
                                   display=False)
            if not myTz:
                print("TZ %s not found" %tz)
                return None
            else:
                data['transport_zone_path'] = myTz

        if vlans:
            data['vlan_ids'] = vlans

        data['subnets'] = []
        if gw:
            index = 0
            '''
            if not dhcp:
                dhcp=[]
            '''
            for g in gw or []:
                subnet={}
                subnet['gateway_address'] = g
                '''
                # Deprecated in Grindcore
                i = len(dhcp)-1
                if i>=index:
                    subnet['dhcp_ranges'] = [dhcp[index]]
                index+=1
                '''
                data['subnets'].append(subnet)

        if dhcp:
            D = DhcpRelay(mp=self.mp)
            dp = D.getPathByName(name=dhcp, display=False)
            if not dp:
                print("Dhcp relay server %s not found" %dhcp)
                return None
            else:
                data['dhcp_config_path'] = dp
                
        if connectPath:
            p=self.getPathByTypeAndName(name=connectPath, types=[Tier0, Tier1],
                                        display=False)
            if not p:
                print("LogicalRouter %s not found for connect Path" %connectPath)
                return None
            else:
                data['connectivity_path'] = p
        if teaming:
            if 'advanced_config' in data:
                advcfg = data['advanced_config']
            else:
                data['advanced_config'] = {}
                advcfg = data['advanced_config']
            advcfg['uplink_teaming_policy_name'] = teaming

        if 'advanced_config' in data:
            advcfg=data['advanced_config']
        else:
            data['advanced_config'] = {}
            advcfg=data['advanced_config']
        if mcast:
            advcfg['multicast'] = True

        advcfg['connectivity'] = connect

        if vni:
            data['overlay_id'] = vni

        self.mp.patch(api=api, data=data,verbose=True, codes=[200])

    def tagSegment(self, segmentName, tags, replace=False, partial=False):
        seg = self.findByName(name=segmentName, display=False)
        if not seg:
            print("Segment %s not found" % segmentName)
            return False

        T = Tags(mp=self.mp)
        if tags:
            taglist = T.createFromSpec(spec=tags)
        else:
            taglist = {}
        if not partial:
            data = seg
        else:
            data = {}
        if replace:
            data['tags'] = taglist
        else:
            if 'tags' in seg:
                data['tags'] = seg['tags']
                data['tags'] += (taglist)
            else:
                data['tags'] = taglist
        api = '/policy/api/v1/infra/segments/%s' % segmentName
        self.mp.patch(api=api, data=data, verbose=True, codes=[200])


    def tagPort(self, segmentName, tagSpec, portName=None, replace=False, glob=False):
        print("looking for %s" %segmentName)
        sp = self.getPathByName(name=segmentName, display=False)
        if not sp:
            print("Segment %s not found" %segmentName)
            return False

        P = SegmentPort(mp=self.mp, segmentPath=sp)
        ports = P.list(display=False)['results']
        for i in ports:
            if portName:
                if glob and portName in i['display_name']:
                    P.tag(portPath=i['path'], tagSpec=tagSpec, portData=i,replace=replace)
                elif portName == i['display_name']:
                    P.tag(portPath=i['path'], tagSpec=tagSpec, portData=i,replace=replace)
                    break
                else:
                    continue
            else:
                P.tag(portPath=i['path'], tagSpec=tagSpec, portData=i,replace=replace)

    def deletePort(self, segmentName, portName=None, portPath=None, glob=False):
        print("looking for %s" %segmentName)
        sp = self.getPathByName(name=segmentName, display=False)
        if not sp:
            print("Segment %s not found" %segmentName)
            return False

        P = SegmentPort(mp=self.mp, segmentPath=sp)
        ports = P.list(display=False)['results']
        for i in ports:
            papi = '/policy/api/v1%s' % i['path']
            if portPath and i['path'] == portPath:
                self.mp.delete(api=papi, verbose=True)
                break
            elif portName:
                if glob and portName in i['display_name']:
                    self.mp.delete(api=papi, verbose=True)
                elif portName == i['display_name']:
                    self.mp.delete(api=papi, verbose=True)
                    break

        
class SegmentPort(Nsx_object):
    def __init__(self, mp, segmentName=None, segmentPath=None):
        super(self.__class__, self).__init__(mp=mp)
        # name will only be used if path is not supplied
        self.segmentPath=segmentPath
        if not segmentPath:
            if not segmentName:
                raise ValueError("Cannot instantiate SegmentPort without segment Name or path")
            S = Segments(mp=self.mp)
            self.segmentPath = S.getPathByName(name=segmentName, display=False)
            if not self.segmentPath:
                raise ValueError("Cannot find segment %s" %segmentName)
        self.listApi='/policy/api/v1'+ self.segmentPath+'/ports'

    def config(self, name, vif=None, tagspec=None):
        tags=None
        if tagspec:
            T = Tags(mp=self.mp)
            tags=T.createFromSpec(spec=tagspec)

        data={}
        data['display_name'] = name
        if vif:
            data['attachment'] = {'id': vif}
        if tags:
            data['tags'] = tags
        api=self.listApi + '/%s' % name.replace(' ', '_')
        self.mp.patch(api=api,data=data,verbose=True,codes=[200])

    def tag(self, portPath, portData, tagSpec,  replace):
        tags = None
        T = Tags(mp=self.mp)
        tags=T.createFromSpec(spec=tagSpec)
        print("path: %s, name: %s, tags: %s" %(portPath, portData['display_name'], tags))
        if 'tags' in portData.keys():
            if replace:
                portData['tags'] = tags
            else:
                portData['tags'] += tags
        else:
            portData['tags'] = tags
        api='/policy/api/v1'+portPath
        self.mp.patch(api=api,data=portData,verbose=True,codes=[200])
        
class IpPool(Nsx_object):
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/infra/ip-pools'
        
    def getSubnets(self, name, display=True):
        p = self.getPathByName(name=name,display=False)
        if not p:
            print("IP Pool of name %s not found" %name)
            return None
        api="/policy/api/v1%s/ip-subnets" % p
        return self.mp.get(api=api,verbose=display,display=display)

    def getPoolId(self, name, display=True):
        pr = self.getRealizationEntities(name=name, display=False)
        if not pr or pr['result_count'] == 0:
            return None
        for i in pr['results']:
            if i['display_name'] == name:
                return i['realization_specific_identifier']
        return None
    
    def config(self,name,cidr,ranges,rangeName,gateway,dns=None,domain=None,addrType=None):

        print('addrType=%s' %addrType) 
        api='/policy/api/v1/infra/ip-pools/%s' %name
        data={}
        data['display_name'] = name
        self.mp.patch(api=api, data=data,verbose=True, codes=[200])        


        if addrType=='range':
            data={}
            api='/policy/api/v1/infra/ip-pools/%s/ip-subnets/%s' %(name,rangeName)
            data['display_name'] = rangeName
            data['allocation_ranges']=[]
            for r in ranges:
                print(r)
                start,end = r.split('-')
                data['allocation_ranges'].append({'start':start,'end':end})
            data['cidr'] = cidr
            data['gateway_ip'] = gateway
            data['resource_type'] = 'IpAddressPoolStaticSubnet'
            if dns:
                data['dns_nameservers'] = dns
            if domain:
                data['dns_suffix'] = domain
            data['parent_path'] = '/infra/ip-pools/%s' %name
            self.mp.patch(api=api, data=data,verbose=True, codes=[200])       

class ComputeManager(Nsx_object):
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/api/v1/fabric/compute-managers'
        
    def register(self, svrName, server, username, password,
                 thumbprint=None,trust=True,svrType='vCenter'):
    
        d = self.findByName(name=svrName, display=False)
        if d:
            data=d
        else:
            data={}
            
        data['display_name'] = svrName or server
        data['server'] = server
        data['origin_type'] = svrType
        if not d:
            data['credential'] = {}
        data['credential']['credential_type'] = 'UsernamePasswordLoginCredential'
        data['credential']['username'] = username
        data['credential']['password'] = password
        if thumbprint:
            data['credential']['thumbprint'] = thumbprint

        if trust:
            data['set_as_oidc_provider'] = trust
            
        if d:
            apip='/api/v1/fabric/compute-managers/%s' % d['id']
            r = self.mp.put(api=apip, data=data, verbose=True)
        else:
            api='/api/v1/fabric/compute-managers'
            r = self.mp.post(api=api, data=data, verbose=True)
        if 'error_code' in r and r['error_code'] == 7057:
            data['credential']['thumbprint'] = r['error_data']['ValidCmThumbPrint']
            if d:
                r = self.mp.put(api=apip, data=data,verbose=True,codes=[200])
            else:
                r = self.mp.post(api=api,data=data,verbose=True, codes=[201])

    def listClusters(self, vc=None, display=True):
        api='/api/v1/fabric/compute-collections'
        if vc:
            vcObj = self.findByName(name=vc)
            if not vcObj:
                print("Compute Manager %s not found" % vc)
                return None
            else:
                api='%s?origin_id=%s' %(api, vcObj['id'])
        return self.list(api=api,display=display)
    def findCluster(self, cluster, vc=None, display=True):
        api='/api/v1/fabric/compute-collections'
        if vc:
            vcObj = self.findByName(name=vc, display=False)
            if not vcObj:
                print("Compute Manager %s not found" % vc)
                return None
            else:
                api='%s?origin_id=%s' %(api, vcObj['id'])
        return self.findByName(api=api, name=cluster, display=display)

    def findClusterId(self, cluster, vc=None, display=True):
        r = self.findCluster(cluster=cluster, vc=vc, display=False)
        if not r:
            print("Cluster %s not found"%cluster)
            return None
        else:
            if display:
                print(r['external_id'])
            return r['external_id']

    def listStorage(self, cluster, vc=None, display=True):
        c = self.findClusterId(cluster=cluster, vc=vc, display=False)
        if not c:
            return None
        api='/api/v1/fabric/compute-collections/%s/storage-resources' % c
        return self.list(api=api, display=display)
        
    def findStorage(self, cluster, name, vc=None,display=True):
        c = self.findClusterId(cluster=cluster, vc=vc, display=False)
        if not c:
            return None

        '''
        {
        "free_space" : 101032394752,
        "multiple_host_access" : false,
        "connection_status" : "CONNECTED",
        "target_type" : "Datastore",
        "target_id" : "datastore-19",
        "name" : "datastore1 (3)"
        }
        '''
        api='/api/v1/fabric/compute-collections/%s/storage-resources' % c
        r = self.list(api=api,display=False)
        for n in r['storage_resources']:
            if n['name'] == name:
                if display:
                    self.jsonPrint(n)
                return n


    def listNetworks(self, cluster, vc=None,storage=None,display=True):
        c = self.findClusterId(cluster=cluster, vc=vc, display=False)
        if not c:
            return None

        if storage:
            api=('/api/v1/fabric/compute-collections/%s/network-resources?storage_id=%s'
                 % (c, storage))
        else:
            api=('/api/v1/fabric/compute-collections/%s/network-resources' % c)

        r = self.list(api=api, display=display)
        
    def findNetwork(self, cluster, name, vc=None, storage=None, display=True):
        '''
        pre-3.0, the ?storage_id is required in the api
        
        {
        "network_resource" : {
        "name" : "DVS1-EdgeTrunkLeft",
        "target_type" : "DistributedVirtualPortgroup",
        "target_id" : "dvportgroup-26"
        },
        "discovered_nodes" : [ "0cde762e-819f-44cf-a8f1-488c4a9e62c9:host-16" ]
        }

        This only returns non NSX Networks
        '''
        c = self.findClusterId(cluster=cluster, vc=vc, display=False)
        if not c:
            return None

        if storage:
            api=('/api/v1/fabric/compute-collections/%s/network-resources?storage_id=%s'
                 % (c, storage))
        else:
            api=('/api/v1/fabric/compute-collections/%s/network-resources' % c)

        r = self.list(api=api, display=False)
        for n in r['network_resources_hosts']:
            if n['network_resource']['name'] == name:
                if display:
                    self.jsonPrint(n)
                return n
        return None
            
class Appliance(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/api/v1/cluster/nodes/deployments'

    def deploy(self, hostname,
               size,
               roles,
               password, 
               vc,
               cluster,
               rootssh,
               ssh,
               gateway,
               cidr,
               network,
               dns,
               dnssearch,
               ntp,
               diskprovisioning,
               storage):

        data={}
        data['form_factor'] = size
        data['roles'] = roles

        usersetting={}
        usersetting['audit_username'] = 'audit'
        usersetting['cli_username'] = 'admin'
        usersetting['audit_password'] = password
        usersetting['root_password'] = password
        usersetting['cli_password'] = password
        data['user_settings'] = usersetting

        # BEGIN Deployment config
        config={}
        config['enable_ssh'] = ssh
        config['allow_ssh_root_login'] = rootssh

        CM=ComputeManager(mp=self.mp)
        v = CM.getIdByName(name=vc, display=False)
        if not v:
            print("VCenter %s not found" %vc)
            return None
        config['vc_id'] = v

        c = CM.findClusterId(cluster=cluster,vc=vc, display=False)
        if not c:
            print("Cluster %s not found" %cluster)
            return None
        config['compute_id'] = c

        n = CM.findNetwork(cluster=cluster, vc=vc, name=network, display=False)
        if not n:
            print("Network %s not found" %network)
            return None
        config['management_network_id'] = n['network_resource']['target_id']

        net,mask=cidr.split('/')
        subnet={'ip_addresses': [net], 'prefix_length': mask}
        config['management_port_subnets'] = [subnet]
        config['default_gateway_addresses'] = gateway

        s = CM.findStorage(cluster=cluster, name=storage, vc=vc, display=False)
        if not s:
            print("Storage %s not found." % storage)
            return None
        config['storage_id'] = s['target_id']
        config['disk_provisioning'] = diskprovisioning
        
        config['dns_servers'] = dns
        config['search_domains'] = dnssearch
        config['ntp_servers'] = ntp
        config['hostname'] = hostname
        config['placement_type'] = 'VsphereClusterNodeVMDeploymentConfig'
        # End deployment config
        data['deployment_config'] = config
        dploy_data={}
        dploy_data['deployment_requests'] = [data]

        api='/api/v1/cluster/nodes/deployments'
        return self.mp.post(api=api,data=dploy_data,verbose=True,codes=[201])

    def findByName(self, name, display=True):
        objs = self.list(display=False)
        
        for i in objs:
            if i['deployment_config']['hostname'] == name:
                if display:
                    self.jsonPrint(i)
                return i
        return None

    def getIdByName(self, name, display=True):
        n = self.findByName(name=name, display=False)
        if not n:
            if display:
                print("None")
            return None
        if display:
            print(n['deployment_config']['vm_id'])
        return n['deployment_config']['vm_id']
        
    def delete(self, name, display=True):
        id = self.getIdByName(name=name, display=False)
        if not id:
            print("Node %s not found" %name)
            return None
        api='/api/v1/cluster/nodes/deployments/%s?action=delete' % id
        return self.mp.post(api=api, data=None, verbose=True, codes=[202])
    
    
               
               
class vDS(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/api/v1/fabric/virtual-switches'
        
class ComputeCollections (Nsx_object):
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/api/v1/fabric/compute-collections'

class TNCollections (Nsx_object):
        def __init__(self,mp):
            super(self.__class__, self).__init__(mp=mp)
            self.listApi='/api/v1/transport-node-collections'

        def config(self, computecollection, tnprofile, name=None, desc=None):
            '''
            name = name of this TNCollection
            desc = Description of TNCollection
            compute-collection =  name of vc-cluster to configure
            transport-node-profile = name of TN-Profile to configure compute-collection
            '''
            data = {}
            data['display_name'] = name
            data['resource_type'] = 'TransportNodeCollection'
            if desc:
                data['description'] = desc

            if computecollection:
                C = ComputeCollections(mp=self.mp)
                c = C.findByName(name=computecollection, display=False)
                data['compute_collection_id'] = c['external_id']

                if not c:
                    print("Compute-Collection %s not found" %computecollection)
                    return None
                                            
            if tnprofile:
                T = TNProfile(mp=self.mp)
                t = T.findByName(name=tnprofile, display=False)
                if not t:
                    print("Transport node profile %s not found" %tnprofile)
                    return None
                data['transport_node_profile_id'] = t['id']
                
                if not t:
                    print("TN Profile %s not found" %tnprofile)
                    return None
            if removeTnp:
                del data['transport_node_profile_id']
            api='/api/v1/transport-node-collections'
            r = self.mp.post(api=api,data=data,verbose=True, codes=[201])

        def detachTnp(self, name):
            C = ComputeCollections(mp=self.mp)
            cluster = C.findByName(name=name, display=False)
            if not cluster:
                print("Cluster %s not found" % name)
                return
            tnc =self.findByName(name=cluster['external_id'],
                                field='compute_collection_id',
                                display=False)
            if not tnc:
                print("Transport node collection not found for cluster %s" %name)
                return
            api='/api/v1/transport-node-collections/%s' %tnc['id']
            r = self.mp.delete(api=api, data=tnc, verbose=True, codes=[200])
class Certificate(Nsx_object):
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/infra/certificates'


    def readCert(self,filename):
        fp=open(filename,'r')
        return fp.read()

    def importMpCertificate(self, name, cert, key=None, passphrase=None,description=None):
        data={}
        data['display_name'] = name
        if description:
            data['description'] = description
        if passphrase:
            data['passphrase'] = passphrase
        if key:
            data['private_key'] = self.readCert(filename=key)
        data['pem_encoded'] = self.readCert(filename=cert)
        restUrl='/api/v1/trust-management/certificates?action=import'
        r = self.mp.post(api=restUrl, data=data, verbose=True, codes=[201])
        
    def importCertificate(self, name, cert, key=None,passphrase=None,
                          service=False, description=None):

        if not service:
            return self.importMpCertificate(name=name, cert=cert, key=key,
                                            passphrase=passphrase,
                                            description=description)
        data={}
        data['display_name'] = name
        if description:
            data['description']= description
        if passphrase:
            data['passphrase'] = passphrase
        if key:
            data['private_key'] = self.readCert(filename=key)
        data['pem_encoded'] = self.readCert(filename=cert)

        api='/policy/api/v1/infra/certificates/%s'%name

        return self.mp.patch(api=api,data=data,verbose=True, codes=[200])

    def applyHttpCert(self,name):
        cert = self.findByName(name=name,api='/api/v1/trust-management/certificates',
                               display=False)

        if not cert:
            print("Certificate %s not found" %name)
        else:
            restUrl='/api/v1/node/services/http?action=apply_certificate&certificate_id=%s'\
                %cert['id']
            self.mp.post(api=restUrl,
                         data=None,verbose=True,codes=[200])


    def setAphCert(self, node, cert):
        N = Cluster(mp=self.mp)
        n = N.findByName(name=node, display=False)
        if not n:
            print("Node %s not found" %node)
            return False

        C = Certificate(mp=self.mp)
        c = C.findByName(name=cert, api='/api/v1/trust-management/certificates',
                         display=False)
        if not c:
            print("Certificate %s not found" %cert)
            return False

        api='/api/v1/trust-management/certificates?action=set_appliance_proxy_certificate_for_inter_site_communication'
        data={}
        data['cert_id'] = c['id']
        data['used_by_id'] = n['node_uuid']
        self.mp.post(api=api, data=data, verbose=True, codes=[200])
        
        
class Realization(Nsx_object):
    '''
    Realization currently will only support global alarms list retrieval
    Do not add individual entity alarms here, as those should be done in the
    class of the entity
    '''
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/infra/realized-state/alarms'
        
    def cleanup(self, path):
        data={}
        data['paths'] = [path]
        api='/policy/api/v1/troubleshooting/infra/tree/realization?action=cleanup'
        r = self.mp.post(api=api, data=data, verbose=True)
        
    def systemList(self):
        api='/policy/api/v1/search?query=(_exists_:status AND !status.consolidated_status.consolidated_status:SUCCESS)'
        r = self.mp.get(api=api,verbose=True)
        self.jsonPrint(r)
        
        
    

class Roles(Nsx_object):
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/aaa/roles'

    def findByName(self, name, data=None,display=False):
        r = self.list(display=False)
        for i in r['results']:
            if i['role'] == name:
                return True

        return False
            
    def bind(self, name, roles, utype='remote_user', display=False):
        data={}
        data['name'] = name
        data['display_name'] = name
        data['type'] = utype
        data['resource_type'] = 'RoleBinding'
        data['roles'] = []
        for i in roles:
            role={}
            role['role'] = i
            data['roles'].append(role)
            
        self.mp.post(api='/policy/api/v1/aaa/role-bindings', data=data,
                  codes=[200], verbose=True)
        

class Vidm(Nsx_object):
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/api/v1/node/aaa/providers/vidm'


    def __getCertificate(self, node, port=443):
        c = ssl.get_server_certificate(addr=(node, port))
        return c

    def getFingerprint(self, node, port=443, digest='sha256'):
        '''
        digest options are sha1 and sha256
        '''
        c =  self.__getCertificate(node=node, port=port)
        x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, c)
        return x509.digest(digest).decode("utf-8")
        
        
        
    def config(self, vidmhost, client, secret,
               nodename, enable=False, lb=False):
        data={}
        data['host_name'] = vidmhost
        data['client_id'] = client
        data['client_secret'] = secret
        data['vidm_enable'] = enable
        data['lb_enable'] = lb
        data['node_host_name'] = nodename
        data['thumbprint'] = self.getFingerprint(node=vidmhost, port=443)
        r=self.mp.put(api='/api/v1/node/aaa/providers/vidm', data=data,
                      verbose=True, codes=[202,200])

    def getStatus(self):
        self.mp.get(api='/api/v1/node/aaa/providers/vidm/status', verbose=True, display=True)

                
class PrincipalIdentity(Nsx_object):
    '''
    Not a policy object...
    '''

    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/api/v1/trust-management/principal-identities'
    

    def create(self, name, nodeid, role=None, desc=None,cert=None,isprotected=False):
        data={}
        data['name'] = name
        data['display_name'] = name
        data['node_id'] = nodeid
        if desc:
            data['description'] = desc
        if cert:
            C = Certificate(mp=self.mp)
            crt = C.readCert(filename=cert)
            if not crt:
                print("Certificate with name %s read error" %cert)
                return None
            else:
                data['certificate_pem'] = crt
        if role:
            data['role'] = role
        if isprotected:
            data['is_protected'] = True
        else:
            data['is_protected'] = False
        
        R = Roles(mp=self.mp)
        if R.findByName(name=role, display=False):
            data['role'] = role
        else:
            print("Invalid role name %s specified" %role)
            return None

        data['resource_type'] = 'PrincipalIdentifyWithCertificate'
         
            
        api='/api/v1/trust-management/principal-identities/with-certificate'
        r = self.mp.post(api=api, data=data, verbose=False, codes=[201])
        return r
            
            
        
    def deletePi(self, name, display=True):
        pi=self.findByName(name=name,display=False)
        if not pi:
            print("Principal identity %s not found" %name)
            return False


        api='/api/v1/trust-management/principal-identities/%s' % pi['id']
        r = self.delete(api=api,verbose=display)
        
        
class DhcpRelay(Nsx_object):
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/search/query?query=resource_type:DhcpRelayConfig'
        self.objApi='/policy/api/v1/infra/dhcp-relay-configs'
    def config(self, name, servers):
        api=self.objApi+'/%s'%name
        data={}
        data['server_addresses'] = servers
        r = self.mp.patch(api=api, data=data,verbose=True,codes=[200])
        
class Domain(Nsx_object):
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/infra/domains'

    def config(self, name, desc=None):
        data={}
        data['display_name'] = name
        if desc:
            data['description'] = desc

        api='/policy/api/v1/infra/domains/%s' % name
        r = self.mp.patch(api=api,data=data,verbose=True, codes=[200])


class Group(Nsx_object):
    def __init__(self, mp, domain='default'):
        super(self.__class__, self).__init__(mp=mp)
        if domain:
            self.domain = domain
        else:
            self.domain = 'default'
        #self.listApi='/policy/api/v1/infra/domains/%s/groups' % self.domain
        self.listApi='/policy/api/v1/search/query?query=resource_type:Group'

    def __addToExpressions(self, expr, data, conjunction):
        if len(expr) == 0:
            expr.append(data)
        else:
            expr.append(conjunction)
            expr.append(data)
            
    def __handleSegments(self, segments, expr, conjunction):
        s = Segments(mp=self.mp)
        data={}
        data['resource_type'] = 'PathExpression'
        data['paths'] = []
        for n in segments:
            curS = s.getPathByName(name=n, display=False)
            if not curS:
                raise ValueError("Segment %s not found" %n)
            data['paths'].append(curS)
        if len(data['paths']) == 0:
            raise ValueError("No valid segments found to add, spec: %s:" %segments)
        self.__addToExpressions(expr=expr, data=data,
                                conjunction=conjunction)
    def __handleGroups(self, groups, expr, conjunction):
        data={}
        data['resource_type'] ='PathExpression'
        data['paths'] = []
        for n in groups:
            curG = self.getPathByName(name=n, display=False)
            if not curG:
                raise ValueError("Group %s not found" %g)
            data['paths'].append(curG)
        if len(data['paths']) == 0:
            raise ValueError("No valid groups found to add, spec: %s:" %segments)
        self.__addToExpressions(expr=expr, data=data,
                                conjunction=conjunction)

    def __handleVms(self, vms, expr, conjunction):
        data={}
        data['resource_type'] = 'ExternalIDExpression'
        data['member_type'] = 'VirtualMachine'
        data['external_ids'] = []
        for n in vms:
            api = '/api/v1/search?query=(resource_type:VirtualMachine AND display_name:%s)' %n
            v = self.findByName(api=api,name=n, display=False)
            if not v:
                raise ValueError("VM %s not found" %n)
            data['external_ids'].append(v['external_id'])
        if len(data['external_ids']) == 0:
            raise ValueError("No valid VMs found to ad, spec: %s" %vms)
        self.__addToExpressions(expr=expr, data=data, conjunction=conjunction)
            
    def __handleVifs(self, vifs, expr, conjunction):
        data={}
        data['resource_type'] = 'ExternalIDExpression'
        data['member_type'] = 'VirtualNetworkInterface'
        data['external_ids'] = []
        for n in vifs:
            # first find the VM
            api = '/api/v1/search?query=(resource_type:VirtualMachine AND display_name:%s)' %n
            v = self.findByName(api=api,name=n,display=True)
            if not v:
                raise ValueError("VM %s not found to retreive VIFs: %s" %(n,vifs))
            api='/api/v1/search?query=(resource_type:VirtualNetworkInterface '\
                'AND owner_vm_id:%s)' %v['external_id']
            r = self.list(api=api,display=False)
            for i in r['results']:
                data['external_ids'].append(i['external_id'])

        if len(data['external_ids']) == 0:
            raise ValueError("No valid VMs found to add, spec: %s" %vifs)
        self.__addToExpressions(expr=expr, data=data, conjunction=conjunction)
            

    def __handleIpAddrs(self, ips, expr, conjunction):
        data={}
        data['resource_type'] = 'IPAddressExpression'
        data['ip_addresses'] = []
        for i in ips:
            data['ip_addresses'].append(i)
        if len(data['ip_addresses']) == 0:
            raise ValueError("No valid IP adddress to add, spec: %s" %ips)
        self.__addToExpressions(expr=expr, data=data, conjunction=conjunction)
    def __handleMacAddrs(self, macs, expr, conjunction):
        data={}
        data['resource_type'] = 'MACAddressExpression'
        data['mac_addresses'] = []
        for i in macs:
            data['mac_addresses'].append(i)
        if len(data['mac_addresses']) == 0:
            raise ValueError("No valid mac adddress to add, spec: %s" %macs)
        self.__addToExpressions(expr=expr, data=data, conjunction=conjunction)

    def getConsolidatedEffectiveMembers(self, name, site=None, siteid=None, display=True):
        if site:
            S=Sites(mp=self.mp)
            s = S.findByName(name=site, display=False)
            if not s:
                print("Site %s not found.  Note that LM cannot find other sites, use siteID")
                return None
            if siteid and siteid != s['unique_id']:
                print("Site %s found with ID %s, but different than provided site ID %s"
                      % (site, s['unique_id'], siteid))
                return None

            siteid = s['unique_id']

        gp = self.getPathByName(name=name, display=False)
        if not gp:
            print("Group %s not found" %name)
            return None

        api='/policy/api/v1' + gp + '/members/consolidated-effective-ip-addresses'
        if siteid:
            api=api+"?site_id="+siteid
        # need to change this to list after finalized changes for API
        data=self.mp.get(api=api, display=True)
        
    def config(self, name,  domain='default',
               expressions=None,
               vifs=None,
               vms=None,
               ipaddrs=None,
               macaddrs=None,
               ports=None,
               segments=None,
               groups=None,
               tags=None):
        '''
        expressions: "expr" [[expr] [..]]
              -One or more expr
        
        expr: "conjunction:member_type:key:operator:value [,:member_type,key:operator:value][..]
               Seperate condition expressions with commans to create nested conditions
          conjunction: AND or OR,
                        if AND, the two member_type being AND'ed must be same
                        When empty, implies OR when nesting, AND when nesting
          member_type: VirtualMachine, IPSet, LogicalPort, LogicalSwitch
          key:
                 if member_type == VirtualMachine:
                      Name, OSName, ComputerName, Tag
                 else:
                      Tag
          operator: EQUALS, CONTAINS, STARTSWITH, ENDSWITH, NOTEQUALS
          value: value to match
        ipaddrs: List of IP addresses, each one can be range
        macaddrs: List of MAC addresses
        vifs: List of VIFs by VIF UUID
        vms: List of VMs by VM UUID
        ports: List of segment ports by path ID
        groups: List of groups by path ID

        '''
        OR={}
        OR['conjunction_operator'] = 'OR'
        OR['resource_type'] = 'ConjunctionOperator'

        AND={}
        AND['conjunction_operator'] = 'AND'
        AND['resource_type'] = 'ConjunctionOperator'
        
        nsgroup={}
        nsgroup['display_name'] = name
        nsgroup['expression'] = []
        if expressions:
            for e in expressions:
                exps = e.split(',')

                if len(exps) > 1:
                    nest={}
                    nest['resource_type'] = 'NestedExpression'
                    nest['expressions'] = []
                    nsgroup['expression'].append(nest)
                    addTo=nest['expressions']
                    nesting = True
                else:
                    addTo=nsgroup['expression']
                    nesting = False

                for c in exps:
                    conditions=c.split(':')
                    if len(conditions) != 5:
                        raise ValueError("Condition %s not in correct format" %c)

                    # Process conjunction.  If first element in nested expression
                    # or first expression, ignore it.  Nested conjunction must be AND
                    conjunction = conditions[0].strip().upper()
                    if conjunction not in ['', 'OR','AND']:
                        raise ValueError("Conjunction not empty, AND, OR: %s" %c)
                    if nesting:
                        if conjunction == 'OR' and len(addTo) != 0:
                            raise ValueError("Nested conjunction must be AND: %s" %c)
                        elif len(addTo) != 0:
                            addTo.append(AND)
                    else:
                        if len(addTo) > 0 and conjunction in ['', 'OR']:
                            addTo.append(OR)
                        elif len(addTo) > 0 and conjunction == 'AND':
                            addTo.append(AND)

                    currentExpr = {}
                    mtype=conditions[1].strip().lower()
                    if mtype == 'ipset':
                        currentExpr['member_type'] = 'IPSet'
                    elif mtype == 'virtualmachine':
                        currentExpr['member_type'] = 'VirtualMachine'
                    elif mtype == 'logicalport':
                        currentExpr['member_type'] = 'LogicalPort'
                    elif mtype == 'logicalswitch':
                        currentExpr['member_type'] = 'LogicalSwitch'
                    else:
                        raise ValueError("Expression member type must be one of "
                                         "IPSet, VirtualMachine, LogicalPort, "
                                         "LogicalSwitch: %s" %c)

                    key = conditions[2].strip().lower()
                    if mtype in ['ipset', 'logicalport', 'logicalswitch']:
                        if key != 'tag':
                            raise ValueError("IPSet, LogicalPort and LogicalSwitch "
                                             "matches only Tag: %s" %c)
                        else:
                            currentExpr['key'] = 'Tag'
                    else:
                        if key == 'tag':
                            currentExpr['key'] = 'Tag'
                        elif key == 'name':
                            currentExpr['key'] = 'Name'
                        elif key == 'osname':
                            currentExpr['key'] = 'OSName'
                        elif key == 'ComputerName':
                            currentExpr['key'] = 'ComputerName'
                        else:
                            raise ValueError("VirtualMachine must match on on "
                                             "Tag, Name, OSName, "
                                             "ComputerName: %s" %c)

                    operator=conditions[3].strip().upper()
                    if operator not in ['EQUALS', 'CONTAINS', 'STARTSWITH',
                                   'ENDSWITH', 'NOTEQUALS']:
                        raiseValueError("Expression operator must be one of \n"
                                        "equals, contains, startswith, endswith, notequals")


                    else:
                        currentExpr['operator'] = operator

                    if currentExpr['key'] == 'Tag':
                        currentExpr['value']  = conditions[4].strip().replace("/","|")
                    else:
                        currentExpr['value'] = conditions[4].strip()
                    currentExpr['resource_type'] = 'Condition'
                    addTo.append(currentExpr)

        if segments:
            self.__handleSegments(segments=segments, expr=nsgroup['expression'],
                                  conjunction=OR)
        if vms:
            self.__handleVms(vms=vms, expr=nsgroup['expression'],
                             conjunction=OR)
        if groups:
            self.__handleGroups(groups=groups, expr=nsgroup['expression'],
                             conjunction=OR)
        if vifs:
            self.__handleVifs(vifs=vifs, expr=nsgroup['expression'],
                             conjunction=OR)
        if ipaddrs:
            self.__handleIpAddrs(ips=ipaddrs, expr=nsgroup['expression'],
                             conjunction=OR)
        if macaddrs:
            self.__handleMacAddrs(macs=macaddrs, expr=nsgroup['expression'],
                             conjunction=OR)
        if ports:
            # not yet implimented
            pass
        
        api='/policy/api/v1/infra/domains/%s/groups/%s' % (domain,name)
        self.mp.patch(api=api,data=nsgroup, verbose=True,codes=[200])

    def getVmMembers(self, name, domain='default'):
        path=self.getPathByName(name=name,display=False)
        if not path:
            print("Group %s not found" %name)
            return None
        E=EnforcementPoints(mp=self.mp)
        epath=E.getPathByName(name='default', display=False)
        api=('/policy/api/v1%s/members/virtual-machines?enforcement_point_path=%s'
             %(path, epath))
        r = self.mp.get(api=api,verbose=True,codes=[200])
        print("VM members of group %s, count: %d:" %(name, r['result_count']))
        for i in r['results']:
            print("   %s" %i['display_name'])
        
    def getIpMembers(self, name, domain='default'):
        path=self.getPathByName(name=name,display=False)
        if not path:
            print("Group %s not found" %name)
            return None
        E=EnforcementPoints(mp=self.mp)
        epath=E.getPathByName(name='default', display=False)
        api=('/policy/api/v1%s/members/ip-addresses?enforcement_point_path=%s'
             %(path, epath))
        r = self.mp.get(api=api,verbose=True,codes=[200])
        self.jsonPrint(r)
        
class Service(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/infra/services'
    def configL4PortService(self, name, entries,desc=None):
        #s = self.findByName(name=name, display=False)
        s=None
        if s:
            data=s
        else:
            data={}
            
        if desc:
            data['description'] = desc
        data['resource_type'] = 'Service'

        # delete current ones
        data['service_entries'] = []
        for entry in entries:
            # name:proto:srcPort:dstPort
            ename,proto,srcPorts,dstPorts = entry.split(':')
            e={}
            e['display_name'] = ename
            if srcPorts.strip() != '':
                e['source_ports'] = srcPorts.strip().split()
            if dstPorts.strip() != '':
                e['destination_ports'] = dstPorts.strip().split()

            e['l4_protocol'] = proto.upper()
            if e['l4_protocol'] not in ['UDP', 'TCP']:
                print("Service Entry %s does not have correct UDP/TCP protocol"
                      %entry)
                return None

            e['resource_type'] = "L4PortSetServiceEntry"
            data['service_entries'].append(e)
        api='/policy/api/v1/infra/services/%s' % name
        return self.mp.patch(data=data, api=api, verbose=True, codes=[200])
    
class SecurityPolicy(Nsx_object):
    def __init__(self, mp, domain='default'):
        super(self.__class__, self).__init__(mp=mp)
        if domain:
            self.domain = domain
        else:
            self.domain = 'default'
        self.listApi='/policy/api/v1/infra/domains/%s/security-policies' % self.domain
        self.listApi='/policy/api/v1/search/query?query=resource_type:SecurityPolicy'
    def config(self, name, domain='default', category='Application', scope=None,
               stateless=False, tcpstrict=False, connectivity="NONE",
               sequence=None,desc=None):

        data={}
        data['display_name'] = name
        data['category'] = category
        if desc:
            data['description'] = desc
        if stateless:
            data['stateful'] = False
        else:
            data['stateful'] = True
        if tcpstrict:
            data['tcp_strict'] = True
        if sequence:
            data['sequence_number'] = sequence
        data['connectivity_strategy'] = connectivity
        if scope:
            G = Group(mp=self.mp)
            data['scope']=[]
            for g in scope:
                p = G.getPathByName(name=g, display=False)
                if not p:
                    print("Group %s not found" % g)
                    return None
                data['scope'].append(p)

        api='/policy/api/v1/infra/domains/%s/security-policies/%s' %(domain,name)
        #api="%s?action=revise&operation=insert_bottom" %api
        self.mp.patch(api=api,data=data,verbose=True,codes=[200])
        #self.mp.post(api=api,data=data,verbose=True,codes=[200])
    def getStats(self, name, rule=None, display=True):
        myPath=self.getPathByName(name=name, display=False)
        if not myPath:
            print("Security Policy %s not found" %name)
            return None

        if rule:
            R=Rule(mp=self.mp, policy=name)
            rId=R.getIdByName(name=rule)
            if not rId:
                print("Rule %s not found in Policy %s" %(rule, name))
                return None
            api=('/policy/api/v1%s/rules/%s/statistics'
                 %(myPath, rId))
        else:
            api=('/policy/api/v1%s/statistics' %myPath)

        r = self.mp.get(api=api,verbose=display)
        if display:
            self.jsonPrint(r)
        return r
                 

        
        
    def position(self, name, domain='default', operation='insert_top',
                 anchor=None, anchordomain='default'):
        thisPath = self.getPathByName(name=name, display=False)
        if not thisPath:
            raise ValueError("Security Policy '%s' not found" %name)
        # why is data required on position change?  PR2332363
        thisData = self.findByName(name=name,display=False)
        if anchor:
            aObj=SecurityPolicy(mp=self.mp,domain=anchordomain)
            anchorPath=aObj.getPathByName(name=anchor, display=False)
        else:
            anchorPath=None

        if not anchorPath and operation in ['insert_before','insert_after']:
            raise ValueError("An anchor must be provided for insert bvefore/after")

        api='/policy/api/v1%s?action=revise' % (thisPath)
        operation='&operation=%s' %operation
        if anchorPath:
            anchorPosition='&anchor_path=%s' % anchorPath
            fullApi="%s%s%s" %(api,operation,anchorPosition)
        else:
            fullApi="%s%s" %(api,operation)

        self.mp.post(api=fullApi,data=thisData,verbose=True,codes=[200])


    def delete(self, name):
        path=self.getPathByName(name=name, display=False)
        if not path:
            print("Security policy %s not found" %name)
            return
            
        api='/policy/api/v1%s'%path
        self.mp.delete(api=api,verbose=True)

class Rule(Nsx_object):
    def __init__(self, mp, policy, domain='default'):
        super(self.__class__, self).__init__(mp=mp)
        if domain:
            self.domain = domain
        else:
            self.domain = 'default'
        p = SecurityPolicy(mp=self.mp, domain=self.domain)


        self.policyPath = p.getPathByName(name=policy, display=False)
        if not self.policyPath:
            raise ValueError("Path for policy %s not found" %policy)
        
        self.listApi='/policy/api/v1%s/rules' % self.policyPath

    def config(self, name, action, 
               src=["ANY"], dst=["ANY"],
               srcNegate=False, dstNegate=False,
               direction="IN_OUT", disabled=False,
               proto="IPV4_IPV6", log=False, services=["ANY"],
               sequence=None, scope=None):


        policydomain=self.domain
        policyPath = self.policyPath
        fullApi='/policy/api/v1%s/rules/%s' %(policyPath,name)
        data={}
        data['resource_type'] = "Rule"
        data['display_name'] = name
        data['action'] = action
        data['direction'] = direction
        data['ip_protocol'] = proto
        if sequence:
            data['sequence_number'] = sequence
        if disabled:
            data['disabled'] = True
        if log:
            data['logged']  = True
        # group format:  domain:name or name, if just name, domain is same as Rule
        data['destination_groups'] = []
        for d in dst:
            if ':' in d:
                dom,gname=d.split(":")
            else:
                dom=policydomain
                gname=d
            if gname.upper()=='ANY':
                data['destination_groups'] = ['ANY']
                break
            grp = Group(mp=self.mp, domain=dom)
            gpath=grp.getPathByName(name=gname, display=False)
            if not gpath:
                print("Path for destination group %s not found in domain %s " %(gname, dom))
                return None
            data['destination_groups'].append(gpath)

        if dstNegate:
            data['destination_excluded'] = True

        data['source_groups'] = []
        for s in src:
            if ':' in s:
                dom,gname=s.split(":")
            else:
                dom=policydomain
                gname=s
            if gname.upper()=='ANY':
                data['source_groups'] = ['ANY']
                break
            grp = Group(mp=self.mp, domain=dom)
            gpath=grp.getPathByName(name=gname, display=False)
            if not gpath:
                print("Path for source group %s not found in domain %s " %(gname, dom))
                return None
            data['source_groups'].append(gpath)

        if srcNegate:
            data['source_excluded'] = True


        data['services'] = []

        S = Service(mp=self.mp)
        for svc in services:
            if svc.upper() == 'ANY':
                data['services'] = ['ANY']
                break
            spath = S.getPathByName(name=svc, display=False)
            if not spath:
                print("Path for service %s not found" %svc)
                return
            data['services'].append(spath)
            
            
        if scope:
            data['scope']=[]
            for i in scope:
                if i=='ANY':
                    data['scope'].append('ANY')
                    break
                sType,sDomain,sValue=i.split(':')
                if sDomain.strip()=='':
                    sDomain=policydomain
                else:
                    sDomain = sDomain.strip()
                if sType.strip().lower() == 'group':
                    G = Group(mp=self.mp, domain=sDomain)
                    path=G.getPathByName(name=sValue, display=False)
                    if not path:
                        print("Path not found for group %s for applied-to spec: %s"
                              %(sValue,i))
                        return
                    data['scope'].append(path)
                elif sType.strip().lower() == 'segment':
                    S = Segments(mp=self.mp)
                    path = S.getPathByName(name=sValue, display=False)
                    if not path:
                        print("Path not found for segment %s for applied-to spec: %s"
                              %(sValue, i))
                        return
                    data['scope'].append(path)


        self.mp.patch(api=fullApi,data=data,verbose=True,codes=[200])
                

    def position(self, name, operation, anchor=None):
        thisPath=self.getPathByName(name=name, display=False)
        if not thisPath:
            raise ValueError("Rule %s not found in Policy %s in domain %s"
                             %(name, self.policyPath, self.domain))
        thisData = self.findByName(name=name,display=False)

        if anchor:
            anchorPath=self.getPathByName(name=anchor, display=False)
        else:
            anchorPath=None

        if not anchorPath and operation in ['insert_before', 'insert_after']:
            raise ValueError("An anchor must be provided for insert before/after")
        api='/policy/api/v1%s?action=revise' % thisPath
        operation='&operation=%s' % operation
        if anchorPath:
            anchorPosition='&anchor_path=%s' % anchorPath
            fullApi = '%s%s%s' %(api,operation,anchorPosition)
        else:
            fullApi = '%s%s' %(api,operation)

        self.mp.post(api=fullApi,data=thisData,verbose=True,codes=[200])
            
    def delete(self, name):
        path=self.getPathByName(name=name, display=False)
        if not path:
            print("Security policy %s not found" %name)
            return
            
        api='/policy/api/v1%s'%path
        self.mp.delete(api=api,verbose=True)
        
class Tags(Nsx_object):
    def createFromSpec(self,spec):
        '''
        spec: [<scope>:<tag name>]
        if <scope>: not given, value is consider tagname with no scope
        '''
        tagsList = []
        if not spec:
            return tagsList
        for i in spec:
            vals=i.split(':')
            if len(vals) == 1:
                tagsList+=self.createFromList(tagnames=[vals[0]])
            elif len(vals) == 2:
                tagsList+=self.createFromList(tagnames=[vals[1]],
                                                    scope=vals[0])
            else:
                raise ValueError('Incorrect tag spec format: %s' %i)
        return tagsList

    def convertToSpec(self,tags,display=False):
        specList = []
        for t in tags:
            spec=''
            if 'scope' in t:
                spec='%s:' %t['scope']
            else:
                spec=':'
            if 'tag' in t:
                spec+='%s' %['tag']
            else:
                spec+=''
            specList.append(spec)
        if display:
            for s in specList:
                print(s, end=' ')
            print ('')
        return specList


    def createFromList(self,tagnames,scope=None):
        tags = []
        for n in tagnames:
            tag={}
            if scope:
                tag['scope']=scope
            tag['tag'] = n
            tags.append(tag)

        if len(tags) > 0:
            return tags
        else:
            return None

    def removeTags(self, source, dels):
        return [item for item in source if item not in dels]
        
class VirtualMachine(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi = '/policy/api/v1/infra/realized-state/enforcement-points/%s/virtual-machines' % self.ep

    def tag(self, vmname, tags, replace=False):
        vm = self.findByName(name=vmname, display=False)
        if not vm:
            print("VM %s not found" % vmname)
            return

        T=Tags(mp=self.mp)
        if tags:
            taglist = T.createFromSpec(spec=tags)
        else:
            taglist=[]
        data={}
        data['virtual_machine_id'] = vm['external_id']
        if replace:
            data['tags'] = taglist
        else:
            if 'tags' in vm:
                data['tags'] = vm['tags']
                data['tags']+=(taglist)
            else:
                data['tags'] = taglist
            
        api='/policy/api/v1/infra/realized-state/enforcement-points/%s/virtual-machines?action=update_tags' % self.ep
        self.mp.post(api=api,data=data,codes=[204], verbose=True)

class LoadBalancer(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi = '/policy/api/v1/infra/lb-services'

    def config(self, name, size=None, tier1=None,
               loglevel='INFO', disable=False):
        data={}
        data['display_name'] = name
        if tier1:
            T=Tier1(mp=self.mp)
            t1path=T.getPathByName(name=tier1,display=False)
            if not t1path:
                print("Tier1 %s not found" %tier1)
                return None
            else:
                data['connectivity_path'] = t1path

        if disable:
            data['enabled'] = False
        else:
            data['enabled'] = True
        if loglevel:
            data['error_log_level'] = loglevel
        if size:
            data['size'] = size
        data['resource_type'] = 'LBService'

        api='/policy/api/v1/infra/lb-services/%s' %name
        self.mp.patch(api=api,data=data,verbose=True)

    def status(self, name, opType='stats', source='cached', display=True):
        myPath=self.getPathByName(name=name,display=False)
        if not myPath:
            print("LB service %s not found" %name)
            return None
        if opType=='usage':
            opType='service-usage'
        elif opType=='status':
            opType='detailed-status'
        else:
            opType='statistics'
        api='/policy/api/v1%s/%s' %(myPath, opType)
        r= self.mp.get(api=api, verbose=True)
        if display:
            self.jsonPrint(r)
        return r
    def getPoolStatus(self, name, pool, opType="stats", source='cached',display=True):
        '''
        
        opType: status, stats
        '''
        myPath=self.getPathByName(name=name,display=True)
        if not myPath:
            print("LB service %s not found" %name)
            return None
        P=LBPool(mp=self.mp)
        pId=P.getIdByName(name=pool, display=False)
        if not pId:
            print("LB Pool %s not found" %pool)
            return None
        if opType=='status':
            opType='detailed-status'
        else:
            opType='statistics'
        api='/policy/api/v1%s/lb-pools/%s/%s?source=%s' %(myPath,pId, opType, source)
        r=self.mp.get(api=api,verbose=True)
        if display:
            self.jsonPrint(r)
        return r

    def getVipStatus(self, name, vip, opType='cached', source='cached', display=True):
        myPath=self.getPathByName(name=name,display=False)
        if not myPath:
            print("LB service %s not found" %name)
            return None
        P=LBVirtualServer(mp=self.mp)
        vId=P.getIdByName(name=vip, display=False)
        if not vId:
            print("LB VIP %s not found" %vip)
            return None
        if opType=='status':
            opType='detailed-status'
        else:
            opType='statistics'
        api='/policy/api/v1%s/lb-virtual-servers/%s/%s?source=%s' %(myPath,vId, opType, source)
        r=self.mp.get(api=api,verbose=True)
        if display:
            self.jsonPrint(r)
        return r
        
        
    
        
class LBAppProfile(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi = '/policy/api/v1/infra/lb-app-profiles'

    def config(self, name, idleTimeout, closeTimeout,
               appType,
               httpRedirectUrl=None,
               httpToHttps=False,
               ntlm=None,
               request_body_size=None,
               request_header_size=None,
               response_header_size=None,
               response_timeout=None,
               x_forwarded_for=None,
               mirror=None,
               desc=None):
        
        api='/policy/api/v1/infra/lb-app-profiles/%s' % name
        data={}
        data['display_name'] = name
        if desc:
            data['description'] = desc

        if appType.upper() == 'UDP':
            data['resource_type'] = 'LBFastUdpProfile'
            if idleTimeout:
                data['idle_timeout'] = idleTimeout
            if mirror:
                data['flow_mirroring_enabled'] = mirror
            
        elif appType.upper() == 'TCP':
            data['resource_type'] = 'LBFastTcpProfile'
            if idleTimeout:
                data['idle_timeout'] = idleTimeout
            if closeTimeout:
                data['close_timeout'] = closeTimeout
            if mirror:
                data['ha_flow_mirroring_enabled'] = mirror
            
        else:
            data['resource_type'] = 'LBHttpProfile'
            if idleTimeout:
                data['idle_timeout'] = idleTimeout
            if httpRedirectUrl:
                data['http_redirect_to'] = httpRedirectUrl
            if httpToHttps:
                data['http_redirect_to_https'] = httpToHttps
            if ntlm:
                data['ntlm'] = ntlm
            if request_body_size:
                data['request_body_size'] = request_body_size
            if request_header_size:
                data['request_header_size'] = request_header_size
            if response_header_size:
                data['response_header_size'] = response_header_size
            if response_timeout:
                data['response_timeout'] = response_timeout
            if x_forwarded_for:
                data['x_forwarded_for'] = x_forwarded_for.upper()
            
        self.mp.patch(api=api,data=data,verbose=True)
            
class LBMonitorProfile(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi = '/policy/api/v1/infra/lb-monitor-profiles'
    
    def configGenericMonitor(self, name, monitorType,
                             desc=None,
                             fallCount=None,
                             riseCount=None,
                             interval=None,
                             timeout=None,
                             port=None,
                             max_fails=None,
                             receive=None,
                             send=None,
                             datalen=None):
                             

        data={}
        data['display_name'] = name
        if monitorType.upper() == 'ACTIVE':
            data['resource_type'] = 'LBActiveMonitorProfile'
        elif monitorType.upper() == 'ICMP':
            data['resource_type'] = 'LBIcmpMonitorProfile'
            if datalen:
                data['data_length'] = datalen
        elif monitorType.upper() == 'PASSIVE':
            data['resource_type'] = 'LBPassiveMonitorProfile'
            if max_fails:
                data['max_fails'] = max_fails
        elif monitorType.upper() == 'UDP':
            data['resource_type'] = 'LBUdpMonitorProfile'
            data['receive'] = receive
            data['send'] = send
        elif monitorType.upper() == 'TCP':
            data['resource_type'] = 'LBTcpMonitorProfile'
            data['receive'] = receive
            data['send'] = send
        if desc:
            data['description'] = desc

        if monitorType.upper() != 'PASSIVE':
            if fallCount:
                data['fall_count'] = fallCount
            if riseCount:
                data['rise_count'] = riseCount
            if interval:
                data['interval'] = interval
            if port:
                data['monitor_port'] = port
            if timeout:
                data['timeout'] = timeout

        api='/policy/api/v1/infra/lb-monitor-profiles/%s' %name
        self.mp.patch(api=api,data=data,verbose=True)

            
        
    def configActive(self, name, desc=None,
                     fallCount=None,
                     riseCount=None,
                     interval=None,
                     timeout=None,
                     port=None):
        self.configGenericMonitor(name=name, desc=desc,
                                  monitorType="ACTIVE",
                                  fallCount=fallCount,
                                  riseCount=riseCount,
                                  timeout=timeout,
                                  port=port)

    def configPassive(self, name, desc=None,
                      maxFails=None,
                      fallCount=None,
                      riseCount=None,
                      interval=None,
                      timeout=None,
                      port=None):
        self.configGenericMonitor(name=name, desc=desc,
                                  monitorType="PASSIVE",
                                  maxFails=maxFails,
                                  fallCount=fallCount,
                                  riseCount=riseCount,
                                  timeout=timeout,
                                  port=port)
                      
            
    def configIcmp(self, name, desc=None,
                   datalen=None,
                   fallCount=None,
                   riseCount=None,
                   interval=None,
                   timeout=None,
                   port=None):
        self.configGenericMonitor(name=name, desc=desc,
                                  maxlen=maxlen,
                                  monitorType="ICMP",
                                  fallCount=fallCount,
                                  riseCount=riseCount,
                                  timeout=timeout,
                                  port=port)

    def configTcp(self, name, send=None, receive=None,
                  desc=None,
                  fallCount=None,
                  riseCount=None,
                  interval=None,
                  timeout=None,
                  port=None):
        self.configGenericMonitor(name=name, desc=desc,
                                  send=send,
                                  receive=receive,
                                  monitorType="TCP",
                                  fallCount=fallCount,
                                  riseCount=riseCount,
                                  timeout=timeout,
                                  interval=interval,
                                  port=port)
            
    def configUdp(self, name, send, receive,
                  desc=None,
                  fallCount=None,
                  riseCount=None,
                  interval=None,
                  timeout=None,
                  port=None):
                  
        self.configGenericMonitor(name=name, desc=desc,
                                  send=send,
                                  receive=receive,
                                  monitorType="UDP",
                                  fallCount=fallCount,
                                  riseCount=riseCount,
                                  interval=interval,
                                  timeout=timeout,
                                  port=port)
            
            
        
    def configHttp(self, name, httpType, desc=None,
                   fallCount=None,
                   riseCount=None,
                   interval=None,
                   timeout=None,
                   port=None,
                   request_body=None,
                   request_headers=None,
                   request_method=None,
                   request_url=None,
                   request_version=None,
                   response_body=None,
                   response_code=None):
        data={}
        data['display_name'] = name
        if httpType.lower() == 'https':
            data['resource_type'] = 'LBHttpsMonitorProfile'
        else:
            data['resource_type'] = 'LBHttpMonitorProfile'
        if fallCount:
            data['fall_count'] = fallCount
        if riseCount:
            data['rise_count'] = riseCount
        if interval:
            data['interval'] = interval
        if port:
            data['monitor_port'] = port
        if timeout:
            data['timeout'] = timeout

        if request_body:
            data['request_body'] = request_body
            
        if request_headers:
            data['request_headers'] =[]
            # in format of key:value
            for i in request_headers:
                k,v=request_headers.split(':')
                data['request_headers'].append({k:v})
        if request_method:
            # GET, OPTIONS, POST, HEAD, PUT
            data['request_method'] = request_method
        if request_url:
            # '/' if not set
            data['request_url'] = request_url
        if request_version:
            # HTTP_VERSION_1_0, HTTP_VERSION_1_1, HTTP_VERSION_2_0, 
            data['request_version'] = request_version
        if response_body:
            data['request_body'] = request_body
        if response_code:
            # this is a list
            data['response_status_codes'] = response_code
        api='/policy/api/v1/infra/lb-monitor-profiles/%s' %name
        self.mp.patch(api=api,data=data,verbose=True)

        
    def configHttpsSslBinding(self, name, certDepth=None,
                              clientCert=None,
                              serverAuth=None,
                              serverCA=None,
                              serverCRL=None,
                              sslProfile=None):

        m=self.findByName(name=name, display=False)
        if not m or m['resource_type'] != 'LBHttpsMonitorProfile':
            print("LB monitor %s not found or not HTTPS monitor profile" %name)
            return
        mpath=self.getPathByName(name=name,display=False)
        api='/policy/api/v1%s' %mpath
        data={}
        C=Certificate(mp=self.mp)
        if certDepth:
            data['certificate_chain_depth'] = certDepth
        if clientCert:
            cpath=C.getPathByName(name=clientCert,display=False)
            if not cpath:
                print("Client certificate %s not found" %clientCert)
                return
            data['client_certificate_path'] = cpath
        if serverAuth:
            # IGNORE, REQUIRED, default: AUTO_APPLY
            data['server_auth']=serverAuth
        if serverCA:
            data['server_auth_ca_paths'] = []
            for s in serverCA:
                spath=C.getPathByName(name=s, display=False)
                if not spath:
                    print("CA certificate %s not found" %serverCA)
                    return
                data['server_auth_ca_paths'].append(spath)
        if serverCRL:
            #
            # Not handled yet...do not use
            data['server_auth_crl_paths'] = []
            for s in serverCA:
                spath=C.getPathByName(name=s, display=False)
                if not spath:
                    print("Certificate CRL e %s not found" %serverCA)
                    return
                data['server_auth_crl_paths'].append(spath)
        if sslProfile:
            S=LBServerSslProfile(mp=self.mp)
            spath=S.getPathByName(name=sslProfile, display=False)
            if not spath:
                print("Server SSL profile %s not found" %sslProfile)
                return
            data['ssl_profile_path'] = spath
        mdata={}
        mdata['resource_type'] = 'LBHttpsMonitorProfile'
        m['server_ssl_profile_binding'] = data
        self.mp.patch(api=api,data=m,verbose=True)
            
class LBServerSslProfile(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi = '/policy/api/v1/infra/lb-server-ssl-profiles'

    def config(self, name, ciphers=None, cipher_group=None, desc=None,
               protocols=None, session_cache_enabled=None):
        data={}
        data['display_name'] = name
        if ciphers:
            # list
            data['ciphers'] = ciphers
        if cipher_group:
            data['cipher_group_label']= cipher_group
        if protocols:
            # list
            data['protocols']=protocols
        if session_cache_enabled:
            data['session_cache_enabled'] = session_cache_enabled
        if desc:
            data['description'] = desc

        api='/policy/api/v1/infra/lb-server-ssl-profiles/%s' %name
        self.mp.patch(api=api,data=data,verbose=True)
    
    
           
class LBClientSslProfile(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi = '/policy/api/v1/infra/lb-client-ssl-profiles'
        
    def config(self, name, ciphers=None, cipher_group=None,
               protocols=None, session_cache_enabled=None,
               prefer_server_ciphers=None,
               session_cache_timeout=None, desc=None):
        data={}
        data['display_name'] = name
        if ciphers:
            # list
            data['ciphers'] = ciphers
        if cipher_group:
            data['cipher_group_label']= cipher_group
        if protocols:
            # list
            data['protocols']=protocols

        if session_cache_enabled:
            data['session_cache_enabled'] = session_cache_enabled
        if desc:
            data['description'] = desc
        if prefer_server_ciphers:
            data['prefer_server_ciphers'] = prefer_server_ciphers
        if session_cache_timeout:
            data['session_cache_timeout'] = session_cache_timeout

        api='/policy/api/v1/infra/lb-client-ssl-profiles/%s' %name
        self.mp.patch(api=api,data=data,verbose=True)
    
class LBPersistenceProfile(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi = '/policy/api/v1/infra/lb-persistence-profiles'


    def configSourcePersistence(self, name, desc=None,
                                shared=None,
                                purge=None,
                                timeout=None,
                                sync=None):
        data={}
        data['display_name'] = name
        if desc:
            data['description'] = desc
        if shared:
            data['persistence_shared'] = shared
        if purge:
            data['purge'] = purge
        if timeout:
            data['timeout'] = timeout
        if sync:
            data['ha_persistence_mirroring_enabled'] = sync

        data['resource_type'] = 'LBSourceIpPersistenceProfile'
        api='/policy/api/v1/infra/lb-persistence-profiles/%s' %name
        self.mp.patch(api=api, data=data, verbose=True)

    def configCookiePersistence(self, name, desc=None,
                                cookie_domain=None,
                                disable_fallback=None,
                                disable_garble=None,
                                cookie_mode=None,
                                cookie_name=None,
                                cookie_path=None,
                                max_idle=None,
                                max_life=None,
                                shared=None):

        data={}
        data['display_name'] = name
        if desc:
            data['description'] = desc
        if cookie_domain:
            data['cookie_domain'] = cookie_domain
        if disable_fallback:
            # it's true by default
            data['cookie_fallback'] = False
        if disable_garble:
            # default is true
            data['cookie_garble'] = False
        if cookie_mode:
            data['cookie_mode'] = cookie_mode
        if cookie_name:
            data['cookie_name'] = cookie_name
        if cookie_path:
            data['cookie_path'] = cookie_path
        if max_idle or max_life:
            tdata={}
            if max_life:
                tdata['type'] = 'LBSessionCookieTime'
                tdata['cookie_max_life'] = max_life
            else:
                tdata['type'] = 'LBPersistenceCookieTime'
            if max_idle:
                tdata['cookie_max_idle'] = max_idle
            data['cookie_time'] = tdata
        if shared:
            data['persistence_shared'] = shared
        
        data['resource_type'] = 'LBCookiePersistenceProfile'
        api='/policy/api/v1/infra/lb-persistence-profiles/%s' %name
        self.mp.patch(api=api, data=data, verbose=True)
            
                                
class LBPool(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi = '/policy/api/v1/infra/lb-pools'

    def config(self, name, desc=None,
               active_monitor=None,
               algorithm=None,
               member_group=None,
               mg_ip_version=None,
               mg_max_ip=None,
               mg_adminDown_ips=None,
               mg_port=None,
               members=None,
               min_active_members=None,
               passive_monitor=None,
               snat_translation=None,
               snat_pool=None,
               tcp_multiplex_enabled=None,
               tcp_multiplex_number=None,
               update=False):

        data={}
        api=None
        if update:
            data=self.findByName(name=name, display=False)
            if data:
                api='/policy/api/v1%s' % self.getPathByName(name=name,display=False)

        if not api:
            api='/policy/api/v1/infra/lb-pools/%s' %name

        data['display_name'] = name
        if desc:
            data['description'] = desc
        if active_monitor or passive_monitor:
            M = LBMonitorProfile(mp=self.mp)
            if active_monitor:
                mpath=M.getPathByName(name=active_monitor,display=False)
                if not mpath:
                    print("Active Monitor %s not found" %active_monitor)
                    return False
                data['active_monitor_paths'] = [mpath]
            if passive_monitor:
                mpath=M.getPathByName(name=passive_monitor,display=False)
                if not mpath:
                    print("Passive Monitor %s not found" %passive_monitor)
                    return False
                data['active_monitor_paths'] = [mpath]
        if algorithm:
            data['algorithm'] = algorithm

        if member_group and members:
            print("May not specify both member_group and member")
            return
        if member_group:
            G=Group(mp=self.mp)
            gpath=G.getPathByName(name=member_group, display=False)
            if not gpath:
                print("Member group %s not found" %member_group)
                return
            if update and 'member_group' in data:
                mg = data['member_group']
            else:
                mg={}
            mg['group_path'] = gpath
            if mg_ip_version:
                mg['ip_revision_filter'] = mg_ipversion
            if mg_max_ip:
                mg['max_ip_list_size'] = mg_max_ip
            if mg_port:
                mg['port'] = mg_port
            if mg_adminDown_ips:
                mg['customized_members'] = []
                for i in mg_adminDown_ips:
                    #format: state|ip
                    pms={}

                    if admin.upper() not in ['ENABLED', 'DISABLED', 'GRACEFUL_DISABLED']:
                        print("Admin state %s not one of ENABLED, DISABLED, GRACEFUL_DISABLED"
                              %i)
                        return
                    else:
                        pms['admin_state'] = admin.upper()
                    pms['ip_address'] = ip
                    mg['customized_members'].append(pms)
            data['member_group'] = mg
        if members:
            data['members'] = []
            for i in members:
                #format "name|ip|state|backup|max_con|port|weight
                # only ip is mandatory.  All fields required, but can be blank
                # backup is true/false
                m={}
                name,ip,state,backup,maxcon,port,weight=i.split('|')
                if name.strip() != '':
                    m['display_name'] = name.strip()
                m['ip_address'] == ip.strip()
                if backup.strip().lower() == 'true':
                    m['backup_member'] = True
                else:
                    m['backup_member'] = False
                if maxcon.strip() != '':
                    m['max_concurrent_connections'] = maxcon.strip()
                if port.strip() != '':
                    m['port'] = port.strip()
                if weight.strip() != '':
                    m['weogjt']=weight.strip()

                mg['members'].append(m)
        if min_active_members:
            data['min_active_members'] = min_active_members
        if snat_translation:
            snat={}
            snat['type'] = snat_translation
            if snat_translation == 'LBSnatIpPool':
                if not snat_pool:
                    print("Must provide IP pool for LbSnatIpPool")
                    return
                snat['ip_addresses'] = []
                for i in snat_pool:
                    ipaddr={}
                    ipaddr['ip_address'] = i
                    snat['ip_addresses'].append(ipaddr)
                print(snat)

            data['snat_translation'] = snat

        if tcp_multiplex_enabled:
            data['tcp_multiplexing_enabled'] = tcp_multiplex_enabled
        if tcp_multiplex_number:
            data['tcp_multiplexing_number'] = tcp_multiplex_number
            
            
        self.mp.patch(api=api,data=data,verbose=True)
            

class LBVirtualServer(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi = '/policy/api/v1/infra/lb-virtual-servers'
    def config(self, name,
               ip_address,
               ports,
               application_profile,
               desc=None, update=False,
               access_log_enabled=None,
               default_pool_member_ports=None,
               disabled=None,
               lb_persistence_profile=None,
               lb_service=None,
               max_concurrent_connections=None,
               max_new_connection_rate=None,
               pool=None,
               sorry_pool=None):
        #client_ssl_profile_binding=None,
        #server_ssl_profile_binding=None,
        data={}
        api=None
        if update:
            d=self.findByName(name=name, display=False)
            if d:
                data=d
                api='/policy/api/v1%s'%self.getPathByName(name=name,display=False)
        if not api:
            api='/policy/api/v1/infra/lb-virtual-servers/%s' % name

        data['display_name'] = name
        if desc:
            data['description'] = desc

        data['ip_address'] = ip_address
        data['ports'] = ports
        A=LBAppProfile(mp=self.mp)
        apath=A.getPathByName(name=application_profile, display=False)
        if not apath:
            print("Application profile %s not found" %apath)
            return
        data['application_profile_path'] = apath

        if access_log_enabled:
            data['access_log_enabled'] = access_log_enabled

        if default_pool_member_ports:
            data['default_pool_member_ports'] = default_pool_member_ports
        if disabled:
            data['enabled'] = False

        if lb_persistence_profile:
            P=LBPersistenceProfile(mp=self.mp)
            ppath=P.getPathByName(name=lb_persistence_profile, display=False)
            if not ppath:
                print("LB Persistence Profile %s not found" %lb_persistence_profile)
                return
            data['lb_persistence_profile_path'] = ppath

        if lb_service:
            S=LoadBalancer(mp=self.mp)
            svcPath=S.getPathByName(name=lb_service, display=False)
            if not svcPath:
                print("LB Service %s not found" %lb_service)
                return
            data['lb_service_path'] = svcPath

        if max_concurrent_connections:
            data['max_concurrent_connections'] = max_concurrent_connections

        if max_new_connection_rate:
            data['max_new_connection_rate'] = max_new_connection_rate

        if pool or sorry_pool:
            P = LBPool(mp=self.mp)
            if pool:
                ppath=P.getPathByName(name=pool,display=False)
                if not ppath:
                    print("LB Pool %s not found" %pool)
                    return False
                data['pool_path'] = ppath
            if sorry_pool:
                ppath=P.getPathByName(name=sorry_pool,display=False)
                if not ppath:
                    print("LB Sorry Pool %s not found" %pool)
                    return False
                data['sorry_pool_path'] = ppath
                

        self.mp.patch(api=api,data=data,verbose=True)

    def configClientSslBinding(self, name, cert,
                               certDepth=None,
                               clientAuth=None,
                               clientCA=None,
                               clientCRL=None,
                               sniCerts=None,
                               sslProfile=None):
        m=self.findByName(name=name, display=False)
        if not m :
            print("LB VIP%s not found " %name)
            return
        mpath=self.getPathByName(name=name,display=False)
        api='/policy/api/v1%s' %mpath
        data={}
        C=Certificate(mp=self.mp)

        cpath=C.getPathByName(name=cert, display=False)
        if not cpath:
            print("Service certificate %s not found" %cert)
            return
        else:
            data['default_certificate_path'] = cpath
        if certDepth:
            data['certificate_chain_depth'] = certDepth
        if clientAuth:
            data['client_auth'] = clientAuth
        if clientCA:
            data['client_auth_ca_paths'] = []
            for s in serverCA:
                spath=C.getPathByName(name=s, display=False)
                if not spath:
                    print("CA certificate %s not found" %serverCA)
                    return
                data['client_auth_ca_paths'].append(spath)
        if clientCRL:
            #
            # Not handled yet...do not use
            data['client_auth_crl_paths'] = []
            for s in serverCA:
                spath=C.getPathByName(name=s, display=False)
                if not spath:
                    print("Certificate CRL e %s not found" %serverCA)
                    return
                data['client_auth_crl_paths'].append(spath)
        if sniCerts:
            data['sni_certificate_paths'] = []
            for s in serverCA:
                spath=C.getPathByName(name=s, display=False)
                if not spath:
                    print("SNI certificate %s not found" %serverCA)
                    return
                data['sni_certificate_paths'].append(spath)
        if sslProfile:
            S=LBClientSslProfile(mp=self.mp)
            spath=S.getPathByName(name=sslProfile, display=False)
            if not spath:
                print("Client SSL profile %s not found" %sslProfile)
                return
            data['ssl_profile_path'] = spath

        m['client_ssl_profile_binding'] = data
        self.mp.patch(api=api,data=m,verbose=True)
        
    def configServerSslBinding(self, name, certDepth=None,
                              clientCert=None,
                              serverAuth=None,
                              serverCA=None,
                              serverCRL=None,
                              sslProfile=None):

        m=self.findByName(name=name, display=False)
        if not m :
            print("LB VIP%s not found " %name)
            return
        mpath=self.getPathByName(name=name,display=False)
        api='/policy/api/v1%s' %mpath
        data={}
        C=Certificate(mp=self.mp)
        if certDepth:
            data['certificate_chain_depth'] = certDepth
        if clientCert:
            cpath=C.getPathByName(name=clientCert,display=False)
            if not cpath:
                print("Client certificate %s not found" %clientCert)
                return
            data['client_certificate_path'] = cpath
        if serverAuth:
            # IGNORE, REQUIRED, default: AUTO_APPLY
            data['server_auth']=serverAuth
        if serverCA:
            data['server_auth_ca_paths'] = []
            for s in serverCA:
                spath=C.getPathByName(name=s, display=False)
                if not spath:
                    print("CA certificate %s not found" %serverCA)
                    return
                data['server_auth_ca_paths'].append(spath)
        if serverCRL:
            #
            # Not handled yet...do not use
            data['server_auth_crl_paths'] = []
            for s in serverCA:
                spath=C.getPathByName(name=s, display=False)
                if not spath:
                    print("Certificate CRL e %s not found" %serverCA)
                    return
                data['server_auth_crl_paths'].append(spath)
        if sslProfile:
            S=LBServerSslProfile(mp=self.mp)
            spath=S.getPathByName(name=sslProfile, display=False)
            if not spath:
                print("Server SSL profile %s not found" %sslProfile)
                return
            data['ssl_profile_path'] = spath

        m['server_ssl_profile_binding'] = data
        self.mp.patch(api=api,data=m,verbose=True)
    
class HostSwitch(Nsx_object):
    def __init__(self,mp,name,pnics=None,profiles=None, ippool= None, tz=None,
                 mode="STANDARD"):
        # name = this is the name, should the match the one define in TZ
        # pnics array of pnics
        # ipppol - UUID of the
        # tz = list of TZs
        self.name = name
        self.pnics=pnics
        self.ippool = ippool
        self.profiles = profiles
        if tz:
            self.transportzones = []
            T = TransportZone(mp=mp)
            for z in tz:
                t = T.findByName(name=z, display=False)
                if not t:
                    raise ValueError("HostSwitch: TZ not found: %s" %z)
                self.transportzones.append({'transport_zone_id': t['id']})
        else:
            self.transportzones = None

        self.host_switch_mode = mode
        
    def getDict(self):
        data={}
        if self.name:
            data['host_switch_name'] = self.name
        if self.pnics:
            data['pnics'] = self.pnics
        if self.profiles:
            data['host_switch_profile_ids'] = self.profiles
        if self.ippool:
            data['ip_assignment_spec'] = {}
            data['ip_assignment_spec']['ip_pool_id'] = self.ippool
            data['ip_assignment_spec']['resource_type'] = 'StaticIpPoolSpec'
        if self.transportzones:
            data['transport_zone_endpoints'] = self.transportzones
        data['host_switch_mode'] = self.host_switch_mode
        
        return data

class TransportNode(Nsx_object):
    #
    # New class to support fabric management for transport nodes
    # that adds support for DVS7
    #
    def __init__(self, mp, tntype=None):
        super(self.__class__, self).__init__(mp=mp)
        if not tntype:
            self.listApi = '/api/v1/transport-nodes'
        else:
            self.listApi = '/api/v1/transport-nodes?node_types=%s' % tntype
                  
    
    def find(self,name=None,id=None,ip=None,display=True):
        if id:
            return self.findById(id=id,display=display)
        elif ip:
            return self.findByIp(ip=ip,display=display)
        else:
            return self.findByName(name=name,display=display)

    def findByNodeId(self,id,display=True):
        nodes = self.list(display=False)
        if nodes['result_count'] == 0:
            if display:
                print("No transport nodes defined in MP")
            return None
        for n in nodes['results']:
            if n['node_id'] == id:
                if display:
                    self.json_print(data=n,convert=False)
                return n
        if display:
            print("No transport node found with node id: %s" % id)
        return None

    def findByIp(self,ip,display=True):
        fnodes=self.list(display=False)
        if fnodes['result_count'] <= 0:
            if display:
                print("FabricNodes: No TN defined on MP.")
            return None

        for n in fnodes['results']:
            if not 'node_deployment_info' in n:
                continue
            if ip in n['node_deployment_info']['ip_addresses']:
                if display:
                    self.json_print(data=n,convert=False)
                return n
        if display:
            print("No transport node found with IP %s" %ip)
        return None

    def delete(self,name,display=False):
        tn = self.find(name=name,display=False)
        if not tn:
            print("Transport node delete - node not found: %s" %name)
            return False

        restUrl = '/api/v1/transport-nodes/%s' %tn['id']
        print ("Deleting transport node: %s, id: %s" %(name,tn['id']))
        r=self.mp.delete(api=restUrl,verbose=True, codes=[200])

    def getState(self, name=None, tnid=None, ip=None, tntype=None, display=True):
        # TN type can EdgeNode, HostNode
        if not name and not tnid and not ip:
            if not tntype:
                api='/api/v1/transport-nodes/state'
            else:
                api='/api/v1/transport-nodes/state?node_types=%s' %tntype
        else:
            obj = self.find(name=name,id=tnid,ip=ip,display=False)
            if not obj:
                if display:
                    print("TN not found for bond state")
                return None
            api='/api/v1/transport-nodes/%s/state' %obj['id']

        return self.mp.get(api=api,verbose=True, display=display)
    
                            

    def getTeps(self, name=None, tnid=None, ip=None,
                tntype=None,
                display=True):

        if tntype:
            self.listApi='/api/v1/transport-nodes?node_types=%s' %tntype
        if name or tnid or ip:
            node = self.find(name=name, id=tnid, ip=ip, display=False)
            if not node:
                print("TN not found")
                return None
            nodes={'results': [node]}
        else:
            nodes=self.list(display=False)
        for tn in nodes['results']:
            api = '/api/v1/transport-nodes/%s/state' %tn['id']
            data=self.mp.get(api=api, verbose=None, display=None)
            print("TN %s" %tn['display_name'])
            if 'host_switch_states' in data and 'endpoints' in data['host_switch_states'][0]:
                for n in data['host_switch_states'][0]['endpoints']:
                    print("   %s / %s gw %s" %(n['ip'], n['subnet_mask'],
                                             n['default_gateway']))
                        
    def getStatus(self, name=None, tnid=None, ip=None, display=True):
        if not name and not tnid and not ip:
            api='/api/v1/transport-nodes/status'
        else:
            obj = self.find(name=name,id=tnid,ip=ip,display=False)
            if not obj:
                if display:
                    print("TN not found for bond status")
                return None
            api='/api/v1/transport-nodes/%s/status' %obj['id']

        return self.mp.get(api=api,verbose=True, display=display)
                            

    def getBondStatus(self,name=None,ip=None,tnid=None,display=True):
        obj = self.find(name=name,id=tnid,ip=ip,display=False)
        if not obj:
            if display:
                print("TN not found for bond status")
            return None
        restUrl='/api/v1/transport-nodes/%s/pnic-bond-status' % obj['id']
        return self.mp.get(api=restUrl,verbose=True, display=display)
        
    def getTunnels(self,name=None,ip=None,tnid=None,display=True):
        obj = self.find(name=name,id=tnid,ip=ip,display=False)
        if not obj:
            if display:
                print("TN not found")
            return None
        restUrl='/api/v1/transport-nodes/%s/tunnels' % obj['id']
        return self.mp.get(api=restUrl,verbose=True, display=display)
                            
    def getRemoteNodeStatus(self,name=None,ip=None,tnid=None,display=True):
        obj = self.find(name=name,id=tnid,ip=ip,display=False)
        if not obj:
            if display:
                print("TN not found")
            return None
        restUrl='/api/v1/transport-nodes/%s/remote-transport-node-status' % obj['id']
        r = self.mp.get(api=restUrl,verbose=True, display=display)
        return json.loads(r.text)                            
                            

    def reSync(self, name=None,ip=None,tnid=None,display=True):
        obj=self.find(name=name,id=tnid,ip=ip,display=False)
        if not obj:
            if display:
                print("Tn not found")
            return None
        restUrl='/api/v1/transport-nodes/%s?action=resync_host_config' % obj['id']
        self.mp.post(api=restUrl,data=None,verbose=True, codes=[200])
        
                            
    def getCapabilities(self,name=None,ip=None,tnid=None,display=True):
        obj = self.find(name=name,id=tnid,ip=ip,display=False)
        if not obj:
            if display:
                print("TN not found")
            return None
        restUrl='/api/v1/transport-nodes/%s/capabilities' % obj['id']
        return self.mp.get(api=restUrl,verbose=True, display=display)
                                   

    def getInterfaces(self,name=None,ip=None,tnid=None,display=True):
        obj = self.find(name=name,id=tnid,ip=ip,display=False)
        if not obj:
            if display:
                print("TN not found")
            return None
        restUrl='/api/v1/transport-nodes/%s/network/interfaces' % obj['id']
        return self.mp.get(api=restUrl,verbose=True, display=display)
  
    def getInterfaceStat(self, name=None,ip=None,tnid=None,
                         interface=None,source=False,display=True):
        
        obj = self.find(name=name,id=tnid,ip=ip,display=False)
        if not obj:
            if display:
                print("TN not found")
            return None

        api='/api/v1/transport-nodes/%s/network/interfaces' %obj['id']
        r = self.mp.get(api=api,verbose=False)
        if source:
            realtime='realtime'
        else:
            realtime='cached'
        for i in r['results']:
            if not interface:
                api=('/api/v1/transport-nodes/%s/network/interfaces/%s/stats?source=%s'
                     %(obj['id'], i['interface_id'], realtime))
                r = self.mp.get(api=api,verbose=True, display=display)
            else:
                if interface.lower() == i['interface_id'].lower():
                    api=('/api/v1/transport-nodes/%s/network/interfaces/%s/stats?source=%s'
                         %(obj['id'], i['interface_id'], realtime))
                    r = self.mp.get(api=api,verbose=True, display=display)
 
    
    def getLldpNeighbors(self,name=None,ip=None,tnid=None,
                         interface=None,display=True):
        obj = self.find(name=name,id=tnid,ip=ip,display=False)
        if not obj:
            if display:
                print("TN not found")
            return None
        if interface:
            restUrl=('/api/v1/lldp/transport-nodes/%s/interfaces/%s'
                     % (obj['id'], interface))
        else:
            restUrl=('/api/v1/lldp/transport-nodes/%s/interfaces'
                     % (obj['id']))

        return  self.mp.get(api=restUrl,verbose=True, display=display)

    def addTz(self, tnname, tzname, swname="nsxDefaultHostSwitch", display=True):
        tzlist = TransportZone(mp=self.mp)
        tz = tzlist.findByName(name=tzname,display=False)
        if not tz:
            print ("TransportZone with name %s not found while configuring TN: %s"
                    %(tzname,tname))
            return

        tn = self.findByName(name=tnname,display=False)
        if not tn:
            print ("TransportNode not found: %s" %tnname)
            return

        for s in  tn['host_switch_spec']['host_switches']:
            if s['host_switch_name'] != swname:
                continue
            tzids = tn['transport_zone_endpoints']
            for z in tzids:
                if z['transport_zone_id'] == tz['id']:
                    print ("TransportNode %s already part of TZ (%s,%s)"
                           %(tnname,tzname,tz['id']))
                    return
            tzep = {}
            tzep['transport_zone_id'] = tz['id']
            tzids.append(tzep)

            data=tn
            data['transport_zone_endpoints'] = tzids

            restUrl = '/api/v1/transport-nodes/%s' %tn['id']
            return self.mp.put(api=restUrl,data=data,verbose=True,codes=[200])

    def addRtep(self, nodename, ippool, vlan, hsw="nsxDefaultHostSwitch"):
        node=self.findByName(name=nodename, display=False)
        if not node:
            print ("Can't find fabric node with name: %s" %nodename)
            return

        data={}
        data['rtep_vlan'] = vlan
        pools=IpPool(mp=self.mp)
        poolProfile=pools.getPoolId(name=ippool)
        if not poolProfile:
            print ("Can't find the IP pool with name: %s" %ippool)
            return
        data['ip_assignment_spec'] = {
            "ip_pool_id": poolProfile,
            "resource_type": "StaticIpPoolSpec"
        }
        data['host_switch_name'] = hsw
        node['remote_tunnel_endpoint'] = data

        api='/api/v1/transport-nodes/%s' % node['id']
        return self.mp.put(api=api, data=node, verbose=True, codes=[200])
        
            
    def config(self,nodename,nics,swname,uplink,lldp=None,ippool=None,
            vlansw=None,vnics=None,tzname=None):
        # Let's fine the node
        node = self.findByName(name=nodename,display=False)
        if not node:
            print ("Can't find fabric node with name: %s" %nodename)
            return

        if vlansw and not vnics:
            print ("Must supply vnics for vlan switch")
            return

        #Find the uplink profile
        upprofiles = HostSwitchProfile(mp=self.mp)
        profile = upprofiles.findByName(name=uplink,display=False)
        if not profile:

            print( "Can't find uplink profile with name: %s" %uplink)
            return

        profiles = []
        profItem={}
        profItem['key'] = profile['resource_type']
        profItem['value'] = profile['id']
        profiles.append(profItem)

        #find LLDP profile
        lldpProfile=None
        if lldp:
            lldpProfile = upprofiles.findByName(name=lldp,display=False)
            if not lldpProfile:
                print ("Can't find the lldp profile with name: %s" %lldp)
                return


        if lldpProfile:
            profItem={}
            profItem['key'] = lldpProfile['resource_type']
            profItem['value'] = lldpProfile['id']
            profiles.append(profItem)

        #find the ippooln
        poolProfile=None
        if ippool:
            pools=IpPool(mp=self.mp)
            poolProfile=pools.getPoolId(name=ippool)
            if not poolProfile:
                print ("Can't find the IP pool with name: %s" %ippool)
                return

        data={}
        data['display_name'] = node['display_name']
        if 'os_type' in node.keys():
            data['description'] = node['display_name'] + ' ' + node['os_type']
        else:
            data['description'] = node['display_name'] + ' ' + node['resource_type']


        team = profile['teaming']
        if 'standby_list' in team:
            uplinkList = team['active_list'] + team['standby_list']
        else:
            uplinkList = team['active_list']

        pnics = []
        upIndex = 0
        vIndex = 0
        vlanNics=[]
        if uplinkList[0]['uplink_type'] == 'PNIC':
            if len(uplinkList) < len(nics):
                print ("You have more nics than defined in the profile")
                return
            for n in nics:
                pnic={}
                pnic['device_name'] = n
                pnic['uplink_name'] = uplinkList[upIndex]['uplink_name']
                pnics.append(pnic)
                upIndex +=1
            if vnics and len(uplinkList) < len(vnics):
                print ("You have more vnics than defined in the profile")
                return
            elif vnics:
                for n in vnics:
                    vnic={}
                    vnic['device_name'] = n
                    vnic['uplink_name'] = uplinkList[vIndex]['uplink_name']
                    vlanNics.append(vnic)
                    vIndex +=1
        else:
            if profile['lags'][0]['number_of_uplinks'] < len(nics):
                print ("You have more nics than defined in the LAG profile")
                return
            for n in nics:
                pnic={}
                pnic['device_name'] = n
                pnic['uplink_name'] = profile['lags'][0]['uplinks'][upIndex]['uplink_name']
                pnics.append(pnic)
                upIndex +=1
            if vnics:
                for n in vnics:
                    print ("working on %s" %n)
                    print ("current index %d" %vIndex)
                    vnic={}
                    vnic['device_name'] = n
                    #self.json_print( profile['lags'][0])
                    print ("using %s" %profile['lags'][0]['uplinks'][vIndex]['uplink_name'])
                    vnic['uplink_name'] = profile['lags'][0]['uplinks'][vIndex]['uplink_name']
                    vlanNics.append(vnic)
                    vIndex+=1

        switchSpec = {}
        switchSpec['resource_type'] = "StandardHostSwitchSpec"
        switchSpec['host_switches'] = []

        hsw = HostSwitch(mp=self.mp,pnics=pnics, profiles = profiles,
                         ippool=poolProfile, tz=tzname, name=swname)
        hswDict=hsw.getDict()

        switchSpec['host_switches'].append(hswDict)

        #if tzname:
        #    data['transport_zone_endpoints'] = hsw.transportzones

        if vlansw:
            vsw = HostSwitch(mp=self.mp, name=vlansw,pnics=vlanNics,profiles=profiles)
            vswDict = vsw.getDict()
            switchSpec['host_switches'].append(vswDict)

        data['host_switch_spec'] = switchSpec

        data['node_id'] = node['id']

        restUrl = '/api/v1/transport-nodes'
        r = self.mp.post(api=restUrl,data=data,verbose=True,codes=[201])

    def setFailureDomain(self, nodename, domain):
        tn = self.findByName(name=nodename, display=False)
        if not tn:
            print("Transport node %s not found")
            return None
        if tn['node_deployment_info']['resource_type'] != 'EdgeNode':
            print("Transport node %s is a %s, not an EdgeNode" %
                  (nodename, tn['node_deployment_info']['resource_type']))
            return None
        F = FailureDomain(mp=self.mp)
        fd = F.findByName(name=domain, display=False)
        print(fd)
        if not fd:
            print("Failure domain %s not found" %domain)
            return None

        tn['failure_domain_id'] = fd['id']
        api='/api/v1/transport-nodes/%s' % tn['id']
        return self.mp.put(api=api, data=tn, verbose=True, codes=[200])

                  
                
    def update(self, nodename, nics=[], swname=None, uplink=None, lldp=None,
              ippool=None, vmklist=None, targets=None):
        ''' update TN hsw configuration
            hswName can be prefixed with '+', '~' for add/remove hsw operation
            hswName w/o any prefixed will be modified according to given parameters
            supported parameters: uplink, lldp, ippool
            not yet supported parameters: vlansw, vnics, tzname
        '''

        def _mapPnics(ulProf, nics):
            team = ulProf['teaming']
            uplinkList = team['active_list']
            if 'standby_list' in team:
                uplinkList += team['standby_list']

            pnics = []
            for upIndex,n in enumerate(nics):
                uplinkName = uplinkList[upIndex]['uplink_name'] if uplinkList[0]['uplink_type']=='PNIC' \
                    else ulProf['lags'][0]['uplinks'][upIndex]['uplink_name']
                pnics.append({
                    'device_name': n,
                    'uplink_name': uplinkName
                })
            return pnics

        op = '='
        if swname[0] in ['+', '-', '!', '~']:
            op = re.sub('[!~]', '-', swname[0])
            swname = swname[1:]

        tn = self.findByName(name=nodename, display=False)
        if not tn:
            self.logger.error("Transport node %s not found." % nodename)
            exit(1)
        uppd = HostSwitchProfile(mp=self.mp)

        targetSwitches = filter(lambda sw:sw['host_switch_name']==swname, tn['host_switch_spec']['host_switches'])
        curSwNames = [sw['host_switch_name'] for sw in tn['host_switch_spec']['host_switches']]
        modifiedHsw=None
        if op=='=':
            print('Updating switch %s' % swname)
            if swname not in curSwNames:
                print('Switch %s not found' % swname)
                exit(102)

            hsw = targetSwitches[0]
            modifiedHsw=hsw
            if uplink or nics:
                hswProf = filter(lambda p:p['key']=='UplinkHostSwitchProfile', hsw['host_switch_profile_ids'])[0]
                ulProf = uppd.findByName(name=uplink, display=False) if uplink \
                    else uppd.findById(hswProf['value'], display=False)

                hswProf['value'] = ulProf['id']
                if nics:
                    hsw['pnics'] = _mapPnics(ulProf, nics)

            if lldp:
                hswProf = filter(lambda p:p['key']=='LldpHostSwitchProfile', hsw['host_switch_profile_ids'])[0]
                lldpProf = uppd.findByName(name=lldp, display=False)
                hswProf['value'] = lldpProf['id']

            if ippool:
                ipp = IpPool(mp=self.mp).findByName(ippool, display=False)
                hsw['ip_assignment_spec']['ip_pool_id'] = ipp['id']
        elif op=='+':
            print('Adding switch %s' % swname)
            if swname in curSwNames:
                print('Switch %s arelady exist' % swname)
                exit(103)

            profiles, pnics, poolProfile = [], None, None
            if lldp:
                lldpProf = uppd.findByName(name=lldp, display=False)
                if lldpProf:
                    profiles.append({ 'key': lldpProf['resource_type'], 'value': lldpProf['id'] })
            if uplink:
                ulProf = uppd.findByName(name=uplink, display=False)
                if ulProf:
                    profiles.append({ 'key': ulProf['resource_type'], 'value': ulProf['id'] })
                    if nics:
                        pnics = _mapPnics(ulProf, nics)
            if ippool:
                ipp = IpPool(mp=self.mp).findByName(ippool, display=False)
                if ipp:
                    poolProfile = ipp['id']

            hsw = HostSwitch(mp=self.mp,name=swname, pnics=pnics,
                             profiles=profiles, ippool=poolProfile)
            hswDict = hsw.getDict()
            tn['host_switch_spec']['host_switches'].append(hswDict)
            modifiedHsw=tn['host_switch_spec']['host_switches'][-1]
        elif op in ['-', '~', '!']:
            print('Removing switch %s' % swname)
            if swname not in curSwNames:
                print('Switch %s not found' % swname)
                exit(102)

            tn['host_switch_spec']['host_switches'] = [sw for sw in
                tn['host_switch_spec']['host_switches'] if sw['host_switch_name']!=swname]

        restUrl = '/api/v1/transport-nodes/%s' % tn['id']
        if vmklist:
            if not targets:
                print("vmklist must require targets")
                exit(103)
            if len(vmklist.split(',')) != len(targets.split(',')):
                print("Number of vmklist objects not equal targets")
                exit(103)
            if not modifiedHsw:
                print("Didn't set modified HSW for migration")
                exit(103)
            else:
                modifiedHsw['is_migrate_pnics'] = True
            #restUrl="%s?vnic=%s&vnic_migration_dest=%s" %(restUrl,vmklist,targets)
            restUrl="%s?if_id=%s&esx_mgmt_if_migration_dest=%s" %(restUrl,vmklist,targets)

        r = self.mp.put(api=restUrl,data=tn, verbose=True, codes=[200])

    def setPassword(self, username, oldpassword, newpassword, node=None, expiry=None, display=True):

        tn = self.findByName(name=node, display=False)
        if not tn:
            print("Node %s not found" %node)
            return False

        uapi = '/api/v1/transport-nodes/%s/node/users' %tn['id']
        user = self.findByName(name=username, field='username',
                               api=uapi, display=False)
        if not user:
            print("Username %s not found on TN %s" % (username, node))
            return False
        userid=user['userid']
        user['old_password'] = oldpassword
        user['password'] = newpassword

        api="%s/%d" %(uapi,userid)
        r = self.mp.put(api=api, data=user, codes=[200])
        if display:
            self.jsonPrint(r)
        return r
            

class TNProfile(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/api/v1/transport-node-profiles'
        
    def __validateUplinks(self, names, nameList):

        for n in names:
            if n not in nameList:
                return False
        return True

    def applyToCluster(self, cluster, tnprofile, detachTnp=False):
        C = TNCollections(mp=self.mp)
        if not detachTnp and not tnprofile:
            print("TNP must be provided")
            return
        C.config(computecollection=cluster, tnprofile=tnprofile, removeTnp=detachTnp)

    def config(self, name,
               uplinkprofile, pnics, uplinknames,
               hswname,
               tz,
               lldp,
               vmks=None, vmknets=None,
               vmkuninstall=None, vmkuninstnets=None,
               pnicuninstalls=True,
               ippool = None,
               vds=None,
               swtype='NVDS',
               mode='STANDARD',
               desc = None):

        '''
        name = name of this TNProfile
        desc = Description of the uplink profile
        uplinkprofile - name of the uplink profile to be used
        uplinks - list of pNICs
        uplinknames - list of uplinks for mapping in order of "uplinks", must match
                      names in uplinkprofile
        vmks - list of vmkernel interfaces to migrate to NSX VLAN logical switches
        vmknets - list of NSX VLAN logical switches, order must match vmks order
        vmkuninstall - list of vmkernel interfaces to migrate out of NVDS at uninstall
        vmkuninstnets - list of DVS portgroups to use when migrating vmks out of NVDS to DVS
        pnicuninstalls - list of pNICs to uninstall
        hswname - name of the NVDS host switch
        tz - list of transport zone names
        lldp - Name of LLDP profile
        ippool - Name of IpPool to use, DHCP if this is None
        '''

        data = {}
            
        data['display_name'] = name
        data['resource_type'] = 'TransportNodeProfile'
        if desc:
            data['description'] = desc


        swdata={}
        switchSpec=self.__configSwitchSpec(data=swdata,hswname=hswname,
                                           uplinkprofile=uplinkprofile,
                                           pnics=pnics,
                                           uplinknames=uplinknames,
                                           vmks=vmks,
                                           lldp=lldp,
                                           vmknets=vmknets,
                                           vmkuninstall=vmkuninstall,
                                           vmkuninstnets=vmkuninstnets,
                                           pnicuninstalls=pnicuninstalls,
                                           ippool=ippool,
                                           tz=tz,
                                           mode=mode,
                                           vds=vds,
                                           swtype=swtype)

        if not switchSpec:
            print("Host switch not created properly")
            return None
        data['host_switch_spec'] = {}
        data['host_switch_spec']['resource_type'] = 'StandardHostSwitchSpec'
        data['host_switch_spec']['host_switches'] = [switchSpec]

        #T = TransportZone(mp=self.mp)
        #data['transport_zone_endpoints'] = []
        #foundSwitch = False
        #for n in tz:
        #   t = T.findByName(name=n, display=False)
        #    if not t:
        #        print("TransportZone %s not found" %n)
        #        return None
        #    else:
        #        data['transport_zone_endpoints'].append({'transport_zone_id':t['id']})
        #        if hswname and hswname==t['host_switch_name']:
        #            foundSwitch = True
        #if hswname and not foundSwitch:
        #    print("Host switch name %s not found in any of listed TZs" %hswname)
        #    return None
        
        api='/api/v1/transport-node-profiles'
        r = self.mp.post(api=api,data=data,verbose=True, codes=[201])

    def __configSwitchSpec(self, data, hswname,
                           uplinkprofile, pnics, uplinknames, tz, lldp=None,
                           vmks=None, vmknets=None,
                           vmkuninstall=None, vmkuninstnets=None,
                           pnicuninstalls=True, vds=None, swtype="NVDS",
                           mode='STANDARD',
                           ippool = None, update=False):
        
        '''
        name = name of this TNProfile
        desc = Description of the uplink profile
        uplinkprofile - name of the uplink profile to be used
        uplinks - list of pNICs
        uplinknames - list of uplinks for mapping in order of "uplinks", must match
                      names in uplinkprofile
        vmks - list of vmkernel interfaces to migrate to NSX VLAN logical switches
        vmknets - list of NSX VLAN logical switches, order must match vmks order
        vmkuninstall - list of vmkernel interfaces to migrate out of NVDS at uninstall
        vmkuninstnets - list of DVS portgroups to use when migrating vmks out of NVDS to DVS
        pnicuninstalls - list of pNICs to uninstall
        hswname - name of the NVDS host switch
        tz - list of transport zone names
        ippool - Name of IpPool to use, DHCP if this is None
        '''

        if not ippool:
            if 'ip_assigment_spec' not in data.keys():
                data['ip_assignment_spec'] = {'resource_type': 'AssignedByDhcp'}
        else:
            P = IpPool(mp=self.mp)
            pid = P.getPoolId(name=ippool, display=False)
            print(pid)
            if not pid:
                print("IP Pool %s not found" %ippool)
                return None
            else:
                ip = {}
                ip['ip_pool_id'] = pid
                ip['resource_type'] = 'StaticIpPoolSpec'
                data['ip_assignment_spec'] = ip
        if tz:
            data['transport_zone_endpoints'] = []
            for n in tz:
                T=TransportZone(mp=self.mp)
                t = T.findByName(name=n, display=False)
                if not t:
                    print("TransportZone %s not found" %n)
                    return None
                else:
                    data['transport_zone_endpoints'].append({'transport_zone_id':t['id']})
        if lldp:
            U = HostSwitchProfile(mp=self.mp)
            u = U.findByName(name=lldp,display=False)
            if not u:
                print("LLDP UplinkProfile %s not found" %lldp)
                return None
            if 'host_switch_profile_ids' not in data.keys():
                data['host_switch_profile_ids'] = [{'key':u['resource_type'], 'value': u['id']}]
            else:
                found=False
                for p in data['host_switch_profile_ids']:
                    if p['value'] == u['id']:
                        found = True
                        break
                    else:
                        tu = U.findById(id=p['value'], display=False)
                        if tu and tu['resource_type'] == u['resource_type']:
                            p['value'] = u['id']
                            found=True
                            break
                            
                if not found:
                    data['host_switch_profile_ids'].append({'key':u['resource_type'],
                                                            'value':u['id']})

        if uplinkprofile:
            U = HostSwitchProfile(mp=self.mp)
            u = U.findByName(name=uplinkprofile,display=False)
            if not u:
                print("UplinkProfile %s not found" %uplinkprofile)
                return None
            if 'host_switch_profile_ids' not in data.keys():
                data['host_switch_profile_ids'] = [{'key':u['resource_type'], 'value': u['id']}]
            else:
                found=False
                for p in data['host_switch_profile_ids']:
                    if p['value'] == u['id']:
                        found = True
                        break
                    else:
                        tu = U.findById(id=p['value'], display=False)
                        if tu and tu['resource_type'] == u['resource_type']:
                            p['value'] = u['id']
                            found=True
                            break
                            
                if not found:
                    data['host_switch_profile_ids'].append({'key':u['resource_type'],
                                                            'value':u['id']})
                


        if hswname:
            data['host_switch_name'] = hswname
        
        l = U.uplinkList(name=None,obj=u,display=False)
        if not self.__validateUplinks(names=uplinknames, nameList=l):
            print("Uplink names do not match names list in uplink profile")
            print(" Provided uplinks: %s "%uplinknames)
            print(" Uplink profile link names: %s" %l)
            return None

        
        if not (len(pnics)  <= len(uplinknames)):
            print("The number of PNICs must be equal to or less than the number of profile uplinks")
            return None

        data['host_switch_mode'] = mode
        if swtype=='NVDS':
            data['host_switch_type'] = 'NVDS'
            _pnics = [ ]
            for i in range(len(pnics)):
                _pnics.append({'device_name':pnics[i], 'uplink_name':uplinknames[i]})
            data['pnics'] = _pnics
            if pnicuninstalls:
                data['pnics_uninstall_migration'] = _pnics
        else:
            data['host_switch_type'] = 'VDS'
            V = vDS(mp=self.mp)
            v = V.findByName(name=vds, display=False)
            if not v:
                print("VDS name %s not found" % vds)
                return None
            data['host_switch_id'] = v['uuid']
            data['uplinks'] = []
            for i,j in zip(uplinknames, v['uplink_port_names']):
                data['uplinks'].append({'uplink_name': i, 'vds_uplink_name': j})

        if vmks:
            if len(vmks) != len(vmknets):
                print("The number of vmknets must be equal the number of vmks to be migrated")
                return None
            S=Segments(mp=self.mp)
            vmk_install_migration = []
            for v in range(len(vmknets)):
                sw = S.getRealizedSwitch(name=vmknets[v],display=False)
                if not sw:
                    print("VMK migration destination network %s does not exist" %vmknets[v])
                    return None
                else:
                    vmk_install_migration.append({'device_name': vmks[v],
                                                  'destination_network': sw})
            data['vmk_install_migration'] = vmk_install_migration

        
        if vmkuninstall:
            if len(vmkuninstall) != len(vmkuninstnets):
                print("The number of vmkuninstnet must equal vmkuninstall")
                return None
            vmk_uninstall_migration = []
            for v in range(len(vmkuninstnets)):
                vmk_uninstall_migration.append({'device_name': vmkuninstall[v],
                                                'destination_network': vmkuninstnets[v]})
            data['vmk_uninstall_migration'] = vmk_uninstall_migration

        return data
        
                            

class HostSwitchProfile(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/api/v1/host-switch-profiles?include_system_owned=true'


    def configUplinkHostSwitchProfile(self, name, uplinktype,
                                      active, policy, standby=None,
                                      vlan = None, mtu=None, named=None,
                                      lagmode="ACTIVE",
                                      laglb="SRCDESTIPVLAN",
                                      laglinks=2,
                                      lagtimeout="SLOW",
                                      desc=None):
        '''
        @name Display name for the uplink profile
        @uplinktype lag or pnic
        @uplinks name of lag (1 item) or list of pnic uplinks
        @vlan Overlay VLAN ID
        @mtu transport MTU
        @desc description
        '''

        found = self.findByName(name=name)
        if found:
            data=found
        else:
            data={}
            
        data['resource_type'] = 'UplinkHostSwitchProfile'
        data['display_name'] = name
        if desc:
            data['description'] = desc
        if mtu:
            data['mtu'] = mtu
        if vlan:
            data['transport_vlan'] = vlan
            
        
        if uplinktype.lower()=="lag":
            lag={}
            lag['load_balance_algorithm'] = laglb
            lag['mode'] = lagmode
            lag['name' ] = active[0]
            lag['number_of_uplinks'] = laglinks
            lag['timeout_type'] = lagtimeout
            data['lags'] = [lag]
            
            # This is the default teaming policy
            teaming={}
            active_list={}
            active_list['uplink_type'] = "LAG"
            active_list['uplink_name'] = lag['name']
            teaming['active_list'] = [active_list]
            # standby not supported here cuz this method only creates
            # one lag per switch.  Note NSX supports more than one
            teaming['policy'] = 'FAILOVER_ORDER'
            data['teaming'] = teaming

            # name:policy:actives:standbys
            # This library only supports one lag, so only name is signifcant
            if named:
                data['named_teamings'] = []
                for i in named:
                    n,p,a,s = i.split(':')
                    named_policy={}
                    named_policy['name'] = n
                    named_policy['policy']='FAILOVER_ORDER'
                    upl={}
                    upl['uplink_name']=lag['name']
                    upl['uplink_type'] = "LAG"
                    named_policy['active_list'] = [upl]
                    data['named_teamings'].append(named_policy)

        else:
            teaming={}
            teaming['policy'] = policy
            teaming['active_list'] = []
            for n in active:
                upl = {}
                upl['uplink_name'] = n
                upl['uplink_type'] = "PNIC"
                teaming['active_list'].append(upl)
            if standby:
                teaming['standby_list'] = []
                for n in standby:
                    upl = {}
                    upl['uplink_name'] = n
                    upl['uplink_type'] = "PNIC"
                    teaming['standby_list'].append(upl)
            data['teaming'] = teaming

            # name:policy:actives:standbys
            # actives and standbys are comma seperated
            if named:
                data['named_teamings'] = []
                for i in named:
                    n,p,a,s = i.split(':')
                    named_policy={}
                    named_policy['name'] = n
                    if p.upper() not in ['FAILOVER_ORDER',
                                 'LOADBALANCE_SRCID',
                                 'LOADBALANCE_SRC_MAC']:
                        print("Named teaming policy %s not FAILOVER_ORDER, LOADBALANCE_SRCID, or LOADBALANCE_SRC_MAC")
                        return
                    named_policy['policy'] = p.upper()
                    named_policy['active_list'] = []
                    for l in a.split(','):
                        upl={}
                        upl['uplink_name'] = l
                        upl['uplink_type'] = "PNIC"
                        named_policy['active_list'].append(upl)
                    if s.strip() != '':
                        named_policy['standby_list'] = []
                        for l in s.split(','):
                            upl={}
                            upl['uplink_name'] = l
                            upl['uplink_type'] = "PNIC"
                            named_policy['standby_list'].append(upl)
                    data['named_teamings'].append(named_policy)
                    
                            
                        
        if found:
            api='/api/v1/host-switch-profiles/%s' % data['id']
            return self.mp.put(api=api,data=data,verbose=True,codes=[200])
        else:
            api='/api/v1/host-switch-profiles'
            return self.mp.post(api=api,data=data,verbose=True,codes=[201])

    def activeUplinks(self,name,obj=None,display=True):
        if not obj:
            data=self.findByName(name=name,display=False)
            if not data:
                raise ValueError("Uplinkprofile %s not found" %name)
        else:
            data = obj
        links = []
        for i in data['teaming']['active_list']:
            if i['uplink_type'] == 'LAG':
                for u in data['lags']:
                    if i['uplink_name'] == u['name']:
                        for x in u['uplinks']:
                            links.append(x['uplink_name'])
                        return links
                return None
            else:
                links.append(i['uplink_name'])
        return links

    def standbyUplinks(self,name,obj=None,display=True):
        if not obj:
            data=self.findByName(name=name,display=False)
            if not data:
                raise ValueError("Uplinkprofile %s not found" %name)
        else:
            data=obj
        if not 'standby_list' in data['teaming']:
            return []

        links = []
        for i in data['teaming']['standby_list']:
            links.append(i['uplink_name'])
        return links
            
    def uplinkList(self,name, obj=None, display=True):
        active=self.activeUplinks(name=name,obj=obj,display=False)
        standby = self.standbyUplinks(name=name, obj=obj,display=False)
        links=active+standby
        return links
                
            
    def configLldpProfile(self, name, lldp, display=True):
        found = self.findByName(name=name, display=False)
        if found:
            data=found
        else:
            data={}

        data['display_name'] = name
        data['send_enabled'] = lldp
        data['resource_type'] = 'LldpHostSwitchProfile'
        if found:
            api='/api/v1/host-switch-profiles/%s' % data['id']
            self.mp.put(api=api, data=data, verbose=True, codes=[200])
        else:
            api='/api/v1/host-switch-profiles'
            self.mp.post(api=api,data=data,verbose=True,codes=[201])
            
class License(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/api/v1/licenses'

    def config(self, license):
        data={'license_key': license}
        return self.mp.post(api='/api/v1/licenses',
                            data=data, verbose=True, codes=[200])


class FailureDomain(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/api/v1/failure-domains'

    def config(self, name, setPrefer, setNotPrefer, desc=None):
        data={}
        data['display_name'] = name
        if setPrefer and setNotPrefer:
            print("Both setPrefer and setNotPrefer active edge services specified, must be one or ther other")
            return None
        if setPrefer:
            data['preferred_active_edge_services'] = True
        if setNotPrefer:
            data['preferred_active_ege_services'] = False

        if desc:
            data['description'] = desc

        return self.mp.post(api='/api/v1/failure-domains', data=data,
                            verbose=True, codes=[201])

class Federation(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/global-infra/federation-config'
        
    def makeActive(self, name):
        data={}
        data['display_name'] = name
        data['mode'] = 'ACTIVE'

        api='/global-manager/api/v1/global-infra/global-managers/%s' %name
        return self.mp.patch(api=api,data=data, verbose=True,codes=[200])
    

class Backup(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/api/v1/cluster/backups/config'

    def getServerSshFingerprint(self, server, port=22, display=True):
        data={}
        data['server'] = server
        data['port'] = port
        api='/api/v1/cluster/backups?action=retrieve_ssh_fingerprint'
        r= self.mp.post(api=api, data=data,verbose=display,codes=[200])
        if display:
            self.jsonPrint(r)
        return r
    
    def history(self, display=True):
        api='/api/v1/cluster/backups/history'
        r = self.mp.get(api=api, verbose=display)
        if display:
            self.jsonPrint(r)

        return r
    def timeStamps(self, display=True):
        api='/api/v1/cluster/restore/backuptimestamps'
        r = self.mp.get(api=api, verbose=display)
        if display:
            self.jsonPrint(r)

        return r

    
    def config(self, auto_weekly, auto_days, auto_hour, auto_min, 
               auto_daily, auto_backup_interval, passphrase,
               remote_dir, remote_port, remote_server,
               remote_user, remote_password, remote_fingerprint=None,
               backup_after_topo=None, inventory=240):


        if not remote_fingerprint:
            r=self.getServerSshFingerprint(server=remote_server,
                                            port=remote_port,
                                            display=False)
            remote_fingerprint=r['ssh_fingerprint']

        data={}
        if backup_after_topo:
            # from 300 to 86400
            data['after_inventory_update_interval'] = backup_after_topo

        if auto_daily and auto_weekly:
            print("Either auto_daily or auto_weekly should be specified, not both")
            return
        if auto_daily or auto_weekly:
            data['backup_enabled'] = True
        if auto_weekly:
            ab = {}
            ab['resource_type'] = 'WeeklyBackupSchedule'
            ab['days_of_week'] = auto_days
            ab['hour_of_day'] = auto_hour
            ab['minute_of_day'] = auto_min
            data['backup_schedule'] = ab
        if auto_daily:
            ib={}
            ib['resource_type'] = 'IntervalBackupSchedule'
            # default is 3600
            ib['seconds_between_backups'] = auto_backup_interval
            data['backup_schedule'] = ib
        data['passphrase'] = passphrase
        data['inventory_summary_interval'] = inventory
        rserver={}
        rserver['directory_path'] = remote_dir
        rserver['port'] = remote_port
        rserver['server'] = remote_server
        protocol = {}
        protocol['protocol_name'] = 'sftp'
        protocol['ssh_fingerprint'] = remote_fingerprint
        protocol['authentication_scheme']={}
        protocol['authentication_scheme']['password'] = remote_password
        protocol['authentication_scheme']['username'] = remote_user
        protocol['authentication_scheme']['scheme_name'] = 'PASSWORD'
        rserver['protocol'] = protocol
        data['remote_file_server'] = rserver
        
        self.mp.put(api='/api/v1/cluster/backups/config',
                     data=data, verbose=True, codes=[200])
        
         
        
class Syslog(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/api/v1/node/services/syslog/exporters'

    def setExporter(self, name,
                    level,
                    port,
                    protocol,
                    server,
                    facilities=None,
                    structured_data=None,
                    msgids=None,
                    server_ca=None,
                    client_cert=None,
                    client_ca=None,
                    client_key=None):


        data={}
        data['exporter_name'] = name
        data['level'] =level
        if facilities:
            data['facilities'] = facilities
        if msgids:
            data['msgids'] = msgids
        if port:
            data['port'] = port
        data['protocol'] = protocol
        data['server'] = server
        if structured_data:
            data['structured_data']= structured_data
        if server_ca:
            fp = open(server_ca, 'r')
            if not fp:
                print("Invalid CA cert file for server: %s" %server_ca)
                return None
            data['tls_ca_pem'] = fp.read()
            close(fp)
        if  client_cert:
            fp = open(client_cert, 'r')
            if not fp:
                print("Invalid  client cert file: %s" %client_cert)
                return None
            data['tls_cert_pem'] = fp.read()
            close(fp)
        
        if  client_ca:
            fp = open(client_ca, 'r')
            if not fp:
                print("Invalid  cert file for server: %s" %client_ca)
                return None
            data['tls_client_ca_pem'] = fp.read()
            close(fp)
        
        if  client_key:
            fp = open(client_key, 'r')
            if not fp:
                print("Invalid  cert key file for server: %s" %client_key)
                return None
            data['tls_key_pem'] = fp.read()
            close(fp)
            
        api='/api/v1/node/services/syslog/exporters'
        self.mp.post(api=api,data=data,verbose=True, codes=[201], display=True)
        
    def removeAllExporters(self):
        api='/api/v1/node/services/syslog/exporters'
        self.mp.delete(api=api, verbose=True, codes=[200])

    def verify(self):
        self.mp.post(api='/api/v1/node/services/syslog/exporters?action=verify',
                     data=None, verbose=True, codes=[200])
    def status(self):
        self.mp.get(api='/api/v1/node/services/syslog/status', verbose=True, display=True)
        
    def serviceCtl(self, action):
        self.mp.post(api='/api/v1/node/services/syslog?action=%s' % action,
                     verbose=True, codes=[200])
    
        
        
class Migration(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/api/v1/migration/setup'


    def createVmGroup(self, vms=None, inputfile=None, group=None):

        data={}
        data['vm_instance_ids'] = []
        if inputfile:
            with open(inputfile, "r") as fp:
                data = json.load(fp)

        
        if group:
            data['group_id'] = group
        elif 'group_id' not in data.keys():
            data['group_id'] = random.randomint(1,10000)

        if vms:
            for v in vms:
                data['vm_instance_ids'].append(v)

        api='/api/v1/migration/vmgroup?action=pre_migrate'

        r = self.mp.post(api=api, data=data, verbose=True, codes=[200])

        print("Group id: %d" %data['group_id'])



    def postMigrateGroup(self, group):
        api='/api/v1/migration/vmgroup?action=post_migrate'

        data={}
        data['group_id'] = group
        r = self.mp.post(api=api, data=data, verbose=True, codes=[200])
        
                         
            
            
        
            
               
               
    
    
    
            
    
        
        
    
    
            
            
        
    
                   
