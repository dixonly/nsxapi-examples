from __future__ import print_function
import connections
import uuid
import json


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
        self.domain=domain
        self.site=site
        self.ep=enforcementPoint
        
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

                    
    def list(self, api=None, brief=False, display=True, header=None):
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
        if display:
            print("API: GET %s" % api)
            self.jsonPrint(data=r, brief=brief, header=header)
        return r
        
    def findByName(self, name, api=None, data=None, display=True,brief=False):
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
            data = self.list(api=api,display=False)
        obj = None
        for o in data['results']:
            if o['display_name'] == name:
                obj = o
                break
        if obj and display:
            if brief:
                print("%d. Name: %s" %(i,obj['display_name']))
                print("    Id: %s" %(obj['id']))
            else:
                self.jsonPrint(data=obj)
        return obj
    
    def findById(self, id, api=None, data=None, display=True,brief=False):
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
        data = self.list(api=api,display=False)
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

    def delete(self, name, display=True):
        '''
        Delete an nsxojbect found by display_name
        '''
        oPath=self.getPathByName(name=name, display=False)
        if not oPath:
            print("%s not found for delete" % name)
            return
        api='/policy/api/v1%s' % oPath
        self.mp.delete(api=api,verbose=True, codes=[200])
            
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
        r = self.mp.get(api=api)
        if display:
            self.jsonPrint(r)
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
        self.clusterid = self.info(display=False)['cluster_id']

    def info(self, display=True):
        restUrl = '/api/v1/cluster'
        r= self.mp.get(restUrl,verbose=False)
        if display: self.jsonPrint(r)
        return r
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
        r = self.mp.get(api=restUrl)
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
        certObj = nsxtlib.Certificate(mp=self.mp)
        cert = certObj.find(name=certName,
                            types=['certificate_signed', 'certificate_self_signed'],
                            display=False)   
        #cert = self.findByName(restUrl='/api/v1/trust-management/certificates',
        #                       name=certName, display=False)
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
        


class GlobalConfigs(Nsx_object):
    '''
    Class for switch and routing GlobalConfigs
    '''
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/api/v1/global-configs'

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
        if replication != None and replication != data['global_replication_mode_enabled']:
            data['global_replication_mode_enabled'] = replication
            changed = True

        if changed:
            r = self.mp.put(api=self.listApi, data=data, verbose=True, codes=[200])
        else:
            print("No change submitted, no-op")
            
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
        self.listApi=('/policy/api/v1/infra/sites/%s/enforcement-points/%s/transport-zones'
                      %(self.site, self.ep))

   
    def config(self,name,hswname,transportType,desc='None'):
        api='/api/v1/transport-zones'
        data={}
        data['display_name'] = name
        if desc:
            data['description'] = desc
        data['host_switch_name'] = hswname
        data['transport_type'] = transportType
        self.mp.post(api, data=data,verbose=True, codes=[201])

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
    
class Edge(Nsx_object):
    '''
    Class to list/find edge nodes, within an edgecluster ec if specified
    '''
    def __init__(self, mp, site='default', enforcementPoint='default', ec=None):
        super(self.__class__, self).__init__(mp=mp)
        
    def list(self, ec=None, display=True):
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
                r = self.list(ec=e['display_name'],display=False)
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

        
class Tier0(Nsx_object):
    '''
    Class to manage Tier0 Gateways
    '''
    def __init__(self, mp, site='default'):
        super(self.__class__, self).__init__(mp=mp, site=site)
        self.listApi='/policy/api/v1/infra/tier-0s'

    def setEdgeCluster(self, name=None, clustername=None, clusterid=None,
                       clusterpath=None, locale='default'):
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
        
        t0 = self.getPathByName(name=name, display=False)
        if not t0:
            print("Can't find Tier0 %s" %name)
            return False
        api='/policy/api/v1'+t0+'/locale-services/' + locale
        data={}
        data['edge_cluster_path'] = path
        self.mp.patch(api=api, data=data, codes=[200], verbose=True)

    def setRouteDistribution(self, name, redist=None, locale='default'):

        t0 = self.getPathByName(name=name, display=False)
        if not t0:
            print("Can't find Tier0 %s" %name)
            return False

        api='/policy/api/v1'+ t0 + '/locale-services/' + locale
        data={}
        data['route_redistribution_types'] = redist
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
                        edge=None, desc=None, locale='default'):
        
        t0=self.getPathByName(name=name, display=False)
        if not t0:
            print("Tier0 with name %s not found" %name)
            return None

        api='/policy/api/v1' + t0 + '/locale-services/' \
            + locale + '/interfaces/' + interface
        s = Segments(mp=self.mp)
        ls = s.getPathByName(name=segment,display=False)
        if not ls:
            print("Segment %s not found" %segment)
            return None
        e=Edge(mp=self.mp)
        eList=e.list(display=False)
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

    def getLocale(self,name,display=True):
        url=self.listApi + "/" + name + "/locale-services"
        self.list(api=url,display=display)
        

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
        
        api='/policy/api/v1' + t0 + '/locale-services/' + locale + '/bgp'

        data={}
        data['local_as_num'] = localas
        if enable_multipathrelax:
            data['multipath_relax'] = enable_multipathrelax
        if disable_multipathrelax:
            data['multipath_relax'] = disable_multipathrelax
        if enable_intersr:
            data['inter_sr_ibgp'] = enable_intersr
        if disable_intersr:
            data['inter_sr_ibgp'] = disable_intersr
        if enable_ecmp:
            data['ecmp'] = enable_ecmp
        if disable_ecmp:
            data['ecmp'] = disable_ecmp
        if enable_gr:
            data['graceful_restart'] = True
        if disable_gr:
            data['graceful_restart'] = False
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
        

    def getBgpNeighbors(self, name, locale='default', display=True):
        
        t0=self.getPathByName(name=name, display=False)
        if not t0:
            print("Tier0 with name %s not found" %name)
            return None
        
        api='/policy/api/v1' + t0 + '/locale-services/' + locale + '/bgp/neighbors'
        self.mp.get(api=api,verbose=True,codes=[200])
    
                

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
                          locale='default', display=True):

        t0=self.getPathByName(name=name, display=False)
        if not t0:
            print("Tier0 with name %s not found" %name)
            return None
        
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
            r = self.mp.get(api=api,verbose=False)
            self.jsonPrint(r)
            
        
class PrefixList(Nsx_object):
    def __init__(self, mp, tier0, t0Path=None):
        super(self.__class__, self).__init__(mp=mp)
        if not t0Path:
            self.listApi='/policy/api/v1/infra/tier-0s/' + tier0 + '/prefix-lists'
        else:
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
    def __init__(self, mp, tier0):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/infra/tier-0s/' + tier0 + '/community-lists'

    def config(self, t0, name, communities, desc=None,display=True):
        api='/policy/api/v1/infra/tier-0s/' + t0 + '/community-lists/' + name

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
    def __init__(self, mp, tier0, t0Path):
        super(self.__class__, self).__init__(mp=mp)
        if not t0Path:
            self.listApi='/policy/api/v1/infra/tier-0s/' + tier0 + '/route-maps'
        else:
            self.listApi='/policy/api/v1' + t0Path + '/route-maps'
            

    def config(self, t0, name, community, prefix, desc=None,display=True):
        api='/policy/api/v1/infra/tier-0s/' + t0 + '/route-maps/' + name

        data={}
        data['display_name'] = name
        if desc:
            data['description'] = desc

        data['entries'] = []
        
        for p in prefix:
            '''
            format CIDR:GE bits:LE bits:action
            action can be PERMIT, DENY
            GE and LE can be blank
            the CIDR could also be "ANY"
            '''
            prefix = p.split(':')
            pdata={}
            if len(prefix) != 4:
                print("Prefix format: CIDR:GE:LE:<PERMIT,DENY>")
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
        api='/policy/api/v1/infra/tier-0s/' + t0 + '/route-maps/' + name
        self.delete(api=api,verbose=display,codes=[200])
            
        
class Tier1(Nsx_object):
    '''
    Class to manage Tier1 Gateways
    '''
    def __init__(self, mp, site='default'):
        super(self.__class__, self).__init__(mp=mp, site=site)
        self.listApi='/policy/api/v1/infra/tier-1s'

    def config(self, name, preempt="NON_PREEMPTIVE", tier0=None, dhcprelay=None,
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

        if dhcprelay:
            ds=DhcpRelay(mp=self.mp)
            dhcp=ds.getPathByName(name=dhcprelay, display=False)
            if not dhcp:
                print("DHCP relay service %s not found." %dhcprelay)
                return False
            data['dhcp_config_paths'] = [dhcp]

        api='/policy/api/v1/infra/tier-1s/%s' %name
        self.mp.patch(api=api,data=data,verbose=True,codes=[200])

        
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

        api='/policy/api/v1%s/locale-services/%s/interfaces/%s' %(t1path,locale,intName)
        sel.mp.patch(api=api,verbose=True,data=data)

    def getLocale(self,name,display=True):
        url=self.listApi + "/" + name + "/locale-services"
        self.list(api=url,display=display)
        
class Segments(Nsx_object):
    '''
    Class to manage Segments
    '''
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/infra/segments'
        
    def config(self, name, tz, connectPath=None, gw=None, dhcp=None, vlans=None, desc=None):
        '''
        name - name of the segment, will be used as ID for path
        tz = name of the transportzone
        connectPath = name of the logical router if connecting upstream
        gw = Gateway IP address in CIDR
        dhcp = dhcp range
        '''

        api='/policy/api/v1/infra/segments/%s' %name

        data={}
        data['display_name'] = name
        t = TransportZone(mp=self.mp)
        myTz = t.getPathByName(name=tz, display=False)
        if not myTz:
            print("TZ %s not found" %tz)
            return None
        else:
            data['transport_zone_path'] = myTz

        if vlans:
            data['vlan_ids'] = vlans

        data['subnets'] = []
        if gw or dhcp:
            index = 0
            if not dhcp:
                dhcp=[]
            for g in gw or []:
                subnet={}
                subnet['gateway_address'] = g
                i = len(dhcp)-1
                if i>=index:
                    subnet['dhcp_ranges'] = [dhcp[index]]
                index+=1
                data['subnets'].append(subnet)

        if connectPath:
            p=self.getPathByTypeAndName(name=connectPath, types=[Tier0, Tier1],
                                        display=False)
            if not p:
                print("LogicalRouter %s not found for connect Path" %connectPath)
                return None
            else:
                data['connectivity_path'] = p

        self.mp.patch(api=api, data=data,verbose=True, codes=[200])

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
        
        
class IpPool(Nsx_object):
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/infra/ip-pools'

    def config(self,name,cidr,ranges,rangeName,gateway,addrType=None):

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
            range_ips = ranges.split(':')
            if len(range_ips) > 0:
                for ip_range in range_ips:
                    start,end = ip_range.split('-')
                    data['allocation_ranges'].append({'start':start,'end':end})
            data['cidr'] = cidr
            data['gateway_ip'] = gateway
            data['resource_type'] = 'IpAddressPoolStaticSubnet'
            data['parent_path'] = '/infra/ip-pools/%s' %name
            self.mp.patch(api=api, data=data,verbose=True, codes=[200])       

class TNProfile(Nsx_object):

    #from nsxtlib import Uplinkprofile, Pools, Switch
    
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/api/v1/transport-node-profiles'
    def __validateUplinks(self, names, nameList):

        for n in names:
            if n not in nameList:
                return False
        return True
        

    def config(self, name,
               uplinkprofile, pnics, uplinknames,
               hswname,
               tz,
               lldp,
               vmks=None, vmknets=None,
               vmkuninstall=None, vmkuninstnets=None,
               pnicuninstalls=True,
               ippool = None,
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

        T = nsxtlib.Transportzone(mgr=self.mp.mgr)
        data['transport_zone_endpoints'] = []
        foundSwitch = False
        for n in tz:
            t = T.findByName(name=n, display=False)
            if not t:
                print("TransportZone %s not found" %n)
                return None
            else:
                data['transport_zone_endpoints'].append({'transport_zone_id':t['id']})
                if hswname==t['host_switch_name']:
                    foundSwitch = True
        if not foundSwitch:
            print("Host switch name %s not found in any of listed TZs" %hswname)
            return None

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
                                           ippool=ippool)

        if not switchSpec:
            print("Host switch not created properly")
            return None
        data['host_switch_spec'] = {}
        data['host_switch_spec']['resource_type'] = 'StandardHostSwitchSpec'
        data['host_switch_spec']['host_switches'] = [switchSpec]

        api='/api/v1/transport-node-profiles'
        r = self.mp.post(api=api,data=data,verbose=True)

    def __configSwitchSpec(self, data, hswname,
                           uplinkprofile, pnics, uplinknames, lldp=None,
                           vmks=None, vmknets=None,
                           vmkuninstall=None, vmkuninstnets=None,
                           pnicuninstalls=True,
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
            P = nsxtlib.Pools(mgr=self.mp.mgr)
            pool = P.findByName(name=ippool, display=False)
            if not pool:
                print("IP Pool %s not found" %ippool)
                return None
            else:
                ip = {}
                ip['ip_pool_id'] = pool['id']
                ip['resource_type'] = 'StaticIpPoolSpec'
                data['ip_assignment_spec'] = ip
                
        if lldp:
            U = nsxtlib.Uplinkprofile(mgr=self.mp.mgr)
            u = U.findByName(name=lldp,display=False)
            self.jsonPrint(u)
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
            U = nsxtlib.Uplinkprofile(mgr=self.mp.mgr)
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
            print(" Provided uplinks: %s "%uplinkNames)
            print(" Uplink profile link names: %s" %l)
            return None

        
        if not (len(pnics)  <= len(uplinknames)):
            print("The number of PNICs must be equal to or less than the number of profile uplinks")
            return None
            

        _pnics = [ ]
        for i in range(len(pnics)):
            _pnics.append({'device_name':pnics[i], 'uplink_name':uplinknames[i]})
        data['pnics'] = _pnics
        if pnicuninstalls:
            data['pnics_uninstall_migration'] = _pnics
        
        
        

        if vmks:
            if len(vmks) != len(vmknets):
                print("The number of vmknets must be equal the number of vmks to be migrated")
                return None
            S=nsxtlib.Switch(mgr=self.mp.mgr)
            vmk_install_migration = []
            for v in range(len(vmknets)):
                sw = S.findByName(name=vmknets[v],display=False)
                if not sw:
                    print("VMK migration destination network %s does not exist" %vmknets[v])
                    return None
                else:
                    vmk_install_migration.append({'device_name': vmks[v],
                                                  'destination_network': sw['id']})
            data['vmk_install_migration'] = vmk_install_migration

        
        if vmkuninstall:
            if len(vmkuninstall) != len(vmkuninstnets):
                print("The number of vmkuninstnet must equal vmkuninstall")
                return None
            S=nsxtlib.Switch(mgr=self.mp)
            vmk_uninstall_migration = []
            for v in range(len(vmkuninstnets)):
                vmk_uninstall_migration.append({'device_name': vmkuninstall[v],
                                                'destination_network': vmkuninstnets[v]})
            data['vmk_uninstall_migration'] = vmk_uninstall_migration

        return data
        

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
                print (c)
                data['compute_collection_id'] = c['external_id']

                if not c:
                    print("Compute-Collection %s not found" %computecollection)
                    return None
                                            
            if tnprofile:
                T = TNProfile(mp=self.mp)
                t = T.findByName(name=tnprofile, display=False)
                data['transport_node_profile_id'] = t['id']
                
                if not t:
                    print("TN Profile %s not found" %tnprofile)
                    return None
            api='/api/v1/transport-node-collections'
            r = self.mp.post(api=api,data=data,verbose=True)


class Certificate(Nsx_object):
    def __init__(self,mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/infra/certificates'


    def readCert(self,filename):
        fp=open(filename,'r')
        return fp.read()
        
    def importCertificate(self, name, cert, key=None,passphrase=None, description=None):
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

        r = self.mp.patch(api=api,data=data,verbose=True)
        if r.status_code != 200:
            print("Error in importing certificate: %d"%r.status_code)
            return None
        else:
            print(r.status_code)
            return True


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

    def findByName(self, name, display=False):
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
        c = ssl.get_server_certificate(addr={node, port})
        return c

    def getFingerprint(self, node, port=443, digest='sha256'):
        '''
        digest options are sha1 and sha256
        '''
        c =  self.__getCertificate(node=node, port=port)
        x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, c)
        return x509.digest(digest)
        
        
        
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
        r=self.mp.put(api='/api/v1/node/aaa/providers/vidm', data=data, verbose=True)
        if r.status_code != 202:
            print("Error in configuring VIDM, code: %d" %r.status_code)

    def getStatus(self):
        self.mp.get(api='/api/v1/node/aaa/providers/vidm/status', verbose=True)

    def getState(self):
        d=self.list(restUrl='/api/v1/node/aaa/providers/vidm/status', display=False)
        if d['runtime_state'] == 'ALL_OK' and d['vidm_enable'] == True:
            return True
        else:
            return False
        
        
        
    
    
                
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
        self.listApi='/policy/api/v1/infra/dhcp-relay-configs'

    def config(self, name, servers):
        api=self.listApi+'/%s'%name
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
        self.listApi='/policy/api/v1/infra/domains/%s/groups' % self.domain

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
        
        
class Service(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi='/policy/api/v1/infra/services'
        

class SecurityPolicy(Nsx_object):
    def __init__(self, mp, domain='default'):
        super(self.__class__, self).__init__(mp=mp)
        if domain:
            self.domain = domain
        else:
            self.domain = 'default'
        self.listApi='/policy/api/v1/infra/domains/%s/security-policies' % self.domain
    def config(self, name, domain='default', category='Application',
               stateless=False, tcpstrict=False, sequence=None,desc=None):

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

class VirtualMachine(Nsx_object):
    def __init__(self, mp):
        super(self.__class__, self).__init__(mp=mp)
        self.listApi = '/policy/api/v1/infra/realized-state/enforcement-points/%s/virtual-machines' % self.ep

    def tag(self, vmname, tags):
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
            if snat_translation == 'LbSnatIpPool':
                if not snat_pool:
                    print("Must provide IP pool for LbSnatIpPool")
                    return
                snat['ip_addresses'] = []
                for i in snat_pool:
                    ip,mask=i.split('|')
                    ipaddr={}
                    ipaddr['ip_address'] = ip
                    ipaddr['[prefix_length'] = mask
                    snat['ip_addresses'].append(ipaddr)

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
    
