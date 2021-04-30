#!/usr/bin/env python3

import pinit
import getpass
import json
import argparse
import connections
import nsxobjects

def parseParameters():

    parser = argparse.ArgumentParser()
    parser.add_argument('nsxmgr')
    parser.add_argument('-u', '--user', default='admin')
    parser.add_argument('-p', '--password', default='CptWare12345!', help='NSX manager password')
    parser.add_argument('--sessiontimeout', default=None,help='Time for REST calls in seconds')
    parser.add_argument('--certFile', default=None, help='Authenticate using certificate file. '
        'CertFile can be in single .p12 format or commma serperated .crt,.key files. '
        'E.g.: "myCert.p12" OR "myCert.crt,myCert.key"')
    parser.add_argument('--safe', action='store_true', help='Do not send non-safe http requests (POST, PUT, DELETE)')
    parser.add_argument('--cookie', default=None,
                        help="Authenticate using session cookie file")
    parser.add_argument('--policysite', default='default',
                        help="Site - default is: default")
    parser.add_argument('--enforcement', default='default',
                        help="Enforcement point, default: default")
    parser.add_argument('--region', default='default',
                        help="Region or Policy domain")
    parser.add_argument('-g', '--global_infra', action='store_true',
                        help="Use global infra for LM")
    parser.add_argument('-m', '--global_gm', action='store_true',
                        help="Talk talk to Global Manager")

    #subparsers is the NameSpace for all first level commands
    subparsers = parser.add_subparsers(dest='ns', required=True)
    #subparsers.required=True
    
    #Parser for remote session creation
    sessionParser = subparsers.add_parser('session')
    sessionNs = sessionParser.add_subparsers(dest='session', required=True)
    session = sessionNs.add_parser('create')
    session.add_argument('--filename', required=True,
                         help='Filename to store the session cookie')
    
    clusterSpace = subparsers.add_parser('cluster')
    clusterNs = clusterSpace.add_subparsers(dest='cluster', required=True)
    createCommonParsers(parser=clusterNs,
                        names=['list', 'find'])
    cluster_parser = clusterNs.add_parser('info')
    cluster_parser = clusterNs.add_parser('nodes')
    cluster_parser = clusterNs.add_parser('status')
    cluster_parser = clusterNs.add_parser('groupstatus')
    cluster_parser = clusterNs.add_parser('health')
    cluster_parser = clusterNs.add_parser('join')
    cluster_parser.add_argument('--primary', required=True,
                                help='IP/hostname of current cluster member')
    cluster_parser.add_argument('--secondaries', required=True, nargs='+',
                                help='IP/hostname of one more secondary node')
    cluster_parser = clusterNs.add_parser('detach')
    cluster_parser.add_argument('--name', required=True,
                                help="hostname or FQDN of the node")
    cluster_parser.add_argument('--graceful', action='store_true',
                                help="Request graceful shutdown")
    cluster_parser.add_argument('--force', action='store_true',
                                help="Force delete")
    cluster_parser.add_argument('--ignore_repo', action='store_true',
                                help="Ignore repository IP check")
    cluster_parser = clusterNs.add_parser('passwd')
    cluster_parser.add_argument('--node', required=True)
    cluster_parser.add_argument('--username', required=True)
    cluster_parser.add_argument('--oldpasswd', required=True)
    cluster_parser.add_argument('--newpasswd', required=True)
    
    
    cluster_parser = clusterNs.add_parser('vip')
    cluster_vipns = cluster_parser.add_subparsers(dest='clustervip', required=True)
    cluster_vipns_parser = cluster_vipns.add_parser('get')
    cluster_vipns_parser = cluster_vipns.add_parser('clear')
    cluster_vipns_parser = cluster_vipns.add_parser('set')
    cluster_vipns_parser.add_argument('--ip', required=True)

    cluster_parser = clusterNs.add_parser('cert')
    cluster_certns = cluster_parser.add_subparsers(dest='clustercert', required=True)
    cluster_certns_parser = cluster_certns.add_parser('get')
    cluster_certns_parser = cluster_certns.add_parser('set')
    cluster_certns_parser.add_argument('--name', required=True,
                                       help="Name of certificate")
    cluster_certns_parser = cluster_certns.add_parser('clear')
    cluster_certns_parser.add_argument('--name', required=True,
                                            help="Name of certificate")
    cluster_parser = clusterNs.add_parser('fqdn')
    cluster_fqdnns = cluster_parser.add_subparsers(dest='fqdn', required=True)
    fqdn = cluster_fqdnns.add_parser('get')
    fqdn = cluster_fqdnns.add_parser('set')
    fqdn = cluster_fqdnns.add_parser('unset')

    cluster_parser = clusterNs.add_parser('partial-patch')
    cluster_pp = cluster_parser.add_subparsers(dest='partial-patch', required=True)
    pp = cluster_pp.add_parser('get')
    pp = cluster_pp.add_parser('set')
    pp = cluster_pp.add_parser('unset')


    cluster_parser = clusterNs.add_parser('deployment')
    cluster_deployns = cluster_parser.add_subparsers(dest='deployns', required=True)
    deploy = cluster_deployns.add_parser('list')
    deploy = cluster_deployns.add_parser('deploy')
    deploy.add_argument('--hostname', required=True,
                        help="Hostname/fqdn for the appliance")
    deploy.add_argument('--size', required=False, default="MEDIUM",
                        choices=['SMALL', 'MEDIUM', 'LARGE'],
                        help="Appliance form factor")
    deploy.add_argument('--roles', required=False,
                        default=['CONTROLLER', 'MANAGER'],
                        choices=['CONTROLLER', 'MANAGER'],
                        help="Appliance role, you want both controller and manager")
    deploy.add_argument('--pwd', default='CptWare12345!',
                        help="Password for root, admin, audit")
    deploy.add_argument('--vc', required=True,
                        help="Compute Manager Name")
    deploy.add_argument('--vcluster', required=True,
                        help="Cluster name to deploy appliance")
    deploy.add_argument('--cidr', required=True,
                        help="IP Address/mask length of the UA")
    deploy.add_argument('--gateway', required=True, nargs="*",
                        help="List of default gateways")
    deploy.add_argument('--network', required=True,
                        help="Name of the network for management")
    deploy.add_argument('--dns', required=False, nargs="*",
                        default=['10.172.106.1'],
                        help="List of DNS Servers")
    deploy.add_argument('--dnssearch', required=False, nargs="*",
                        default=['cptroot.com'],
                        help="DNS Search")
    deploy.add_argument('--ntp', required=False, nargs="*",
                        default=['dns1.cptroot.com'],
                        help="List of NTP servers")
    deploy.add_argument('--storage', required=True,
                        help="Name of the datastore")
    deploy.add_argument('--diskprovisioning', required=False,
                        default="THIN",
                        choices=["THIN",
                                 "LAZY_ZEROED_THICK",
                                 "EAGER_ZEROED_THICK"],
                        help="Disk provisioning type")
    deploy.add_argument('--no-root-ssh', dest="rootssh",
                        action='store_false',
                        help="Disable root ssh")
    deploy.add_argument('--root-ssh', dest='rootssh',
                        action='store_true',
                        help="Enable root ssh")
    deploy.set_defaults(rootssh=True)
    deploy.add_argument('--enable-ssh', dest='enablessh',
                        action='store_true',
                        help="Enable SSH")
    deploy.add_argument('--disable-ssh', dest='enablessh',
                        action='store_false',
                        help="Enable SSH")
    deploy.set_defaults(enablessh=True)
    
                        
    

    backupSpace = subparsers.add_parser('backup')
    backupNs = backupSpace.add_subparsers(dest='backup', required=True)
    createCommonParsers(parser=backupNs, names=['list'])
    bup = backupNs.add_parser('history')
    bup = backupNs.add_parser('timestamps')
    bup = backupNs.add_parser('config')
    bup.add_argument('--sftpServer', required=True,
                     help="Remote sftp server")
    bup.add_argument('--sftpUser', required=True,
                     help="Remote SFTP username")
    bup.add_argument('--sftpPassword', required=True,
                     help="Remote SFTP password")
    bup.add_argument('--sftpPort', required=False, default=22,
                     help="Remote sftp port")
    bup.add_argument('--sftpDir', required=True,
                     help="Remote sftp directory")
    bup.add_argument('--sftpFingerprint', required=False,
                     help="SFTP fingerprint")
    bup.add_argument('--backupPassphrase', required=True,
                     help="Backup crypto passphrase")
    bup.add_argument('--auto_daily', required=False,
                     action='store_true',
                     help="Schedule daily backups, mutually exclusive with periodic")
    bup.add_argument('--daily_days', required=False,nargs="*",
                     choices=[1,2,3,4,5,6,7],
                     default=[1,2,3,4,5,6,7],
                     help="Days of the week 1-7")
    bup.add_argument('--daily_hour', required=False, type=int,
                     default=1,
                     help="Hour of the day in 24 hours")
    bup.add_argument('--daily_min', required=False, type=int,
                     default=0,
                     help="minute of the hour")
    bup.add_argument('--auto_periodic', required=False,
                     action='store_true',
                     help="Schedule periodic backups, mutually exclusive with auto_daily")
    bup.add_argument('--periodic_interval', required=False,
                     default=360,
                     help="Number of seconds between backups")
    bup.add_argument('--topoChange_auto', required=False,
                     help="Seconds after topo change to do auto backup")
    bup.add_argument('--inventory_interval', required=False,
                     default="240",
                     help="Number of seconds between inventory intervals")
    
    edgeSpace = subparsers.add_parser('edge')
    edgeNs = edgeSpace.add_subparsers(dest='edge', required=True)
    createCommonParsers(parser=edgeNs, names=['list', 'find', 'path'])
    edg = edgeNs.add_parser('state')
    edg.add_argument("--name", required=True)
    edg = edgeNs.add_parser('teps')
    edg.add_argument("--name", required=False)
    edg = edgeNs.add_parser('rteps')
    edg.add_argument('--names', required=False, nargs="*")
    
    
    edg = edgeNs.add_parser("deploy")
    edg.add_argument("--name", required=True)
    edg.add_argument("--size", required=False,
                      default="MEDIUM",
                      choices=['SMALL', 'MEDIUM',
                               'LARGE', 'XLARGE'])
    edg.add_argument("--tz", required=True,nargs="+",
                     help="List of Transport zone names")
    edg.add_argument("--enableSsh", action="store_true")
    edg.add_argument("--enableRootSsh", action="store_true")
    edg.add_argument("--dns", nargs="+", required=True)
    edg.add_argument("--hostname", required=True)
    edg.add_argument("--ntp", nargs="+", required=True)
    edg.add_argument("--domains", nargs="+", required=False)
    edg.add_argument("--rootpw", required=True)
    edg.add_argument("--clipw", required=True)
    edg.add_argument("--auditpw", required=False)
    edg.add_argument("--vc", required=True,
                     help="CM name")
    edg.add_argument("--vcuser", required=False,
                     default="administrator@vsphere.local",
                     help="VC User name")
    edg.add_argument("--vcpasswd", required=False,
                     default="Vmware123!",
                     help="VC Username password")
                     
    edg.add_argument("--cluster", required=True)
    edg.add_argument("--host", required=False)
    edg.add_argument("--storage", required=True)
    edg.add_argument("--ntype", required=False,
                     default="vc",
                     choices=['vc', 'opaque'],
                     help="Find networks on VC natively or use opaque switch")
                              
    edg.add_argument("--fpe0", required=True)
    edg.add_argument("--fpe1", required=True)
    edg.add_argument("--fpe2", required=True)
    edg.add_argument("--mgmtNet", required=True)
    edg.add_argument("--gateway", nargs="+", required=True)
    edg.add_argument("--mgmtIp", required=True)
    edg.add_argument("--mgmtMask", required=True)
    edg.add_argument("--uplinkprofile", required=True)
    edg.add_argument("--nics", nargs="+", required=True)
    edg.add_argument("--ippool", required=True)

                     
    edg = edgeNs.add_parser('inter-site')
    esiteNs = edg.add_subparsers(dest='inter-site', required=True)
    esite = esiteNs.add_parser('bgpNeighbors')
    esite.add_argument('--name', required=True)
    esite = esiteNs.add_parser('bgpSummary')
    esite.add_argument('--name', required=True)
    esite = esiteNs.add_parser('stats')
    esite.add_argument('--name', required=True)
    
                     
                     
    
                      

    edgeClusterSpace = subparsers.add_parser('edgecluster')
    edgeClusterNs = edgeClusterSpace.add_subparsers(dest='edgecluster', required=True)
    createCommonParsers(parser=edgeClusterNs, names=['list', 'find'])
    ec = edgeClusterNs.add_parser('details')
    ec.add_argument('--name', required=False,
                    help="Name of edge cluster, else all")
    ec = edgeClusterNs.add_parser('config')
    ec.add_argument('--name', required=True)
    ec.add_argument('--inter', action='store_true',
                    help="Enable inter site forwarding")
    ec.add_argument('--members', required=True, nargs="*",
                    help="List of TN names for members")
    ec.add_argument('--fd', action='store_true',
                     help="Enable allocaiton based on failure domain")
    ec.add_argument('--ha', nargs="*",
                     help="Cluster Profiles")
    ec = edgeClusterNs.add_parser('intersite')
    ec.add_argument('--name', required=True)
    ec.add_argument('--enable', action='store_true')
    ec = edgeClusterNs.add_parser('enablefd')
    ec.add_argument('--name', required=True)

    ec = edgeClusterNs.add_parser('intersiteStatus')
    ec.add_argument('--name', required=True)
    

    ec = edgeClusterNs.add_parser('setprofile')
    ec.add_argument('--name', required=True,
                    help="Cluster name")
    ec.add_argument('--profile', required=True, nargs="*",
                    help="Cluster Profile name")

    ec = edgeClusterNs.add_parser('configProfile')
    ec.add_argument('--name', required=True)
    ec.add_argument('--bfdInterval', default=1000,
                    help="BFD probe interval")
    ec.add_argument('--bfdMultiple', default=3,
                    help="BFD Dead multiple")
    ec.add_argument('--bfdHops', default=1,
                    help="Max BFD Hops")
    ec.add_argument('--realloc', default=30,
                    help="Standby relocation timer in minutes, min 10, default 30")
    
    globalSpace = subparsers.add_parser('global')
    globalNs = globalSpace.add_subparsers(dest='global', required=True)
    createCommonParsers(parser=globalNs,
                        names=['list'])
    global_parser = globalNs.add_parser('switch')
    global_parser.add_argument('--desc',
                                   help="Set the description")
    global_parser.add_argument('--name',
                                   help='Set the display name')
    global_parser.add_argument('--mtu',
                                   help='Set the MTU')
    global_parser.add_argument('--replication',
                                   choices=[True, False],
                                   help="Enable the global replication mode")
        
    global_parser = globalNs.add_parser('routing')
    global_parser.add_argument('--desc',
                               help="Set the description")
    global_parser.add_argument('--name',
                               help='Set the display name')
    global_parser.add_argument('--mtu',
                               help='Set the MTU')
    global_parser.add_argument('--l3mode',
                               choices=['IPV4_ONLY', 'IPV4_AND_IPV6', 'IPV4_ONLY'],
                               help='Set the MTU')

    global_parser = globalNs.add_parser('policy')
    global_parser.add_argument('--name',
                               help='Set the display name')
    global_parser.add_argument('--desc',
                               help="Set the description")
    global_parser.add_argument('--mtu',
                               help='Set the routing MTU')
    global_parser.add_argument('--toggleFips',
                               action='store_true',
                               help="Toggle LB FIPS mode")
    global_parser.add_argument('--l3mode',
                               choices=['IPV4_ONLY', 'IPV4_AND_IPV6', 'IPV4_ONLY'],
                               help='Set the routing mode')
    global_parser.add_argument('--arp_limit',
                               type=int,
                               help="ARP Limitper gateway, default 50k, range 5k-50k")
    global_parser.add_argument('--uplink_mtu_threshold',
                               type=int,
                               help="Uplink profile maximum MTU, default 9k")
    global_parser.add_argument('--toggle_vdr_change',
                               action='store_true',
                               help="Toggle allow_chaning_vdr_mac_in_use")
    global_parser.add_argument("--vdrMac",
                              help="Change the default VDR MAC 02:50:56:56:44:52")
    global_parser.add_argument('--vdrNestedMac',
                               help="Changed the default nested VDR MAC 02:50:56:44:53")
    
                               
    
    
    dhcpRelaySpace = subparsers.add_parser('dhcprelay')
    dhcpRelayNs = dhcpRelaySpace.add_subparsers(dest='dhcprelay', required=True)
    createCommonParsers(parser=dhcpRelayNs, names=['list', 'path'])
    dhcprelay = dhcpRelayNs.add_parser('config')
    dhcprelay.add_argument('--name', required=True,
                           help="Name of the dhcprelay config")
    dhcprelay.add_argument('--servers', required=True,nargs='+',
                           help="List of dhcp rela servers")
    tnprofileSpace = subparsers.add_parser('tnprofile')
    tnprofileNs = tnprofileSpace.add_subparsers(dest='tnprofile', required=True)
    createCommonParsers(parser=tnprofileNs,
                        names=['list', 'find'])
    tnp_parser = tnprofileNs.add_parser('delete')
    tnp_parser.add_argument('--name', required=True,
                            help="Name of the TransportNode Profile")
    '''
    '''
    tnp_parser = tnprofileNs.add_parser('config')
    tnp_parser.add_argument('--name', required=True,
                            help="Name of the TransportNode Profile")
    tnp_parser.add_argument('--uplinkprofile',
                            help='Name of uplink profile')
    tnp_parser.add_argument('--pnics', nargs='*',
                            help="One or more pnics to map")
    tnp_parser.add_argument('--uplinknames', nargs='*',
                            help="One or more uplink names to map pnics, names should match uplink profile names")
    tnp_parser.add_argument('--hswname',
                            help='Name of the NVDS host switch')
    tnp_parser.add_argument('--lldp',
                            help='Name of the LLDP profile')
    tnp_parser.add_argument('--mode',default='STANDARD',
                            choices=['STANDARD', 'ENS', 'ENS_INTERRRUPT'],
                            help="Switch mode type")
    tnp_parser.add_argument('--swtype', default="NVS",
                            choices=['NVDS', 'VDS'],
                            help="VDS7  or N-VDS")
    tnp_parser.add_argument('--vds', default=None,
                            help="DVS name if it's --swtype VDS")
                                
                            
    tnp_parser.add_argument('--tz', nargs="*",
                            help='List of transport zones')
    tnp_parser.add_argument('--vmks', nargs="*",
                            help="list of VMKernel interfaces to migrate")
    tnp_parser.add_argument('--vmknets', nargs="*",
                            help="List of destinations for vmk migraiton")
    tnp_parser.add_argument('--vmkuninstall', nargs="*",
                            help="list of vmkernel interfaces to migrate from NVDS at uninstall")
    tnp_parser.add_argument('--vmkuninstnets', nargs="*",
                            help="List of destinations for vmk migration from NVDS at uninstall")
    tnp_parser.add_argument('--pnicuninstalls', action='store_true',
                            help="Migrate pnics from NVDS at uninstall?")
    tnp_parser.add_argument('--ippool', required=False,
                            help="Name of IP Pool, DHCP if not specified")
    tnp_parser.add_argument('--desc', required=False,
                            help="Description of this TN Profile")

    tnp_parser = tnprofileNs.add_parser('apply')
    tnp_parser.add_argument('--cluster', required=True,
                            help="Name of the cluster")
    tnp_parser.add_argument('--tnp', required=True,
                            help="Name of the TN Profile, required if applying")

    '''
    '''
    siteSpace = subparsers.add_parser('site')
    siteNs = siteSpace.add_subparsers(dest='site', required=True)
    createCommonParsers(parser=siteNs,
                        names=['list', 'find', 'path'])
    '''
    '''
    enforceSpace = subparsers.add_parser('enforce')
    enforceNs = enforceSpace.add_subparsers(dest='enforce', required=True)
    createCommonParsers(parser=enforceNs,
                        names=['list', 'find', 'path'])
    enforce = enforceNs.add_parser('sync')
    enforce.add_argument('--site', required=False,
                         default='default',
                         help="Site name.  Default is default")
    enforce.add_argument('--name', required=False,
                         default='default',
                         help="Enforcement point name, default is default")
    enforce = enforceNs.add_parser('reload')
    enforce.add_argument('--site', required=False,
                         default='default',
                         help="Site name.  Default is default")
    enforce.add_argument('--name', required=False,
                         default='default',
                         help="Enforcement point name, default is default")
    '''
    '''
    tzSpace = subparsers.add_parser('tz')
    tzNs = tzSpace.add_subparsers(dest='tz', required=True)
    createCommonParsers(parser=tzNs,
                        names=['list', 'find', 'delete'])
    tz_parser = tzNs.add_parser('config')
    tz_parser.add_argument('--name', required=True,
                                help="Name for the transport-zone")
    tz_parser.add_argument('--desc', default=None, 
                                help="Description for the transport-zone")
    tz_parser.add_argument('--teaming', default=None, nargs="*",
                           help="Named teaming policy names")
    tz_parser.add_argument('--hswname', required=False,
                                help="N-VDS name for the transport-zone")
    tz_parser.add_argument('--type', required=False,default='OVERLAY',
                                help="Type for the transport-zone. [OVERLAY|VLAN] Default=OVERLAY")
    tz_parser.add_argument('--isdefault', required=False,
                           action='store_true',
                           help="Set this to TZ to be default")
    tz_parser = tzNs.add_parser('nested')
    tz_parser.add_argument('--name', required=True,
                         help="Name of the TZ")
    tz_parser.add_argument('--enable', action='store_true',
                         help="Enable nested mode")
    tz_parser.add_argument('--disable', action='store_true',
                         help="Disable nested mode")
    
    
    '''
    '''
    ippoolSpace = subparsers.add_parser('ippool')
    ippoolNs = ippoolSpace.add_subparsers(dest='ippool', required=True)
    createCommonParsers(parser=ippoolNs,
                        names=['list', 'find', 'path', 'realization', 'delete'])

    ipp = ippoolNs.add_parser('subnets')
    ipp.add_argument('--name', required=True,
                     help = "Name of the subnet")
    
    ipppool_parser = ippoolNs.add_parser('config')
    ippoolCfgNs = ipppool_parser.add_subparsers(dest='ippoolcfgns', required=True)
    ippoolCfgNs_RangeP = ippoolCfgNs.add_parser('range')
    ippoolCfgNs_RangeP.add_argument('--name', required=True,
                                help="Name of the ippool")
    ippoolCfgNs_RangeP.add_argument('--rangeName', required=True, 
                                help="Name of the ippool range")
    ippoolCfgNs_RangeP.add_argument('--ranges', required=True, nargs="*",
                                help="Allocation ranges for ip pool ex: '10.1.1.1-10.1.1.20:10.1.1.30-10.1.1.50:10.1.1.100-10.1.1.250'")
    ippoolCfgNs_RangeP.add_argument('--cidr', required=True,
                                help="cidr for the ippool range ex: 10.1.1.0/24")
    ippoolCfgNs_RangeP.add_argument('--gateway', required=True,
                                help="gateway ip for the ippool range")
    ippoolCfgNs_RangeP.add_argument('--dns', required=False,nargs='*',
                                    help="One or more DNS servers")
    ippoolCfgNs_RangeP.add_argument('--domain', required=False,
                                    help="DNS domain name")

    '''
    '''
    realizeSpace = subparsers.add_parser('realizealarms')
    realizeNs = realizeSpace.add_subparsers(dest='realizealarms', required=True)
    createCommonParsers(parser=realizeNs,
                        names=['list'])
    alarm_parser = realizeNs.add_parser('cleanup')
    alarm_parser.add_argument('--path', required=True,
                              help="Actual path of alarm from object's alarm, see policy logs, or combined alarm's source_reference with relative_path")
    alarm_parser = realizeNs.add_parser('system')
    '''
    '''
    segmentSpace = subparsers.add_parser('segment')
    segmentNs = segmentSpace.add_subparsers(dest='segment', required=True)
    createCommonParsers(parser=segmentNs,
                        names=['list', 'find', 'path', 'realization', "delete"])
    seg_parser = segmentNs.add_parser('config')
    seg_parser.add_argument('--name', required=True)
    seg_parser.add_argument('--tz', required=False,help="Name of TZ")
    seg_parser.add_argument('--lr', required=False, default=None,
                            help="Logical router to connect to, default none")
    seg_parser.add_argument('--gw', required=False, default=None, nargs='*',
                            help='CIDR of gateway, means LR interface IP')
    seg_parser.add_argument('--dhcp', required=False, default=None,
                            help="Name of dhcp relay config")
    seg_parser.add_argument('--vlans', required=False, default=None, nargs='*', help="List of vlans")
    seg_parser.add_argument('--admin', required=False,
                            choices=['UP','DOWN'],
                            help="Admin State")
    seg_parser.add_argument('--teaming', required=False,
                            help="Teaming policy name")
    seg_parser.add_argument('--mcast', required=False,
                            action='store_true',
                            help="Enable multicast")
    seg_parser.add_argument('--connect', required=False,
                            default="ON",
                            choices=['ON', 'OFF'],
                            help="Connected or disconnected router port")
    seg_parser.add_argument('--vni', required=False,
                            type=int,
                            help="VNI number")

    seg_parser.add_argument('--desc', required=False)
    seg_parser.add_argument('--force', action='store_true',
                            help="Force is required if updating segments that may impact connectivity")

    seg_parser = segmentNs.add_parser('tagSegment')
    seg_parser.add_argument('--name', required=True,
                            help="Name of the segment")
    seg_parser.add_argument('--tags', nargs="+", required=True,
                            help="Tag Spec in form of scope:value")
    seg_parser.add_argument('--replace', required=False,
                            action='store_true',
                            help="If specified, will replace all existing tags")
    seg_parser.add_argument('--partial', required=False,
                            action='store_true',
                            help="If specified, payload will just be tags")
    
    seg_parser = segmentNs.add_parser('tagport')
    seg_parser.add_argument('--name', required=True,
                            help="Name of the segment")
    seg_parser.add_argument('--tagSpec', nargs="+", required=True,
                             help="Tag Spec in form of scope:value")
    seg_parser.add_argument('--replace', required=False,
                             action='store_true',
                             help="If specified, will replace all existing tags")
    seg_parser.add_argument('--portName', required=False,
                             help="Name of port, will tag all ports if not specified")
    seg_parser.add_argument('--glob', required=False,
                             action='store_true',
                             help="If specified, will match portName as a substring of LP's name")

    seg_parser = segmentNs.add_parser('deletePort')
    seg_parser.add_argument('--name', required=True)
    seg_parser.add_argument('--portname',
                             required=False)
    seg_parser.add_argument('--portpath',
                             required=False)
    seg_parser.add_argument('--glob',
                            action='store_true',
                            help="use portname as substring instead of exact match")
    
    port = segmentNs.add_parser('port')
    port.add_argument('--name', required=True, help="Segment Name")
    portNs = port.add_subparsers(dest='port', required=True)
    createCommonParsers(parser=portNs,
                        names=['list', 'path', 'realization'])
    port_parser = portNs.add_parser('config')
    port_parser.add_argument('--portname',
                             required=True,
                             help="Name of port")
    port_parser.add_argument('--vif', default=None,
                             help="Set the VIF ID")
    port_parser.add_argument('--tags', default=None, nargs='*',
                             help="Tags in format of scope:tag-value")

    bgpComSpace = subparsers.add_parser('bgpcommunity')
    bgpComNs = bgpComSpace.add_subparsers(dest='bgpcommunity', required=True)
    createCommonParsers(parser=bgpComNs,
                        names=['list', 'find', 'path', 'realization', 'delete'],
                        arguments=['t0'])
    bgpCom = bgpComNs.add_parser('config')
    bgpCom.add_argument('--t0', required=True,
                        help="Tier0 name")
    bgpCom.add_argument('--name', required=True,
                        help="Name of the BGP Community list")
    bgpCom.add_argument('--comms', required=True,nargs="*",
                        choices=["NO_EXPORT",
                                 "NO_ADVERTISE",
                                 "NO_EXPORT_SUBCONFED"])
                        
                        

    pfxSpace = subparsers.add_parser('prefixlist')
    pfxNs = pfxSpace.add_subparsers(dest='prefixlist', required=True)
    createCommonParsers(parser=pfxNs,
                        names=['list', 'find', 'path', 'realization', "delete"],
                        arguments=['t0'])
    

    pfx_parser = pfxNs.add_parser('config')
    pfx_parser.add_argument('--t0',
                            required=True,
                            help="Policy ID of the Tier0 router")
    pfx_parser.add_argument('--name',
                            required=True,
                            help="Prefix list name")
    pfx_parser.add_argument("--prefix",
                            required=True,
                            nargs="*",
                            help="List of prefixes, format: CIDR,GE,LE,ACTION, \
                            GE and LE can be blank, ACTION must be PERMIT/DENY")
    pfx_parser.add_argument('--desc', default=None)
    
    pfx_parser = pfxNs.add_parser('delete')
    pfx_parser.add_argument('--t0',
                            required=True,
                            help="Policy ID of the Tier0 router")
    pfx_parser.add_argument('--name',
                            required=True,
                            help="Prefix list name")
    rmapSpace = subparsers.add_parser('routemap')
    rmapNs = rmapSpace.add_subparsers(dest='routemap', required=True)
    createCommonParsers(parser=rmapNs,
                        names=['list', 'find', 'path', 'realization', "delete"],
                        arguments=['t0'])
    rmP = rmapNs.add_parser('config')
    rmP.add_argument('--name', required=True)
    rmP.add_argument('--append', action='store_true',
                     help="Append to existing route map if specified")
    rmP.add_argument('--t0', required=True)
    rmP.add_argument('--prefix', required=False, nargs="*",
                     help="Names of prefix lists to match")
    rmP.add_argument('--prefixAction', required=False,
                     choices=['PERMIT', 'DENY'],
                     help="Match action for prefix lists")
    rmP.add_argument('--comm', required=False, nargs="*",
                     help="Names of communities to match")
    rmP.add_argument('--commAction', required=False,
                     choices=["PERMIT", "DENY"],
                     help="match action for communities")
    rmP.add_argument('--asPathPrepend', required=False,
                     help="AS PATH prepend if specified, quoated and space seperated")
    rmP.add_argument('--setCommunity', required=False,
                     help="Set BGP community if specified")
    rmP.add_argument('--localPref', required=False, type=int,
                     help="Set Local Preference if specified")
    rmP.add_argument('--med', required=False,type=int,
                     help="Set BGP Med if specified")
    rmP.add_argument('--weight', required=False, type=int,
                     help="Set weight if specified")
    rmP.add_argument('--preferV6Global', required=False,
                     action='store_true',
                     help="Prefer IPv6 global next hop if specified")
    
    logSpace = subparsers.add_parser('syslog')
    logNs = logSpace.add_subparsers(dest='syslog', required=True)
    createCommonParsers(parser=logNs, names=['list'])
    slog = logNs.add_parser('config')
    slog.add_argument('--name', required=True, help="Export name")
    slog.add_argument('--server', required=True, help="Remove log server")
    slog.add_argument('--protocol', required=True,
                      choices=['TCP', 'UDP', 'TLS', 'LI', 'LI-TLS'],
                      help="Export protocol")
    slog.add_argument('--port', type=int,
                      help="Export port, default is 514")
    slog.add_argument('--level', default="INFO",
                      choices=['EMERG', 'ALERT', 'CRIT', 'ERR',
                               'WARNING', 'NOTICE', 'INFO', 'DEBUG'],
                      help="Export level, default is INFO")
    slog.add_argument('--facilities', nargs="*",
                      choices=['KERN', 'USER', 'MAIL', 'DAEMON',
                               'AUTH', 'SYSLOG', 'LPR', 'NEWS',
                               'UUCP', 'AUTHPRIV', 'FTP', 'CRON',
                               'LOGALERT', 'LOCAL0', 'LOCAL1',
                               'LOCAL2', 'LOCAL3', 'LOCAL4',
                               'LOCAL5', 'LOCAL6', 'LOCAL7'])
    slog.add_argument('--msgids', nargs="*",
                      help="List of MSGIDs")
    slog.add_argument('--structured_data', nargs="*",
                      help="List of structure data to export")
    slog.add_argument('--serverCA', required=False,
                      help="File containing PEM for CA to validate server cert")
    slog.add_argument('--cert', required=False,
                      help="File containing PEM for syslog client cert if using TLS")
    slog.add_argument('--key', required=False,
                      help="File containing PEM for syslog client key if using TLS")
    slog.add_argument('--clientCA', required=False,
                      help="File contaiing PEM for syslog client CA if using TLS")

    slog = logNs.add_parser('remove',
                            help="Delete all syslog exporters")
    slog = logNs.add_parser('verify',
                            help="Verify appliance iptables for exporters")
    slog = logNs.add_parser('status',
                            help="Get syslog service status")
    slog = logNs.add_parser('serviceCtl',
                            help="Service restart,stop,start")
    slog.add_argument('--action', required=True,
                      choices=['start', 'stop', 'restart'])

    pimProfileSpace = subparsers.add_parser('pimProfile')
    pimProfileNs = pimProfileSpace.add_subparsers(dest='pimProfile', required=True)
    createCommonParsers(parser=pimProfileNs, names=['list', 'path', 'find', 'realization',
                                                    'tag', 'delete'])
    pp = pimProfileNs.add_parser('config')
    pp.add_argument('--name', required=True)
    pp.set_defaults(bsm=True)
    pp.add_argument('--enableBsm', action='store_true',
                    help="Enable BSM")
    pp.add_argument('--disableBsm', action='store_false',
                    help="Disable BSM")
    pp.add_argument('--rpmap', required=True, nargs="*",
                    help="RP Mapping.  Format: RP|range1,range2,.. range in CIDR")
    pp.add_argument('--desc', required=False)
                    
    

    t0Space = subparsers.add_parser('tier0')
    t0Ns = t0Space.add_subparsers(dest='tier0', required=True)
    createCommonParsers(parser=t0Ns,
                        names=['list', 'find', 'path', 'realization', "span", "delete", "tag" ])
    t0_parser = t0Ns.add_parser('routes')
    t0_parser.add_argument('--name', required=True,
                           help="Name of Tier0")
    t0_parser = t0Ns.add_parser('fib')
    t0_parser.add_argument('--name', required=True,
                           help="Name of Tier0")
    
    
    t0_parser = t0Ns.add_parser('config')
    t0_parser.add_argument('--name', required=True,
                           help="Name or Policy ID of Tier0 to update or add")
    t0_parser.add_argument('--failover', required=False, default=None,
                           choices=['PREEMPTIVE', 'NON_PREEMPTIVE'],
                           help="Failover mode, defaults to non preemptive on create")
    t0_parser.add_argument('--ha', required=False, default=None,
                           choices=['ACTIVE_ACTIVE', 'ACTIVE_STANDBY'],
                           help="HA mode, defaults to active/active on new create")
    t0_parser.add_argument('--transit', required=False, default=None,
                           nargs='*',
                           help="List of CIDR address for Tier0-Tier1 links")
    t0_parser.add_argument('--dhcprelay', required=False, default=None,
                           help="DHCP relay service name")
    t0_parser.add_argument('--desc', required=False, default=None,
                           help="Description of the Tier0")
    
    t0_parser = t0Ns.add_parser('interface')
    t0_intNs = t0_parser.add_subparsers(dest='t0intNs', required=True)
    t0_int = t0_intNs.add_parser('get')
    t0_int.add_argument('--name', required=True,
                        help="Name of the Tier0 router")
    t0_int.add_argument('--locale', default='default',
                        help="Locale, default is 'default'")
    t0_int.add_argument('--int', default=None,
                        help="Specific interface name")
        
    t0_int = t0_intNs.add_parser('config')
    t0_int.add_argument('--name', required=True,
                        help="Name of the Tier0 router")
    t0_int.add_argument('--int', required=True,
                        help="Interface Name, should be unique")
    t0_int.add_argument('--segment', required=True,
                        help="Name of the segment to connect interface")
    t0_int.add_argument('--ec', required=False,
                        help="Edge Cluster name, required if GM")
    t0_int.add_argument('--cidr', required=True,
                        nargs="*",
                        help="CIDR for interface, 1 or more")
    t0_int.add_argument('--mtu', required=False,
                        default=1500,
                        help="MTU of the interface, default 1500")
    t0_int.add_argument('--edge',
                        required=False,
                        help="Name of the edge if type external")
    t0_int.add_argument('--locale', default='default')
    t0_int.add_argument('--desc', default=None)
    t0_int.add_argument('--type', default="EXTERNAL",
                        choices=['EXTERNAL', 'SERVICE'])
    t0_int.add_argument('--pim', required=False,
                        action='store_true',
                        help="Enable PIM")
    t0_int.add_argument('--pimHelloInterval', default=30,
                        type=int,
                        help="PIM Hello Interval")
    t0_int.add_argument('--pimHoldTime', default=105,
                        type=int,
                        help="PIM Hold time")

    t0_int = t0_intNs.add_parser('delete')
    t0_int.add_argument('--name', required=True)
    t0_int.add_argument('--int', required=True)
    t0_int.add_argument('--locale', default='default')
    t0_int = t0_intNs.add_parser('status')
    t0_int.add_argument('--name', required=True)
    t0_int.add_argument('--int', required=True)
    t0_int.add_argument('--locale', default='default')
    t0_int = t0_intNs.add_parser('stats')
    t0_int.add_argument('--name', required=True)
    t0_int.add_argument('--int', required=True)
    t0_int.add_argument('--locale', default='default')
    t0_int = t0_intNs.add_parser('entities')
    t0_int.add_argument('--locale', default='default')
    t0_int.add_argument('--name', required=True)
    t0_int.add_argument('--int', required=True)

    t0_parser = t0Ns.add_parser('nat')
    t0_natNs = t0_parser.add_subparsers(dest='t0natns', required=True)

    t0_natp = t0_natNs.add_parser('list')
    t0_natp.add_argument('--t0', required=True,
                        help="Name of tier0 router")
    t0_natp.add_argument('--natid', default="USER",
                         choices=['USER', 'DEFAULT', 'INTERNAL'],
                         help="Nat-Id is the Nat Section and default set is USER")

    t0_natp = t0_natNs.add_parser('get')
    t0_natp.add_argument('--t0', required=True,
                        help="Name of tier0 router")
    t0_natp.add_argument('--natrulename', required=True,
                        help="name of natrule")
    t0_natp.add_argument('--natid', default="USER",
                        choices=['USER', 'DEFAULT', 'INTERNAL'],
                        help="Nat-Id is the Nat Section and default set is USER")

    t0_natp = t0_natNs.add_parser('delete')
    t0_natp.add_argument('--t0', required=True,
                        help="Name of tier0 router")
    t0_natp.add_argument('--natrulename', required=True,
                        help="Name of nat rule to delete")
    t0_natp.add_argument('--natid', default="USER",
                         choices=['USER', 'DEFAULT', 'INTERNAL'],
                         help="Nat-Id is the Nat Section and default set is USER")

    t0_natp = t0_natNs.add_parser('config')
    t0_natp.add_argument('--t0', required=True,
                            help="Name of the tier0 router")
    t0_natp.add_argument('--natrulename', required=True, 
                            help="Name of the nat rule to create or update")
    t0_natp.add_argument('--action', required=True,
                         choices=['DNAT', 'SNAT', 'REFLEXIVE', 'NO_SNAT', 'NO_DNAT'],
                         help='set nat action type')
    t0_natp.add_argument('--natid', default="USER",
                         choices=['USER', 'DEFAULT', 'INTERNAL'],
                         help="Nat-Id is the Nat Section and default set is USER")
    t0_natp.add_argument('--translatedip', required=None,
                         help="translated network address|range|cidr - required for all types except NO_SNAT and NO_DNAT")
    t0_natp.add_argument('--sourceip', required=None,
                         help = "source network address|range|cidr - required for all types except DNAT and NO_DNAT")
    t0_natp.add_argument('--destinationip', required=None,
                         help="destination network address|range|cidr - required for DNAT and NO_DNAT")
    t0_natp.add_argument('--desc', default=None)
    t0_natp.add_argument('--service', required=None,
                         help="Name of the service to apply NAT rule, default is ANY")
    t0_natp.add_argument('--appliedto', required=None,
                         help="comma separated list of interfaces nat rule is applied to")
    t0_natp.add_argument('--ruleenabled', required=False,
                         help="set boolean true or false, default is enabled")
    t0_natp.add_argument('--logging', required=False,
                         help="set boolean true to false, logging is disabled by default")
    t0_natp.add_argument('--translatedports', required=None,
                         help="port number or port-range to be translated, default is all ports")
    t0_natp.add_argument('--firewall', required=False,
                         choices=['MATCH_INTERNAL_ADDRESS', 'MATCH_EXTERNAL_ADDRESS', 'BYPASS'],
                         help="firewall config for nat rule")
    t0_natp.add_argument('--priority', required=False)


    t0_parser = t0Ns.add_parser('static')
    t0_staticNs = t0_parser.add_subparsers(dest='t0staticns', required=True)
    t0_staticp = t0_staticNs.add_parser('config')
    t0_staticp.add_argument("--name", required=True,
                            help="Name of the tier0 router")
    t0_staticp.add_argument("--routename", required=True,
                            help="Name for the static route, policy id compliant")
    t0_staticp.add_argument("--cidr", required=True,
                            help="Network CIDR for the route")
    t0_staticp.add_argument("--hops", required=True,
                            nargs='+',
                            help="List of next hops, format: ip:admin_distance")
    
    t0_parser = t0Ns.add_parser('locale')
    t0_localeNs = t0_parser.add_subparsers(dest='t0localens', required=True)
    t0_localeP = t0_localeNs.add_parser('get')
    t0_localeP.add_argument('--name', required=True,
                            help="Name of the Tier0")
    
    t0_localeP = t0_localeNs.add_parser('edgecluster')
    t0_localeP.add_argument('--name', required=True,
                            help="name of the Tier0")
    t0_localeP.add_argument('--cluster', required=True,
                            help="Name of the edge cluster")
    t0_localeP.add_argument('--locale', required=False,
                            default='default')
        
    t0_localeP = t0_localeNs.add_parser('redist')
    t0_localeP.add_argument('--name', required=True,
                            help="name of the Tier0")
    t0_localeP.add_argument('--ec', required=False,
                            help="Name of edge cluster if GM")
    t0_localeP.add_argument('--routemap', required=False,
                            help="Name of route map to use, if specified")
    t0_localeP.add_argument('--types', required=True,
                            nargs='*',
                            choices=['TIER0_STATIC',
                                     'TIER0_CONNECTED',
                                     'TIER0_EXTERNAL_INTERFACE',
                                     'TIER0_SEGMENT',
                                     'TIER0_ROUTER_LINK',
                                     'TIER0_SERVICE_INTERFACE',
                                     'TIER0_DNS_FORWARDER_IP',
                                     'TIER0_IPSEC_LOCAL_IP',
                                     'TIER0_NAT',
                                     'TIER1_NAT',
                                     'TIER1_STATIC',
                                     'TIER1_LB_VIP',
                                     'TIER1_LB_SNAT',
                                     'TIER1_DNS_FORWARDER_IP',
                                     'TIER1_CONNECTED'],
                            help='Set Route Redistribution types')
    t0_localeP.add_argument('--locale', required=False,
                            default='default')
    t0_localeP = t0_localeNs.add_parser('preferredEdge')
    t0_localeP.add_argument('--name', required=True,
                            help="name of the Tier0")
    t0_localeP.add_argument('--edges', required=True,
                            nargs='*',
                            help="List of preferred edge names")
    t0_localeP.add_argument('--locale', required=False,
                            default='default')

    t0_parser = t0Ns.add_parser('bgp')
    t0_bgpNs = t0_parser.add_subparsers(dest='bgpns', required=True)
    t0_bgp = t0_bgpNs.add_parser('get')
    t0_bgp.add_argument('--name', required=True,
                        help="Name of the Tier0 router")
    t0_bgp.add_argument('--locale', default='default',
                        help='Name of locale, default is "default"')
                            
    t0_bgp = t0_bgpNs.add_parser('config')
    t0_bgp.add_argument('--name', required=True,
                        help="Name of the Tier0 router")
    t0_bgp.add_argument('--locale', default='default',
                        help='Name of locale, default is "default"')
    t0_bgp.add_argument('--local_as', required=True, type=int,
                        help="Local AS number")
    t0_bgp.add_argument('--enable_multipathrelax',
                        action='store_true',
                        help="Enable BGP multipath relax, default is enabled")
    t0_bgp.add_argument('--disable_multipathrelax',
                        action='store_true',
                        help="Disable BGP multipath relax, takes precedence over enable")
    t0_bgp.add_argument('--enable_intersr',
                        action='store_true',
                        help="Enable Tier0 Inter-SR routing, default is enabled")
    t0_bgp.add_argument('--disable_intersr',
                        action='store_true',
                        help="Disable inter-SR routing, takes precedence over enable")
    t0_bgp.add_argument('--enable_ecmp',
                        action='store_true',
                        help="Enable BGP ECMP, default is enabled")
    t0_bgp.add_argument('--disable_ecmp',
                        action='store_true',
                        help="Disable BGP ECMP, takes precedence over enable")
    t0_bgp.add_argument('--enable_gr', action='store_true',
                        help="Enable GR.  Legacy method.  Use --grmode instead")
    t0_bgp.add_argument('--disable_gr', action='store_true',
                        help="Disable GR.  Legacy method.  Use --grmode instead")
    t0_bgp.add_argument('--grmode', default="NONE",
                        choices=['NONE', 'DISABLE',
                                 'GR_AND_HELPER',
                                 'HELPER_ONLY'],
                        help="System default is HELPER_ONLY.  Use NONE if you want no-action")
    t0_bgp.add_argument('--gr_restart_timer', default=180, type=int,
                        help="GR restart timer, default 180s")
    t0_bgp.add_argument('--gr_stale_timer', default=600, type=int,
                        help="GR stale timer, default=600s")
    
    
    t0_bgp = t0_bgpNs.add_parser('neighbor')
    t0_bgpNeighborNs = t0_bgp.add_subparsers(dest='bgpNeighborNs', required=True)
    t0_neighbor = t0_bgpNeighborNs.add_parser('get')
    t0_neighbor.add_argument('--name', required=True,
                             help="name of Tier0 router")
    t0_neighbor.add_argument('--locale', default='default',
                             help="Tier0 locale, default is 'default'")

    t0_neighbor = t0_bgpNeighborNs.add_parser('config')
    t0_neighbor.add_argument('--name', required=True,
                             help="name of Tier0 router")
    t0_neighbor.add_argument('--locale', default='default',
                             help="Tier0 locale, default is 'default'")

    t0_neighbor.add_argument('--peer', required=True,
                             help="Peer name")
    t0_neighbor.add_argument('--address', required=True,
                             help="Neighbor IP address")
    t0_neighbor.add_argument('--ipv6', action='store_true',
                             help="Specify this to be IPv6 neigbor")
    t0_neighbor.add_argument('--remoteAs', required=True,
                             help="Neighbor AS number")
    t0_neighbor.add_argument('--holdtime', required=False,
                             default=None,
                             help="BGP hold down time, default 180s")
    t0_neighbor.add_argument('--keepalive', required=False,
                             default=None,
                             help="BGP keepalive timer, default 60s")
    t0_neighbor.add_argument('--secret', required=False,
                             default=None,
                             help="Neighbor password, use empty value '' to clear")
    t0_neighbor.add_argument('--enablebfd', required=False,
                             action='store_true',
                             help="Enable BFD")
    t0_neighbor.add_argument('--disablebfd', required=False,
                             action='store_true',
                             help="Disable BFD, will take precedence over enable")
    t0_neighbor.add_argument('--bfdinterval', required=False,
                             default=None,
                             help="BFD interval in ms, default 1000ms")
    t0_neighbor.add_argument('--bfdmultiple', required=False,
                             default=None,
                             help="BFD Multiplier, default 3")
    t0_neighbor.add_argument('--inprefixlist', required=False,default=None,nargs='*',
                             help="Inbound prefix list")
    t0_neighbor.add_argument('--outprefixlist', required=False, default=None,
                             nargs="*", help="Output prefix list")
    t0_neighbor.add_argument('--sourceip', required=False, default=None, nargs='*',
                             help="Source IP address(s), by default all uplinks")
    t0_neighbor.add_argument('--gr', required=False,
                             choices=["DISABLE", "GR_AND_HELPER", "HELPER_ONLY"],
                             help="Graceful restart mode, default is DISABLE")
    t0_neighbor.add_argument('--desc', required=False,
                             default=None,
                             help="Neighbor description")
    t0_neighbor.add_argument('--ec', required=False,
                             help="Edge cluster name if GM, must also specify --policysite")
    
    t0_neighbor = t0_bgpNeighborNs.add_parser('delete')                            
    t0_neighbor.add_argument('--name', required=True,
                             help="name of Tier0 router")
    t0_neighbor.add_argument('--locale', default='default',
                             help="Tier0 locale, default is 'default'")
    
    t0_neighbor.add_argument('--peer', required=True,
                             help="Peer name")
    t0_neighbor = t0_bgpNeighborNs.add_parser('status')
    t0_neighbor.add_argument('--name', required=True,
                             help="name of Tier0 router")

    t0_PimSpace = t0Ns.add_parser('pim')
    t0PimNs = t0_PimSpace.add_subparsers(dest='pim', required=True)
    t0Pim = t0PimNs.add_parser('get')
    t0Pim.add_argument('--t0', required=True,
                       help="Name of tier0")
    t0Pim = t0PimNs.add_parser('config')
    t0Pim.add_argument('--t0', required=True)
    t0Pim.set_defaults(pimEnable=False)
    t0Pim.add_argument('--enablePim', dest='pimEnable',
                       action='store_true',
                       help="Enable PIM")
    t0Pim.add_argument('--disablePim', dest='pimEnable',
                       action='store_false',
                       help="Disable PIM")
    t0Pim.add_argument('--profile', required=True,
                       help='Name of the PIM Profile')
    t0Pim.add_argument('--replicationRange', required=True,
                       help="CIDR for replication range")
    t0Pim.add_argument('--igmpProfile', required=False,
                       default='default',
                       help="IGMP profile")
    t0Pim.add_argument('--locale',
                       default='default')
    
                       


    
    t1Space = subparsers.add_parser('tier1')
    t1Ns = t1Space.add_subparsers(dest='tier1', required=True)
    createCommonParsers(parser=t1Ns,
                        names=['list', 'find', 'delete', 'path', 'realization', 'span', 'tag'])
    t1_parser = t1Ns.add_parser('config')
    t1_parser.add_argument('--name', required=True)
    t1_parser.add_argument('--tier0', required=False,
                           default=None)
    t1_parser.add_argument('--preempt', required=False,
                           default="NON_PREEMPTIVE",
                           choices=['PREEMPTIVE','NON_PREEMPTIVE'])
    t1_parser.add_argument('--advertisements', default=None,
                           required=False,
                           nargs='+',
                           choices=['TIER1_STATIC_ROUTES',
                                    'TIER1_CONNECTED',
                                    'TIER1_NAT',
                                    'TIER1_LB_VIP',
                                    'TIER1_LB_SNAT',
                                    'TIER1_DNS_FORWARDER_IP'])
    t1_parser.add_argument('--dhcprelay', default=None,required=False,
                           help="Name of dhcprelay config")
    t1_parser.add_argument('--standby_relocate', action='store_true',
                           help="Enable Standby Auto Relocation")

    t1_parser = t1Ns.add_parser('pim')
    t1_parser.add_argument('--t1', required=True,
                           help="Name of the Tier1")
    t1_parser.add_argument('--enable',
                           action='store_true',
                           help="Enable PIM, leave this out to disable")
    t1_parser.add_argument('--log',
                           help="display name for logs")
    t1_parser.add_argument('--locale', default="default")
    
    t1_parser = t1Ns.add_parser('pimstatus')
    t1_parser.add_argument('--t1', required=True,
                           help="Name of Tier1")
    t1_parser.add_argument('--locale', default="default")
    

    t1_parser = t1Ns.add_parser('remove')
    t1_parser.add_argument('--name')

    t1_parser = t1Ns.add_parser('edgecluster')
    t1_parser.add_argument('--name', required=True,
                           help="Name of the Tier1")
    t1_parser.add_argument('--cluster', required=True,
                           help="Name of the edge cluster")
    t1_parser.add_argument('--preferredEdges', required=False,
                           default=None, nargs='+',
                           help="List of edges from the cluster to use")
    t1_parser.add_argument('--locale', required=False,
                           default='default')

    t1_parser = t1Ns.add_parser('locale')
    t1_localeNs = t1_parser.add_subparsers(dest='t1localens', required=True)
    t1_localeP = t1_localeNs.add_parser('get')
    t1_localeP.add_argument('--name', required=True,
                            help="Name of the Tier1")
    
    t1_parser = t1Ns.add_parser('static')
    t1_staticNs = t1_parser.add_subparsers(dest='t1staticns', required=True)
    t1_staticp = t1_staticNs.add_parser('config')
    t1_staticp.add_argument("--t1", required=True,
                            help="Name of the tier0 router")
    t1_staticp.add_argument("--name", required=True,
                            help="Name for the static route, policy id compliant")
    t1_staticp.add_argument("--cidr", required=True,
                            help="Network CIDR for the route")
    t1_staticp.add_argument("--hops", required=True,
                            nargs='+',
                            help="List of next hops, format: ip:admin_distance")
    t1_parser = t1Ns.add_parser('setPrimary')
    t1_parser.add_argument('--name', required=True,
                           help="Name of the Tier1")
    t1_parser.add_argument('--primary', required=True,
                           help="Name of the primary site")
    t1_parser = t1Ns.add_parser('interface')
    t1_intNs = t1_parser.add_subparsers(dest='t1intns', required=True)
    t1_intp = t1_intNs.add_parser('list')
    t1_intp.add_argument('--name', required=True,
                         help="Name of the Tier1 router")

    t1_intp  = t1_intNs.add_parser('add')
    t1_intp.add_argument('--t1', required=True,
                         help="Name of the Tier1 router")
    t1_intp.add_argument('--name', required=True,
                         help="Name of the interface")
    t1_intp.add_argument('--segment', required=True,
                         help="Name of the segment to connect to")
    t1_intp.add_argument('--ip', required=True, nargs='+',
                         help="One or more IP addresses")
    t1_intp.add_argument('--mask', required=True,
                         help="Network mask length")

    t1_parser = t1Ns.add_parser('nat')
    t1_natNs = t1_parser.add_subparsers(dest='t1natns', required=True)

    t1_natp = t1_natNs.add_parser('list')
    t1_natp.add_argument('--t1', required=True,
                         help="Name of tier0 router")
    t1_natp.add_argument('--natid', default="USER",
                         choices=['USER', 'DEFAULT', 'INTERNAL'],
                         help="Nat-Id is the Nat Section and default set is USER")

    t1_natp = t1_natNs.add_parser('get')
    t1_natp.add_argument('--t1', required=True,
                         help="Name of tier0 router")
    t1_natp.add_argument('--natrulename', required=True,
                         help="name of natrule")
    t1_natp.add_argument('--natid', default="USER",
                         choices=['USER', 'DEFAULT', 'INTERNAL'],
                         help="Nat-Id is the Nat Section and default set is USER")

    t1_natp = t1_natNs.add_parser('delete')
    t1_natp.add_argument('--t1', required=True,
                         help="Name of tier1 router")
    t1_natp.add_argument('--natrulename', required=True,
                         help="Name of nat rule to delete")
    t1_natp.add_argument('--natid', default="USER",
                         choices=['USER', 'DEFAULT', 'INTERNAL'],
                         help="Nat-Id is the Nat Section and default set is USER")

    t1_natp = t1_natNs.add_parser('config')
    t1_natp.add_argument('--t1', required=True,
                         help="Name of the tier1 router")
    t1_natp.add_argument('--natrulename', required=True,
                         help="Name of the nat rule to create or update")
    t1_natp.add_argument('--action', required=True,
                         choices=['DNAT', 'SNAT', 'REFLEXIVE', 'NO_SNAT', 'NO_DNAT'],
                         help='set nat action type')
    t1_natp.add_argument('--natid', default="USER",
                         choices=['USER', 'DEFAULT', 'INTERNAL'],
                         help="Nat-Id is the Nat Section and default set is USER")
    t1_natp.add_argument('--translatedip', required=None,
                         help="translated network address|range|cidr - required for all types except NO_SNAT and NO_DNAT")
    t1_natp.add_argument('--sourceip', required=None,
                         help="source network address|range|cidr - required for all types except DNAT and NO_DNAT")
    t1_natp.add_argument('--destinationip', required=None,
                         help="destination network address|range|cidr - required for DNAT and NO_DNAT")
    t1_natp.add_argument('--desc', default=None)
    t1_natp.add_argument('--service', required=None,
                         help="Name of the service to apply NAT rule, default is ANY")
    t1_natp.add_argument('--appliedto', required=None,
                         help="comma separated list of interfaces nat rule is applied to")
    t1_natp.add_argument('--ruleenabled', required=False,
                         help="set boolean true or false, default is enabled")
    t1_natp.add_argument('--logging', required=False,
                         help="set boolean true to false, logging is disabled by default")
    t1_natp.add_argument('--translatedports', required=None,
                         help="port number or port-range to be translated, default is all ports")
    t1_natp.add_argument('--firewall', required=False,
                         choices=['MATCH_INTERNAL_ADDRESS', 'MATCH_EXTERNAL_ADDRESS', 'BYPASS'],
                         help="firewall config for nat rule")
    t1_natp.add_argument('--priority', required=False)

    domainSpace = subparsers.add_parser('domain')
    domainNs = domainSpace.add_subparsers(dest='domain', required=True)
    createCommonParsers(parser=domainNs,
                        names=['list', 'find'])
    domain = domainNs.add_parser('config')
    domain.add_argument('--name', required=True,
                        help="Name - will also be used for ID")
    domain.add_argument('--desc', default=None,
                        help="Description")
    groupSpace = subparsers.add_parser('group')
    groupNs = groupSpace.add_subparsers(dest='group', required=True)
    createCommonParsers(parser=groupNs,
                        names=['list', 'find', 'realization', 'path', "delete", "tag"],
                        arguments=['domain'])

    group = groupNs.add_parser('config')
    group.add_argument('--name', required=True,
                       help="Name of the Group")
    group.add_argument('--domain', default='default',
                       help="Domain.  Default is 'defualt'")
    group.add_argument('--expressions', nargs='+',
                       help="Group membership expressions list.\n"
                       "Each expression can be of the form\n"
                       " conjunction:type:key:operator:value\n"
                       " -conjunction: AND or OR\n"
                       " -type: VirtualMachine, IPSet, LogicalPort, LogicalSwitch\n"
                       " -key: can be Tag for any type\n"
                       "       can also be Name, OSName, ComputerName for VMs\n"
                       " -value: value to match")
    group.add_argument('--vm', default=None, nargs='*',
                       help='List of VirtualMachines by ID')
    group.add_argument('--vif', default=None, nargs='*',
                       help="List of VIFs by ID")
    group.add_argument('--ip', default=None, nargs='*',
                       help='List of IP addresses, each can be a range')
    group.add_argument('--mac', default=None, nargs='*',
                       help='List of MAC addresses')
    group.add_argument('--ports', default=None, nargs='*',
                       help="List of Segment Ports by path")
    group.add_argument('--segments', default=None, nargs='*',
                       help="List of Segments by path")
    group.add_argument('--nsgroups', default=None, nargs='*',
                       help="List of Policy groups by path")
    group.add_argument('--tags', default=None, nargs='*',
                       help="List of tags in format of scope/policy")
    group=groupNs.add_parser('members')
    group.add_argument('--name', required=True)
    group=groupNs.add_parser('ipaddrs')
    group.add_argument('--name', required=True)
    group = groupNs.add_parser('consolidatedMembers')
    group.add_argument('--name', required=True)
    group.add_argument('--site', required=False)
    group.add_argument('--siteid', required=False)
    
    serviceSpace = subparsers.add_parser('service')
    serviceNs = serviceSpace.add_subparsers(dest='service', required=True)
    createCommonParsers(parser=serviceNs,
                        names=['list', 'find', 'realization', 'path', "delete"])
    svc = serviceNs.add_parser('config')
    svc.add_argument('--name', required=True)
    svc.add_argument('--desc', required=False,
                     help='Description')
    svc.add_argument('--entries', nargs="*",
                     help="Service entry in format of name:UDP/TCP:srcPorts:dstPorts, where ports can be space seperated with ranges seperated by -")
    
    policySpace = subparsers.add_parser('policy')
    policySpace.add_argument('--domain', default='default',
                             help="Domain for this policy, default is 'default'")
    policyNs = policySpace.add_subparsers(dest='policy', required=True)
    createCommonParsers(parser=policyNs,
                        names=['list', 'find', 'realization', 'path', "delete", "tag"])
    policy = policyNs.add_parser('config')
    policy.add_argument('--name', required=True,
                        help="Name of the DFW Policy ")
    policy.add_argument('--category', required=False,
                        default='Application',
                        choices=['Ethernet',
                                 'Emergency',
                                 'Infrastructure',
                                 'Environment',
                                 'Application'],
                        help="Policy Category, default is Application")
    policy.add_argument('--stateless', required=False,
                        action='store_true',
                        help="All L3 policies are stateless by default, set stateless to change")
    policy.add_argument('--tcpstrict', required=False,
                        action='store_true',
                        help="Set if require strict TCP handshake for stateful policies")
    policy.add_argument('--sequence', required=False, default=None,type=int,
                        help="Sequence number")
    policy.add_argument('--connectivity', required=False, default="NONE",
                        choices=['NONE', 'WHITELIST', 'BLACKLIST',
                                 'WHITELIST_ENABLE_LOGGING',
                                 'BLACKLIST_ENABLE_LOGGING'],
                        help="Connectivity strategy, default is None")
                                 
    policy.add_argument('--scope', required=False, default=None, nargs="*",
                        help="List of grups for Policy Applied to")
    policy.add_argument('--desc', required=False,
                        default=None,
                        help="Description of the Policy")

    policy = policyNs.add_parser('stats')
    policy.add_argument('--name', required=True,
                        help="Name of the security policy")
    policy.add_argument('--rule', required=False, default=None,
                        help="Name of a rule in the policy")

    position = policyNs.add_parser('position')
    position.add_argument('--name', required=True,
                          help="Name of the policy to reposition")
    position.add_argument('--operation', required=True,
                          default='insert_top',
                          choices=['insert_top', 'insert_bottom',
                                   'insert_before', 'insert_after'],
                          help="Where to position.  Must specify anohter Policy as anchor if before/after")
    position.add_argument('--anchor', default=None,
                          required=False,
                          help="Name of Policy for anchor if insert before or after")
    position.add_argument('--anchordomain', default='default',
                          required=False,
                          help="Domain for the anchor.  default is 'default'")

    
    polDelete = policyNs.add_parser('delete')
    polDelete.add_argument('--name', required=True)
                          
        
    ruleSpace = subparsers.add_parser('rule')
    ruleSpace.add_argument('--domain', default='default')
    ruleSpace.add_argument('--policyname', required=True)
    ruleNs = ruleSpace.add_subparsers(dest='rule', required=True)
    createCommonParsers(parser=ruleNs,
                        names=["list", "find", "realization", "path", "delete", "tag"])
    rule = ruleNs.add_parser('config')
    rule.add_argument('--name', required=True,
                      help="Name of the rule")
    rule.add_argument('--src', default=["ANY"],
                      required=False,
                      nargs='+',
                      help="Source Groups, format: <domain>:<group name> "
                      "or just groupname if same domain as rule  or 'ANY'")
    rule.add_argument('--invertSrc', action='store_true',
                      help="If set, will exclude sources in --src")
    rule.add_argument('--dst', default=["ANY"],
                      required=False,
                      nargs='+',
                      help="Destination group, format: <domain>:<group name> "
                      "or just groupname if same domain as rule  or 'ANY'")
    rule.add_argument('--invertDst', action='store_true',
                      help="if set, will exclude destinations in --dst")
    rule.add_argument('--services', default=["ANY"], nargs='+',
                      help="Names of services. default is 'ANY'")
    rule.add_argument('--protocol', default="IPV4_IPV6",
                      choices=['IPV4_IPV6', 'IPV4', 'IPV6'])
    rule.add_argument('--applyto', default=["ANY"],
                      required=False, nargs='+',
                      help="Apply to.  Default is ANY - meaning apply to DFW. "
                      "Format: <type>:<domain>:value, where type is group, segment "
                      "domain name of domain or blank to be same as rule's domain. "
                      "value is the name to match for that type/domain")
    rule.add_argument('--direction', default="IN_OUT", required=False,
                      choices=['IN', 'OUT', 'IN_OUT'], 
                      help="Direction of traffic, default is IN_OUT")
    rule.add_argument('--action', required=True,
                      choices=['ALLOW', 'DROP', 'REJECT'],
                      help="Action for this rule")
    rule.add_argument('--log', action='store_true',
                      help="If set, will log packet hits")
    rule.add_argument('--disabled', action='store_true',
                      help="if set, rule will be created but disabled")
    rule.add_argument('--sequence', default=None,
                      required=False,
                      help="Sequence number for placing rules")
    
    rule = ruleNs.add_parser('position')
    rule.add_argument('--name', required=True)
    rule.add_argument('--operation', required=True,
                      choices=['insert_top', 'insert_bottom',
                               'insert_before', 'insert_after'],
                      help="Where to insert the rule")
    rule.add_argument('--anchor', default=None,
                      required=False,
                      help="Anchor rule if using insert before/after")
                      
    rule = ruleNs.add_parser('delete')
    rule.add_argument('--name', required=True)
    
    
    vmSpace = subparsers.add_parser('vm')
    vmNs = vmSpace.add_subparsers(dest='vm', required=True)
    createCommonParsers(parser=vmNs,
                        names=["list", "find" ])
    vm = vmNs.add_parser('tagvm')
    vm.add_argument('--vmname', required=True)
    vm.add_argument('--replace', action='store_true',
                    help="Overwrite existing tags")
    vm.add_argument('--tags', required=True,
                    nargs='*',
                    help="Tags in format of <scope:><tag>, use quoted empty to clear all tags")

    certSpace=subparsers.add_parser('cert')
    certNs = certSpace.add_subparsers(dest='cert', required=True)
    createCommonParsers(parser=certNs,
                        names=["list", "find", "realization", "path", "delete"])
    cert = certNs.add_parser('import')
    cert.add_argument('--name', required=True)
    cert.add_argument('--service', action='store_true',
                      help="Service certificate when specified")
    cert.add_argument('--certificate', required=True,
                      help="Certificate PEM file")
    cert.add_argument('--key', required=False,
                      help="Certificate key PEM file")
    cert.add_argument('--passphrase', required=False, default=None,
                      help="Pass phrase")
    cert.add_argument('--desc', required=False, default=None,
                      help="Description for cert")
    cert = certNs.add_parser('applyHttp')
    cert.add_argument('--name',required=True,
                      help="Name of the certificate to apply")
    cert = certNs.add_parser('listMp')
    cert = certNs.add_parser('findMp')
    cert.add_argument('--name', required=True,
                       help="Name of the MP certificate")
    cert = certNs.add_parser('applyAph')
    cert.add_argument('--node', required=True)
    cert.add_argument('--certificate', required=True)
    
    lbSpace = subparsers.add_parser('lb')
    lbNs = lbSpace.add_subparsers(dest='lb', required=True)
    createCommonParsers(parser=lbNs,
                        names=["list", "find", "realization", "path", "delete", "tag"])
    lb = lbNs.add_parser('config')
    lb.add_argument('--name', required=True,
                    help="Name of the LB, will be used for ID")
    lb.add_argument('--size', required=False, default=None,
                    choices=['SMALL', 'MEDIUM', 'LARGE'],
                    help="LB Size.  Default is small if not specified")
                    
    lb.add_argument('--tier1', required=False, default=None,
                    help="Name of the Tier1 to use")
    lb.add_argument('--loglevel', required=False, default=None,
                     choices=['DEBUG', 'INFO', 'WARNING', 'ERROR',
                              'CRITICAL', 'ALERT', 'EMERGENCY'],
                     help="Log level, default is INFO if not specified")
    lb.add_argument('--disable', action='store_true',
                    help="Create in disabled state")
    lbmonitorSpace = lbNs.add_parser('monitoring')
    lbmonitorSpace.add_argument('--name', required=True,
                                help="LB service name")
    lbmonitorSpace.add_argument('--source', required=False,
                                default='cached',
                                choices=['cached', 'realtime'],
                                help="Cached or realtime data")

    lbmonitorNs=lbmonitorSpace.add_subparsers(dest='lbmonitoring', required=True)
    lbmonitor = lbmonitorNs.add_parser('status')
    lbmonitor = lbmonitorNs.add_parser('usage')
    lbmonitor = lbmonitorNs.add_parser('stats')
    lbmonitor = lbmonitorNs.add_parser('poolstatus')
    lbmonitor.add_argument('--pool', required=True,
                           help="Name of the LB pool")
    lbmonitor = lbmonitorNs.add_parser('poolstats')
    lbmonitor.add_argument('--pool', required=True,
                           help="Name of the LB pool")
    lbmonitor = lbmonitorNs.add_parser('vipstatus')
    lbmonitor.add_argument('--vip', required=True,
                           help="Name of the LB VIP")
    lbmonitor = lbmonitorNs.add_parser('vipstats')
    lbmonitor.add_argument('--vip', required=True,
                           help="Name of the LB VIP")
                                      
                                       
    appProfileSpace = lbNs.add_parser('appProfile')
    appProfileNs = appProfileSpace.add_subparsers(dest='appProfile', required=True)
    createCommonParsers(parser=appProfileNs,
                        names=["list", "find", "realization", "path", "delete", "tag"])
    app = appProfileNs.add_parser('config')
    app.add_argument('--name', required=True,
                     help="Name of the appProfile, will be used for ID")
    app.add_argument('--type', required=True,
                     choices=['UDP', 'TCP', 'HTTP'],
                     help="Type of App Profile")
    app.add_argument('--desc', required=False,
                     help="Description for the appprofile")
    app.add_argument('--mirror', required=False,
                     action='store_true',
                     help="Mirror flows to standby for UDP or TCP profile")
    app.add_argument('--idleTimeout', required=False, default=None,
                     help="Session idle timeout.  Defaults: udp-300,tcp-1800, http-15."
                     "This the only configurable option for UDP")
    app.add_argument('--closeTimeout', required=False, default=None,
                     help="TCP Session close timeout.  Apples only to TCP profile.  Default 8")
    
    app.add_argument('--redirectUrl', required=None, default=None,
                     help="HTTP type only. HTTP redidrect URL when VIP down")
    app.add_argument('--httpsRedirect', required=False,
                     action='store_true',
                     help="HTTP type only. Enable HTTP->HTTPS redirect")
    app.add_argument('--ntlm', required=False,
                     action='store_true',
                     help="HTTP type only.  Enable NTLM support")
    app.add_argument('--request_body_size', required=False, default=None,
                     help="HTTP type only.  Max request body size, default unlimited")
    app.add_argument('--request_header_size', required=False, default=None,
                     help="HTTP type only.  Max request header size.  Default 1024")
    app.add_argument('--response_timeout', required=False, default=None,
                     help="HTTP type only.  Server idle timeout. Default 60")
    app.add_argument('--x_forwarded_for', required=False, default=None,
                     choices=['INSERT', 'REPLACE'],
                     help="HTTP type only.  X Forwarded For Type")

    monitorSpace = lbNs.add_parser('monitor')
    monitorNs = monitorSpace.add_subparsers(dest='monitor', required=True)
    createCommonParsers(parser=monitorNs,
                        names=["list", "find", "realization", "path", "delete", "tag"])
    monitor = monitorNs.add_parser('configActive',
                                   help="configure Active Monitor Profile")
    monitor.add_argument('--name', required=True)
    monitor.add_argument('--desc', required=False, default=None,
                         help="Description of the monitor")
    monitor.add_argument('--fallCount', required=False, default=None,
                         help="Number of consecutive fails to mark health down, default 3")
    monitor.add_argument('--riseCount', required=False, default=None,
                         help="Number of consecutive success to bring back DOWN node, default 3")
    monitor.add_argument('--interval', required=False, default=None,
                         help="Interval between health checks, default 5")
    monitor.add_argument('--timeout', required=False, default=None,
                         help="Timeout before health check declares health check fail, default 15")
    monitor.add_argument('--port', required=False, default=None,
                         help="Port to use for health check.  Default is VIP port")
    
    monitor = monitorNs.add_parser('configPassive',
                                   help="configure Passive Monitor Profile")
    monitor.add_argument('--desc', required=False, default=None,
                         help="Description of the monitor")
    monitor.add_argument('--name', required=True)
    monitor.add_argument('--maxfail', required=False, default=None,
                         help="Number of consecutive connection failures, default 5")
    monitor.add_argument('--fallCount', required=False, default=None,
                         help="Number of consecutive fails to mark health down, default 3")
    monitor.add_argument('--riseCount', required=False, default=None,
                         help="Number of consecutive success to bring back DOWN node, default 3")
    monitor.add_argument('--interval', required=False, default=None,
                         help="Interval between health checks, default 5")
    monitor.add_argument('--timeout', required=False, default=None,
                         help="Timeout before health check declares health check fail, default 15")
    monitor.add_argument('--port', required=False, default=None,
                         help="Port to use for health check.  Default is VIP port")
    
    monitor = monitorNs.add_parser('configIcmp',
                                   help="configure ICMP Monitor Profile")
    monitor.add_argument('--name', required=True)
    monitor.add_argument('--desc', required=False, default=None,
                         help="Description of the monitor")
    monitor.add_argument('--datalen', required=False, default=None,
                         help="ICMP data length, default 56")
    monitor.add_argument('--fallCount', required=False, default=None,
                         help="Number of consecutive fails to mark health down, default 3")
    monitor.add_argument('--riseCount', required=False, default=None,
                         help="Number of consecutive success to bring back DOWN node, default 3")
    monitor.add_argument('--interval', required=False, default=None,
                         help="Interval between health checks, default 5")
    monitor.add_argument('--timeout', required=False, default=None,
                         help="Timeout before health check declares health check fail, default 15")
    monitor.add_argument('--port', required=False, default=None,
                         help="Port to use for health check.  Default is VIP port")
    
    monitor = monitorNs.add_parser('configTcp',
                                   help="configure TCP Monitor Profile")
    monitor.add_argument('--name', required=True)
    monitor.add_argument('--desc', required=False, default=None,
                         help="Description of the monitor")
    monitor.add_argument('--send', required=False, default=None,
                         help="Data to send")
    monitor.add_argument('--receive', required=False, default=None,
                         help="Data to receive")
    monitor.add_argument('--fallCount', required=False, default=None,
                         help="Number of consecutive fails to mark health down, default 3")
    monitor.add_argument('--riseCount', required=False, default=None,
                         help="Number of consecutive success to bring back DOWN node, default 3")
    monitor.add_argument('--interval', required=False, default=None,
                         help="Interval between health checks, default 5")
    monitor.add_argument('--timeout', required=False, default=None,
                         help="Timeout before health check declares health check fail, default 15")
    monitor.add_argument('--port', required=False, default=None,
                         help="Port to use for health check.  Default is VIP port")
    
    monitor = monitorNs.add_parser('configUdp',
                                   help="configure UDP Monitor Profile")
    monitor.add_argument('--name', required=True)
    monitor.add_argument('--send', required=True,
                         help="Data to send")
    monitor.add_argument('--receive', required=True,
                         help="Data to receive")
    monitor.add_argument('--desc', required=False, default=None,
                         help="Description of the monitor")
    monitor.add_argument('--fallCount', required=False, default=None,
                         help="Number of consecutive fails to mark health down, default 3")
    monitor.add_argument('--riseCount', required=False, default=None,
                         help="Number of consecutive success to bring back DOWN node, default 3")
    monitor.add_argument('--interval', required=False, default=None,
                         help="Interval between health checks, default 5")
    monitor.add_argument('--timeout', required=False, default=None,
                         help="Timeout before health check declares health check fail, default 15")
    monitor.add_argument('--port', required=False, default=None,
                         help="Port to use for health check.  Default is VIP port")
    
    monitor = monitorNs.add_parser('configHttp',
                                   help="configure HTTP or HTTPSMonitor Profile")
    monitor.add_argument('--name', required=True)
    monitor.add_argument('--type', required=True,
                         choices=['http', 'https'],
                         help="HTTP or HTTPS profile")
    monitor.add_argument('--desc', required=False, default=None,
                         help="Description of the monitor")
    monitor.add_argument('--fallCount', required=False, default=None,
                         help="Number of consecutive fails to mark health down, default 3")
    monitor.add_argument('--riseCount', required=False, default=None,
                         help="Number of consecutive success to bring back DOWN node, default 3")
    monitor.add_argument('--interval', required=False, default=None,
                         help="Interval between health checks, default 5")
    monitor.add_argument('--timeout', required=False, default=None,
                         help="Timeout before health check declares health check fail, default 15")
    monitor.add_argument('--port', required=False, default=None,
                         help="Port to use for health check.  Default is VIP port")
    monitor.add_argument('--request_headers', required=False, default=None,
                         nargs="*",
                         help="Request headers list, format header_name:value")
    monitor.add_argument('--request_body', required=False, default=None,
                         help="Request body")
    monitor.add_argument('--request_method', required=False, default=None,
                         choices=['GET', 'OPTIONS', 'POST', 'HEAD', 'PUT'],
                         help="Request method, default is GET")
    monitor.add_argument('--request_version', required=False, default=None,
                         choices=['HTTP_VERSION_1_0', 'HTTP_VERSION_1_1',
                                  'HTTP_VERSION_2_0'],
                         help="HTTP request version, default HTTP_VERSION_1_1")
    monitor.add_argument('--request_url', required=False, default=None,
                         help="HTTP request URL, default '/'")
    monitor.add_argument('--response_codes', required=False, default=None,
                         nargs='*',
                         help="List of HTTP response codes")
    monitor.add_argument('--response_body', required=False, default=None,
                         help="HTTP Response body, not regex")

    monitor = monitorNs.add_parser('serverSslBinding',
                                   help="Configure Server SSL binding for HTTPS monitor profile")
    monitor.add_argument('--name', required=True,
                         help="Name of the HTTPS monitor profile")
    monitor.add_argument('--certDepth', required=False, default=None,
                         help="Certificate chain depth, default is 3")
    monitor.add_argument('--clientCert', required=False, default=None,
                         help="Client cert for client authentication")
    monitor.add_argument('--serverAuth', required=False,
                         choices=['REQUIRED', 'IGNORE', 'AUTO_APPLY'],
                         help="Server auth mode, default is auto_apply")
    monitor.add_argument('--serverCA', required=False, nargs="*",
                         help="CA certs list for server auth")
    monitor.add_argument('--serverCRL', required=False, nargs="*",
                         help="CRL list for server auth")
    monitor.add_argument('--sslProfile', required=True,
                         help="Name of SSL profile")


    
                         
    
    serverSslSpace = lbNs.add_parser('serverSslProfile')
    serverSslNs = serverSslSpace.add_subparsers(dest='serverSslProfile', required=True)
    createCommonParsers(parser=serverSslNs,
                        names=["list", "find", "realization", "path", "delete", "tag"])
    serverSsl = serverSslNs.add_parser('config')
    serverSsl.add_argument('--name', required=True)
    serverSsl.add_argument('--cipher_group', required=False,default=None,
                           choices=['BALANCED', 'HIGH_SECURITY',
                                    'HIGH_COMPATBILITY',
                                    'CUSTOM'],
                           help="Predefined cipher groups")
    serverSsl.add_argument('--ciphers', required=False,
                           nargs="*", default=None,
                           choices=['TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256',
                                    'TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384',
                                    'TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA',
                                    'TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA',
                                    'TLS_ECDH_ECDSA_WITH_AES_256_CBC_SHA',
                                    'TLS_ECDH_RSA_WITH_AES_256_CBC_SHA',
                                    'TLS_RSA_WITH_AES_256_CBC_SHA',
                                    'TLS_RSA_WITH_AES_128_CBC_SHA',
                                    'TLS_RSA_WITH_3DES_EDE_CBC_SHA',
                                    'TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA',
                                    'TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256',
                                    'TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA384',
                                    'TLS_RSA_WITH_AES_128_CBC_SHA256',
                                    'TLS_RSA_WITH_AES_128_GCM_SHA256',
                                    'TLS_RSA_WITH_AES_256_CBC_SHA256',
                                    'TLS_RSA_WITH_AES_256_GCM_SHA384',
                                    'TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA',
                                    'TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA256',
                                    'TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256',
                                    'TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA384',
                                    'TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384',
                                    'TLS_ECDH_ECDSA_WITH_AES_128_CBC_SHA',
                                    'TLS_ECDH_ECDSA_WITH_AES_128_CBC_SHA256',
                                    'TLS_ECDH_ECDSA_WITH_AES_128_GCM_SHA256',
                                    'TLS_ECDH_ECDSA_WITH_AES_256_CBC_SHA384',
                                    'TLS_ECDH_ECDSA_WITH_AES_256_GCM_SHA384',
                                    'TLS_ECDH_RSA_WITH_AES_128_CBC_SHA',
                                    'TLS_ECDH_RSA_WITH_AES_128_CBC_SHA256',
                                    'TLS_ECDH_RSA_WITH_AES_128_GCM_SHA256',
                                    'TLS_ECDH_RSA_WITH_AES_256_CBC_SHA384',
                                    'TLS_ECDH_RSA_WITH_AES_256_GCM_SHA384'],
                           help="List of ciphers")
    serverSsl.add_argument('--protocols', required=False, default=None,
                           nargs="+",
                           choices=['SSL_V2', 'SSL_V3', 'TLS_V1',
                                    'TLS_V1_1', 'TLS_V1_2'],
                           help="SSL/TLS protocols to support")
    serverSsl.add_argument('--cache', required=False, default=None,
                           action='store_true',
                           help="Enable session cache")
    
    clientSslSpace = lbNs.add_parser('clientSslProfile')
    clientSslNs = clientSslSpace.add_subparsers(dest='clientSslProfile', required=True)
    createCommonParsers(parser=clientSslNs,
                        names=["list", "find", "realization", "path", "delete", "tag"])

    clientSsl = clientSslNs.add_parser('config')
    clientSsl.add_argument('--name', required=True)
    clientSsl.add_argument('--desc', required=False)
    clientSsl.add_argument('--cipher_group', required=False,default=None,
                           choices=['BALANCED', 'HIGH_SECURITY',
                                    'HIGH_COMPATBILITY',
                                    'CUSTOM'],
                           help="Predefined cipher groups")
    clientSsl.add_argument('--ciphers', required=False,
                           nargs="*", default=None,
                           choices=['TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256',
                                    'TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384',
                                    'TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA',
                                    'TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA',
                                    'TLS_ECDH_ECDSA_WITH_AES_256_CBC_SHA',
                                    'TLS_ECDH_RSA_WITH_AES_256_CBC_SHA',
                                    'TLS_RSA_WITH_AES_256_CBC_SHA',
                                    'TLS_RSA_WITH_AES_128_CBC_SHA',
                                    'TLS_RSA_WITH_3DES_EDE_CBC_SHA',
                                    'TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA',
                                    'TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256',
                                    'TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA384',
                                    'TLS_RSA_WITH_AES_128_CBC_SHA256',
                                    'TLS_RSA_WITH_AES_128_GCM_SHA256',
                                    'TLS_RSA_WITH_AES_256_CBC_SHA256',
                                    'TLS_RSA_WITH_AES_256_GCM_SHA384',
                                    'TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA',
                                    'TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA256',
                                    'TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256',
                                    'TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA384',
                                    'TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384',
                                    'TLS_ECDH_ECDSA_WITH_AES_128_CBC_SHA',
                                    'TLS_ECDH_ECDSA_WITH_AES_128_CBC_SHA256',
                                    'TLS_ECDH_ECDSA_WITH_AES_128_GCM_SHA256',
                                    'TLS_ECDH_ECDSA_WITH_AES_256_CBC_SHA384',
                                    'TLS_ECDH_ECDSA_WITH_AES_256_GCM_SHA384',
                                    'TLS_ECDH_RSA_WITH_AES_128_CBC_SHA',
                                    'TLS_ECDH_RSA_WITH_AES_128_CBC_SHA256',
                                    'TLS_ECDH_RSA_WITH_AES_128_GCM_SHA256',
                                    'TLS_ECDH_RSA_WITH_AES_256_CBC_SHA384',
                                    'TLS_ECDH_RSA_WITH_AES_256_GCM_SHA384'],
                           help="List of ciphers")
    clientSsl.add_argument('--protocols', required=False, default=None,
                           nargs="+",
                           choices=['SSL_V2', 'SSL_V3', 'TLS_V1',
                                    'TLS_V1_1', 'TLS_V1_2'],
                           help="SSL/TLS protocols to support")
    clientSsl.add_argument('--cache', required=False, default=None,
                           action='store_true',
                           help="Enable session cache")
    clientSsl.add_argument('--prefer_server_ciphers', default=None,
                           action='store_true',
                           help="Prefer Server's ciphers")
    clientSsl.add_argument('--cache_timeout', required=False,
                           default=None,
                           help="Session cache timeout")
                           

    persistSpace = lbNs.add_parser('persistence')
    persistNs = persistSpace.add_subparsers(dest='persistence', required=True)
    createCommonParsers(parser=persistNs,
                        names=["list", "find", "realization", "path", "delete", "tag"])
                           
    persist = persistNs.add_parser('configSourcePersistence')
    persist.add_argument('--name', required=True)
    persist.add_argument('--desc', required=False)
    persist.add_argument('--shared', required=False, action='store_true',
                         help="Shared persistence across VIPs using this profile")
    persist.add_argument('--purge', required=False, default=None,
                         choices=['FULL', 'NO_PURGE'],
                         help="Default is FULL - meaning purge to make room when table is full")
    persist.add_argument('--timeout', required=False, default=None,
                         help="Persistence expiration, default 300s")
    persist.add_argument('--sync', required=False, default=None,
                         action='store_true',
                         help="Sync persistence entries to HA standby")

    persist = persistNs.add_parser('configCookiePersistence')
    persist.add_argument('--name', required=True)
    persist.add_argument('--desc', required=False)
    persist.add_argument('--shared', required=False, 
                         action='store_true',
                         help="Shared persistence across VIPs using this profile")
    persist.add_argument('--mode', required=False, default=None,
                         choices=['INSERT', 'PREFIX', 'REWRITE'],
                         help="Cookie mode")
    persist.add_argument('--cookie_name', required=False, default=None,
                         help="Cookie name.  default NSXLB")
    persist.add_argument('--cookie_domain', required=False, default=None,
                         help="Cookie domain for insert mode")
    persist.add_argument('--disable_fallback', required=False, default=None,
                         action='store_true',
                         help="Disable cookie fallback")
    persist.add_argument('--disable_garble', required=False, default=None,
                         action='store_true',
                         help="Disable encryption of cookie value")
    persist.add_argument('--cookie_path', required=False, default=None,
                         help="Cookie path for insert mode")
    persist.add_argument('--max_idle', default=None, required=False,
                         help="Max cookie idle time")
    persist.add_argument('--max_life', default=None, required=False,
                         help="Max cookie session life time")
    
    poolSpace = lbNs.add_parser('pool')
    poolNs = poolSpace.add_subparsers(dest='pool', required=True)
    createCommonParsers(parser=poolNs,
                        names=["list", "find", "realization", "path", "delete", "tag"])
    pool = poolNs.add_parser('config')
    pool.add_argument('--name', required=True)
    pool.add_argument('--desc', required=False)
    pool.add_argument('--update', required=False,
                      action='store_true',
                      help="Do a GET to merge new data before PATCH")
    pool.add_argument('--member_group', required=False,
                      help="Group name for dynamic members.  Exlusive with --members")
    pool.add_argument('--algorithm', required=False, default=None,
                      choices=["ROUND_ROBIN", "WEIGHTED_ROUND_ROBIN",
                               "LEAST_CONNECTION", 
                               "WEIGHTED_LEAST_CONNECTION",
                               "IP_HASH"],
                      help="Load balance algorithm, dfault is round robin")
    pool.add_argument('--mg_ip_version', required=False, default=None,
                      choices=['IPV4', 'IPV6', 'IPV4_IPV6'],
                      help="Include only these addresses from group members")
    pool.add_argument('--mg_max_ip', required=None, default=None,
                      help="Max number of IPs to include from group members list")
    pool.add_argument('--mg_adminDown_ips', required=None, default=None,nargs='+',
                      help="List of dynamic member IPs to disable. "
                      "Format: state|ip, where values for state are: "
                      "ENABLED, DISABLED, GRACEFUL_DISABLED")
    pool.add_argument('--mg_port', required=False, default=None,
                      help="Port for dynamic group members")
    pool.add_argument('--members', required=False, default=None,nargs='+',
                      help="List of static members.  Format: "
                      "name|ip|state|backup|maxcon|port|weight "
                      "state values: ENABLED, DISABLED, GRACEFUL_DISABLED. "
                      "backup: true or false"
                      "maxcon: Max number of connections"
                      "port: port to use for this member"
                      "weight: default 1 - member weight, max 256")
    pool.add_argument('--active_monitor', required=False, default=None,
                      help="Name of Active Monitor profile")
    pool.add_argument('--passive_monitor', required=False, default=None,
                      help="Name of Passive Monitor profile")
    pool.add_argument('--snat_translation',required=None, default=None,
                      choices=['LBSnatAutoMap', 'LBSnatDisabled', 'LBSnatIpPool'],
                      help="Source NAT")
    pool.add_argument('--snat_pool', required=False, default=None,nargs='+',
                      help="List of IPs or ranges for LBSnatIpPool."
                      "format example: 10.1.1.1/24 10.1.1.2-10.1.1.10/24")
    pool.add_argument('--tcp_multiplex_enabled', required=False, default=None,
                      action='store_true',
                      help="Enable TCP multiplexing")
    pool.add_argument('--tcp_multiplex_number', required=False, default=None,
                      help="Max # of sessions to to keepalive for multiplexing, default 6")
    
    vipSpace = lbNs.add_parser('vip')
    vipNs = vipSpace.add_subparsers(dest='vip', required=True)
    createCommonParsers(parser=vipNs,
                        names=["list", "find", "realization", "path", "delete", "tag"])
    vip = vipNs.add_parser('config')
    vip.add_argument('--name', required=True)
    vip.add_argument('--update', required=False, action='store_true',
                     help="Do a GET and merge with new content before PATCH")
    vip.add_argument('--desc', required=False, default=None)
    vip.add_argument('--ip', required=True,
                     help="IP Address for the VIP")
    vip.add_argument('--ports', required=True, nargs='+',
                     help="List of ports or port ranges for VIP")
    vip.add_argument('--appProfile', required=True,
                     help="Application profile name")
    vip.add_argument('--enable_access_log', required=False, 
                     action='store_true',
                     help="Enable access logs")
    vip.add_argument('--default_pool_member_ports', required=False, nargs='+',
                     help="Pool member ports if not specified by the pool member")
    vip.add_argument('--disabled', required=False,
                     action='store_true',
                     help="VIP is in disabled state")
    vip.add_argument('--persistProfile', required=False, default=None,
                     help="Name of persistence profile")
    vip.add_argument('--lb_service', required=False, default=None,
                     help="Name of the LB service to attach")
    vip.add_argument('--max_concurrent_connections', required=False, default=None,
                     help="Max concurrent connections")
    vip.add_argument('--max_new_connection_rate', required=False, default=None,
                     help="Max new connection rate")
    vip.add_argument('--pool', required=False, default=None,
                     help="Name of LB pool")
    vip.add_argument('--sorry_pool', required=False, default=None,
                     help="Name of sorry LB pool")
    vip = vipNs.add_parser('serverSslBinding')
    vip.add_argument('--name', required=True,
                         help="Name of the VIP")
    vip.add_argument('--certDepth', required=False, default=None,
                         help="Certificate chain depth, default is 3")
    vip.add_argument('--clientCert', required=False, default=None,
                         help="Client cert for client authentication")
    vip.add_argument('--serverAuth', required=False,
                         choices=['REQUIRED', 'IGNORE', 'AUTO_APPLY'],
                         help="Server auth mode, default is auto_apply")
    vip.add_argument('--serverCA', required=False, nargs="*",
                         help="CA certs list for server auth")
    vip.add_argument('--serverCRL', required=False, nargs="*",
                         help="CRL list for server auth")
    vip.add_argument('--sslProfile', required=True,
                         help="Name of SSL profile")
    
    vip = vipNs.add_parser('clientSslBinding')
    vip.add_argument('--name', required=True,
                         help="Name of the VIP")
    vip.add_argument('--cert', required=True,
                         help="Name of the imported cert for clients")
    vip.add_argument('--certDepth', required=False, default=None,
                         help="Certificate chain depth for client auth, default is 3")
    vip.add_argument('--clientAuth', required=False,
                         choices=['REQUIRED', 'IGNORE'],
                         help="auth mode, default is IGNORE")
    vip.add_argument('--clientCA', required=False, nargs="*",
                         help="CA certs list for CA auth")
    vip.add_argument('--clientCRL', required=False, nargs="*",
                         help="CRL list for client auth")
    vip.add_argument('--sniCerts', required=False, nargs='*',
                     help="List of SNI certificates")
    vip.add_argument('--sslProfile', required=True,
                         help="Name of SSL profile")

    tnSpace = subparsers.add_parser('tn')
    tnNs = tnSpace.add_subparsers(dest='tn', required=True)
    createCommonParsers(parser=tnNs,
                        names=["list", "find", "delete", "tag"])

    tn = tnNs.add_parser('state')
    tn.add_argument('--name', required=False,
                    help="Name of the TN")
    tn.add_argument('--id', required=False,
                    help="ID of the TN")
    tn.add_argument('--ip', required=False,
                    help="IP of the TN")


    tn = tnNs.add_parser('status')
    tn.add_argument('--name', required=False,
                    help="Name of the TN")
    tn.add_argument('--id', required=False,
                    help="ID of the TN")
    tn.add_argument('--ip', required=False,
                    help="IP of the TN")
 
    tn = tnNs.add_parser('pnicStatus')
    tn.add_argument('--name', required=False,
                    help="Name of the TN")
    tn.add_argument('--id', required=False,
                    help="ID of the TN")
    tn.add_argument('--ip', required=False,
                    help="IP of the TN")

    tn = tnNs.add_parser('teps')
    tn.add_argument('--name', required=False,
                    help="Name of the TN")
    tn.add_argument('--id', required=False,
                    help="ID of the TN")
    tn.add_argument('--ip', required=False,
                    help="IP of the TN")
    tn = tnNs.add_parser('tunnels')
    tn.add_argument('--name', required=False,
                    help="Name of the TN")
    tn.add_argument('--id', required=False,
                    help="ID of the TN")
    tn.add_argument('--ip', required=False,
                    help="IP of the TN")
    
    tn = tnNs.add_parser('remoteNodesStatus')
    tn.add_argument('--name', required=False,
                    help="Name of the TN")
    tn.add_argument('--id', required=False,
                    help="ID of the TN")
    tn.add_argument('--ip', required=False,
                    help="IP of the TN")
    
    tn = tnNs.add_parser('resync')
    tn.add_argument('--name', required=False,
                    help="Name of the TN")
    tn.add_argument('--id', required=False,
                    help="ID of the TN")
    tn.add_argument('--ip', required=False,
                    help="IP of the TN")
    
    tn = tnNs.add_parser('capabilities')
    tn.add_argument('--name', required=False,
                    help="Name of the TN")
    tn.add_argument('--id', required=False,
                    help="ID of the TN")
    tn.add_argument('--ip', required=False,
                    help="IP of the TN")

    tn = tnNs.add_parser('interfaces')
    tn.add_argument('--name', required=False,
                    help="Name of the TN")
    tn.add_argument('--id', required=False,
                    help="ID of the TN")
    tn.add_argument('--ip', required=False,
                    help="IP of the TN")
    
    tn = tnNs.add_parser('interfaceStat')
    tn.add_argument('--name', required=False,
                    help="Name of the TN")
    tn.add_argument('--id', required=False,
                    help="ID of the TN")
    tn.add_argument('--ip', required=False,
                    help="IP of the TN")
    tn.add_argument('--interface', required=False,
                    help="Interface ID i.e. name")
    tn.add_argument('--realtime', required=False,
                    action='store_true',
                    help="Real time instead of cached stats")

    tn = tnNs.add_parser('lldpNeighbors')
    tn.add_argument('--name', required=False,
                    help="Name of the TN")
    tn.add_argument('--id', required=False,
                    help="ID of the TN")
    tn.add_argument('--ip', required=False,
                    help="IP of the TN")
    tn.add_argument('--interface', required=False,
                    help="Interface ID i.e. name")

    tn = tnNs.add_parser('addtz')
    tn.add_argument('--node', required=True,
                    help="Name of the TN")
    tn.add_argument('--tz', required=True,
                    help="Name of the TZ")
    tn.add_argument('--swname', required=False,
                    default='nsxDefaultHostSwitch',
                    help="Host switch name to modify; default: nsxDefaultHostSwitch")

    tn = tnNs.add_parser('config')
    tn.add_argument('--node', required=True,
                    help="Name of the node")
    tn.add_argument('--nics', required=True,
                    nargs="*",
                    help="List of pnics")
    tn.add_argument('--uplinkprofile', required=True,
                    help="Name of the uplink profile")
    tn.add_argument('--hswname', required=False,
                    default='nsxDefaultHostSwitch',
                    help="HostSwitchName")
    tn.add_argument('--lldpprofile', required=False,
                    default=None,
                    help="Name of thje LLDP profile")
    tn.add_argument('--ippool', required=False,
                    default=None,
                    help="Name of the IP Pool")
    tn.add_argument('--tzname', required=False,
                    nargs="*",
                    help="TZ name list")

    tn = tnNs.add_parser('update')
    tn.add_argument('--node', required=True,
                    help="Name of the node")
    tn.add_argument('--nics', required=False, nargs="*",
                    help="List of NICs")
    tn.add_argument('--hswname', required=False,
                    help="Host switch name")
    tn.add_argument('--uplinkprofile', required=False,
                    help="Name of uplink profile")
    tn.add_argument('--lldpprofile', required=False,
                    help="Name of the LLDP profile")
    tn.add_argument('--ippool', required=False,
                    help="Name of the IP Pool")
    tn.add_argument('--vmklist', required=False,
                    help="List of vmks to migrate")
    tn.add_argument('--targets', required=False,
                    help="List of targets for VMK migration")
    
            
    tn = tnNs.add_parser('rtep')
    tn.add_argument('--node', required=True,
                    help="Name of the Edge TN")
    tn.add_argument('--ippool', required=True,
                    help="Name of the RTEP Pool")
    tn.add_argument('--vlan', required=True, type=int,
                    help="VLAN ID for the RTEP")
    tn.add_argument('--hsw', required=False,
                    default="nsxDefaultHostSwitch",
                    help="Name of existing hostSwitch to use")

    tn = tnNs.add_parser('setfd')
    tn.add_argument('--node', required=True,
                    help="Name of the Edge TN")
    tn.add_argument('--domain', required=True,
                    help="Name of the Failure Domain")

    tn = tnNs.add_parser('passwd')
    tn.add_argument('--node', required=True)
    tn.add_argument('--username', required=True)
    tn.add_argument('--oldpasswd', required=True)
    tn.add_argument('--newpasswd', required=True)
    
    uplinkSpace = subparsers.add_parser('uplink')
    uplinkNs = uplinkSpace.add_subparsers(dest='uplink', required=True)
    createCommonParsers(parser=uplinkNs,
                        names=["list", "find", "delete", "tag"])
    upl = uplinkNs.add_parser('configLldpProfile')
    upl.add_argument('--name', required=True,
                     help="Name of the uplink profile")
    upl.add_argument('--send', required=False,
                     action='store_true',
                     help="Enable LLDP send if specified")
    upl = uplinkNs.add_parser('configUplinkProfile')
    upl.add_argument("--name", required=True,
                     help="Name of the uplink profile")
    upl.add_argument("--type", required=True,
                     choices=['lag','pnic'],
                     help="Type of uplink profile: LAG or PNIC")
    upl.add_argument("--active", required=True, nargs="*",
                     help="List of active uplink names, LAG will use only one")
    upl.add_argument("--standby", required=False, nargs="*",
                     default=None,
                     help="List of standby uplink names, LAG does not use this")
    upl.add_argument("--policy", required=True,
                     choices=['FAILOVER_ORDER',
                              'LOADBALANCE_SRCID',
                              'LOADBALANCE_SRC_MAC'],
                     help="Load balance policy, LAG will only use FAILOVER regardless")
    upl.add_argument("--vlan", required=False,
                     help="VLAN ID when using profile for overlay.  0 is default")
    upl.add_argument("--mtu", required=False,
                     help="MTU.  Will default to global value if not specified")
    upl.add_argument('--named', required=False, nargs="*",
                     help="List of named uplink polies in format of name:policy:actives:standbys, where policy is from --policy choices, actives and standbys are comma seperated list of links.  Actives must be specified")
    upl.add_argument('--lagmode', default="ACTIVE",
                     choices=["ACTIVE", "PASSIVE"],
                     help="LACP mode when --type is lag")
    upl.add_argument('--laglb', default="SRCDESTIPVLAN",
                      choices=['SRCMAC',
                               'DESTMAC',
                               'SRCDESTMAC',
                               'SRCDESTIPVLAN',
                               'SRCDESTMACIPPORT'],
                      help="LACP load balance algorithm when --type is lag")
    upl.add_argument('--laglinks', default=2, type=int,
                     help="Number of uplinks for the LACP bundle, range: 2-32")
    upl.add_argument('--lagtimeout', default="SLOW",
                     choices=["SLOW", "FAST"],
                     help="LACP timeout type")
    upl.add_argument('--desc',
                     help="Description")
    
                      
    cmSpace = subparsers.add_parser('computeManager')
    cmNs = cmSpace.add_subparsers(dest='computeManager', required=True)
    createCommonParsers(parser=cmNs,
                        names=["list", "find", "delete", "tag"])
    cm = cmNs.add_parser('config')
    cm.add_argument('--name', required=True,
                    help="Display name for this CM")
    cm.add_argument('--server', required=True,
                    help="Server or IP for the CM")
    cm.add_argument('--username', required=True,
                    help="Username used to register")
    cm.add_argument('--passwd', required=True,
                    help="Password for --username")
    cm.add_argument('--thumbprint', required=False,
                    help="Thumbprint for the CM")
    cm.add_argument('--trust', required=False,
                    action='store_true',
                    help="Enable OIDC trust for VC7+")
    cm = cmNs.add_parser('listCluster')
    cm.add_argument('--vc', required=False,
                    help="Name of the vc")
    cm = cmNs.add_parser('findCluster')
    cm.add_argument('--name', required=True,
                    help="name of the cluster")
    cm.add_argument('--vc', required=False,
                    help="Name of the vc")

    cm = cmNs.add_parser('listStorage')
    cm.add_argument('--cluster', required=True,
                    help="Name of the cluster")
    cm.add_argument('--vc', required=False,
                    help="Name of the vc")
    cm = cmNs.add_parser('findStorage')
    cm.add_argument('--name', required=True,
                    help="name of the storage")
    cm.add_argument('--cluster', required=True,
                    help="Name of the cluster")
    cm.add_argument('--vc', required=False,
                    help="Name of the vc")

    cm = cmNs.add_parser('listNetworks')
    cm.add_argument('--cluster', required=True,
                    help="Name of the cluster")
    cm.add_argument('--vc', required=False,
                    help="Name of the vc")
    cm.add_argument('--storage', required=False,
                    help="DatastoreId - required if pre-3.0")
    
    cm = cmNs.add_parser('findNetwork')
    cm.add_argument('--name', required=True,
                    help="name of the Network")
    cm.add_argument('--storage', required=False,
                    help="DatastoreId - required if pre-3.0")
    cm.add_argument('--cluster', required=True,
                    help="Name of the cluster")
    cm.add_argument('--vc', required=False,
                    help="Name of the vc")
    
    tncSpace = subparsers.add_parser('tncollection')
    tncNs = tncSpace.add_subparsers(dest='tncollection', required=True)
    createCommonParsers(parser=tncNs, names=['list','find', 'delete'])
    tnc = tncNs.add_parser('detach')
    tnc.add_argument("--name", required=True,
                     help="Name of the TNC to detatch TNP")
    vdsSpace = subparsers.add_parser('vds')
    vdsNs  = vdsSpace.add_subparsers(dest='vds', required=True)
    createCommonParsers(parser=vdsNs,
                        names=["list", "find"])

    vidmSpace = subparsers.add_parser('vidm')
    vidmNs  = vidmSpace.add_subparsers(dest='vidm', required=True)
    createCommonParsers(parser=vidmNs,
                        names=["list"])
    
    vidm = vidmNs.add_parser('status')
    vidm = vidmNs.add_parser('config')
    vidm.add_argument('--vidmhost', required=True,
                      help="FQDN/IP of the VIDM server")
    vidm.add_argument('--client', required=True,
                      help="VIDM client ID")
    vidm.add_argument('--secret', required=True,
                      help="Secret for VIDM client ID")
    vidm.add_argument('--host', required=True,
                      help="FQDN or IP to register - this is the MP")
    vidm.add_argument('--enable', required=False,
                      action='store_true',
                      help="Enable the VIDM config")
    vidm.add_argument('--lb', required=False,
                      action='store_true',
                      help="Enable the LB flag")

    roleSpace = subparsers.add_parser('role')
    roleNs  = roleSpace.add_subparsers(dest='role', required=True)
    createCommonParsers(parser=roleNs,
                        names=["list"])

    role = roleNs.add_parser('bind')
    role.add_argument('--name', required=True,
                      help="User name")
    role.add_argument('--type', required=False,
                      default="remote_user",
                      choices=["remote_user",
                               "remote_group",
                               "local_user",
                               "principal_identity"])
    role.add_argument('--roles', required=True,
                      nargs='*', choices=["enterprise_admin",
                                          "network_engineer",
                                          "auditor",
                                          "lb_admin",
                                          "security_engineer",
                                          "gi_partner_admin",
                                          "network_op",
                                          "vpn_admin",
                                          "security_op",
                                          "lb_auditor",
                                          "netx_partner_admin"])
    role=roleNs.add_parser('listBindings')
    

    licenseSpace = subparsers.add_parser('license')
    licenseNs = licenseSpace.add_subparsers(dest='license', required=True)
    createCommonParsers(parser=licenseNs, names=['list'])
    lic = licenseNs.add_parser('config')
    lic.add_argument('--key', required=True,
                     help="License Key")

    fdSpace = subparsers.add_parser('faultdomain')
    fdNs = fdSpace.add_subparsers(dest='faultdomain', required=True)
    createCommonParsers(parser=fdNs,
                        names=['list', 'find'])
    fd = fdNs.add_parser('config')
    fd.add_argument('--name', required=True,
                    help="Name of the failure domain")
    fd.add_argument('--setPrefer', action='store_true',
                    help="Set this domain to prefer active services")
    fd.add_argument('--setNotPrefer', action='store_true',
                    help="Set this to not prefer active services")
    fd.add_argument('--desc',
                    help="Failure domain description")
                             
    fedSpace = subparsers.add_parser('federation')
    fedNs = fedSpace.add_subparsers(dest='federation', required=True)
    createCommonParsers(parser=fedNs,
                        names=['list'])
    fed = fedNs.add_parser('makeActive')
    fed.add_argument('--name', required=True,
                     help="Name of the Active Site")
    
    
    # Parse all the argumentes, and ask for password if
    # it's not supplied and not using session/cert auth
    args = parser.parse_args()
    if not args.certFile and not args.cookie:
        if not args.password:
            args.password = getpass.getpass("NSX Manager password: ")
    return args
    
def createCommonParsers(parser, names=[], arguments=None):
    '''
    arguments should be a list, if specified
    '''
    if 'list' in names:
        p = parser.add_parser('list')
        p.add_argument('--brief', action='store_true')
        if arguments:
            for i in arguments:
                arg='--'+i
                p.add_argument(arg)

    if 'find' in names:
        p = parser.add_parser('find')
        p.add_argument('--name')
        p.add_argument('--id')
        if arguments:
            for i in arguments:
                arg='--'+i
                p.add_argument(arg)
    if 'delete' in names:
        p=parser.add_parser('delete')
        p.add_argument('--name', required=True)
        p.add_argument('--force', action='store_true')
        if arguments:
            for i in arguments:
                arg='--'+i
                p.add_argument(arg)
        
    if 'path' in names:
        p = parser.add_parser('path')
        p.add_argument('--name')
        p.add_argument('--id')
        if arguments:
            for i in arguments:
                arg='--'+i
                p.add_argument(arg)

    if 'realization' in names:
        r = parser.add_parser('realization')
        rns = r.add_subparsers(dest="realizationns", required=True)
        if arguments:
            for i in arguments:
                arg='--'+i
                r.add_argument(arg)

        p = rns.add_parser('entities')
        p.add_argument('--name', required=True)

        p = rns.add_parser('status')
        p.add_argument('--name', required=True)
        
    if 'span' in names:
        p=parser.add_parser('span')
        p.add_argument('--name', required=True)
        if arguments:
            for i in arguments:
                arg='--'+i
                p.add_argument(arg)
        

    if 'tag' in names:
        p=parser.add_parser('tag')
        pNs = p.add_subparsers(dest='tagns', required=True)
        t = pNs.add_parser('add')
        t.add_argument("--name", required=True,
                       help="Name of the entity")
        t.add_argument("--tags", required=True, nargs="*",
                       help="Tag spec in list of scope:value")
        t.add_argument("--replace", required=False,
                       action='store_true',
                       help="Replace all existing tags if true")
        d = pNs.add_parser('del')
        d.add_argument("--name", required=True,
                       help="Name of the entity")
        d.add_argument("--tags", required=False, nargs="*",
                       help="List of tags in scope:value to remove, can be false if wipe")
        d.add_argument("--wipe", required=False,
                       action="store_true",
                       help="Delete all tags if specified")
        
def commonHandlers(obj, argsNs, subNs, args, debug=False):
    if debug:
        print("argsNs: %s" %argsNs)
        print("subNs: %s" %subNs)
        print("args: %s" %args)
    if subNs == 'path':
        if not args.name and not args.id:
            print("Must provide either name or id, ID takes precedence")
            return
        if not obj.listApi:
            d=obj.list(display=False)
        else:
            d=None
        if args.id:
            obj.getPathById(id=args.id, data=d,display=True)
        else:
            obj.getPathByName(name=args.name,data=d,display=True)

    elif subNs == 'list':
        obj.list(display=True, brief=args.brief)
    elif subNs == 'find' or subNs == 'show':
        if not args.name and not args.id:
            print("Must provide either name or id, ID takes precedence")
            return

        if not obj.listApi:
            d=obj.list(display=False)
        else:
            d=None

        if args.id:
            obj.findById(id=args.id,data=d,display=True)
        else:
            obj.findByName(name=args.name,data=d,display=True)
    elif subNs == 'delete':
        if not args.name:
            print("Must provide name for delete")
            return
        obj.delete(name=args.name, force=args.force)
    elif subNs == 'realization':
        if args.realizationns == 'entities':
            obj.getRealizationEntities(name=args.name,display=True)
        elif args.realizationns == 'status':
            obj.getRealizationStatus(name=args.name,display=True)
    elif subNs == 'span':
        if not args.name:
            print("Must provide name to get global span")
            return
        obj.getFederationSpan(name=args.name)
    elif subNs == 'tag':
        print(args)
        if args.tagns == 'add':
            obj.addTag(name=args.name, tags=args.tags, replace=args.replace)
        elif args.tagns == 'del':
            obj.delTag(name=args.name, tags=args.tags, wipe=args.wipe)
            

def createNsxObject(objName, mp, args):
    '''
    For every object that inherits from Policy_object to be used from nsxplib, create it here
    '''

    if objName=='cluster':
        return nsxobjects.Cluster(mp=mp)
    elif objName=='global':
        return nsxobjects.GlobalConfigs(mp=mp)
    elif objName=='site':
        return nsxobjects.Sites(mp=mp)
    elif objName=='enforce':
        return nsxobjects.EnforcementPoints(mp=mp)
    elif objName=='tz':
        return nsxobjects.TransportZone(mp=mp)
    elif objName=='segment':
        return nsxobjects.Segments(mp=mp)
    elif objName=='port':
        return nsxobjects.SegmentPort(mp=mp, segmentName=args.name)
    elif objName=='ippool':
        return nsxobjects.IpPool(mp=mp)
    elif objName=='tncollection':
        return nsxobjects.TNCollections(mp=mp)
    elif objName=='computecollection':
        return nsxobjects.ComputeCollections(mp=mp)
    elif objName=='cert':
        return nsxobjects.Certificate(mp=mp)
    elif objName=='realizealarms':
        return nsxobjects.Realization(mp=mp)
    elif objName=='realize':
        return nsxobjects.Realization(mp=mp)
    elif objName=='tier0':
        return nsxobjects.Tier0(mp=mp)
    elif objName=='tier1':
        return nsxobjects.Tier1(mp=mp)
    elif objName=='trust':
        return nsxobjects.PrincipalIdentity(mp=mp)
    elif objName=='role':
        return nsxobjects.Roles(mp=mp)
    elif objName=='vidm':
        return nsxobjects.Vidm(mp=mp)
    elif objName=='edgecluster':
        return nsxobjects.EdgeCluster(mp=mp)
    elif objName=='edge':
        return nsxobjects.Edge(mp=mp)
    elif objName=='dhcprelay':
        return nsxobjects.DhcpRelay(mp=mp)
    elif objName=='bgpcommunity':
        if not args.t0:
            raise ValueError("BGP Community must specify Tier0 router")
        return nsxobjects.BgpCommunity(mp=mp, tier0=args.t0)
    elif objName=='prefixlist':
        if not args.t0:
            raise ValueError("Prefixlist must specify Tier0 router")
        return nsxobjects.PrefixList(mp=mp, tier0=args.t0)
    elif objName=='routemap':
        if not args.t0:
            raise ValueError("RouteMap must specify Tier0 router")
        return nsxobjects.RouteMap(mp=mp, tier0=args.t0)
    elif objName=='domain':
        return nsxobjects.Domain(mp=mp)
    elif objName=='group':
        return nsxobjects.Group(mp=mp)
    elif objName=='service':
        return nsxobjects.Service(mp=mp)
    elif objName=='policy':
        return nsxobjects.SecurityPolicy(mp=mp, domain=args.domain)
    elif objName=="rule":
        return nsxobjects.Rule(mp=mp, policy=args.policyname, domain=args.domain)
    elif objName=='vm':
        return nsxobjects.VirtualMachine(mp=mp)
    elif objName=='lb':
        return nsxobjects.LoadBalancer(mp=mp)
    elif objName=='appProfile':
        return nsxobjects.LBAppProfile(mp=mp)
    elif objName=='monitor':
        return nsxobjects.LBMonitorProfile(mp=mp)
    elif objName=='serverSslProfile':
        return nsxobjects.LBServerSslProfile(mp=mp)
    elif objName=='clientSslProfile':
        return nsxobjects.LBClientSslProfile(mp=mp)
    elif objName=='persistence':
        return nsxobjects.LBPersistenceProfile(mp=mp)
    elif objName=='pool':
        return nsxobjects.LBPool(mp=mp)
    elif objName=='vip':
        return nsxobjects.LBVirtualServer(mp=mp)
    elif objName=='tn':
        return nsxobjects.TransportNode(mp=mp)
    elif objName=='tnprofile':
        return nsxobjects.TNProfile(mp=mp)
    elif objName=='uplink':
        return nsxobjects.HostSwitchProfile(mp=mp)
    elif objName=='computeManager':
        return nsxobjects.ComputeManager(mp=mp)
    elif objName=='vds':
        return nsxobjects.vDS(mp=mp)
    elif objName=='license':
        return nsxobjects.License(mp=mp)
    elif objName=='faultdomain':
        return nsxobjects.FailureDomain(mp=mp)
    elif objName == 'federation':
        return nsxobjects.Federation(mp=mp)
    elif objName == 'appliance':
        return nsxobjects.Appliance(mp=mp)
    elif objName=='backup':
        return nsxobjects.Backup(mp=mp)
    elif objName=='syslog':
        return nsxobjects.Syslog(mp=mp)
    elif objName=='pimProfile':
        return nsxobjects.PimProfile(mp=mp)
    '''
    elif objName=='':
        return nsxobjects.(mp=mp)
    '''
    return None

def main():
    args = parseParameters()
    argsNs = vars(args)

    mp=connections.NsxConnect(server=args.nsxmgr,
                              user=args.user,
                              password=args.password,
                              cookie=args.cookie,
                              cert=args.certFile,
                              global_infra=args.global_infra,
                              global_gm=args.global_gm,
                              site=args.policysite,
                              enforcement=args.enforcement,
                              domain=args.region,
                              timeout=args.sessiontimeout)

    if not args.ns:
        print(args)
        return None

    if args.ns  == 'session':
        if argsNs['session'] == 'create':
            mp.createSessionCookie(filename=args.filename)
        # return here as session is a special case
        return

    obj = createNsxObject(objName=args.ns, mp=mp, args=args)
        
    if args.ns == 'lb' and argsNs['lb'] not in ['list', 'find', 'monitoring',
                                                'realization', 'delete',
                                                'path', 'config']:
        obj=createNsxObject(objName=argsNs['lb'], mp=mp, args=args)
            
    elif args.ns == 'segment' and argsNs['segment'] == 'port':
        obj = createNsxObject(objName=argsNs['segment'], mp=mp, args=args)
            
    if not obj:
        print("Object name %s not handled by createNsxObject()" %args.ns)
        return

    if args.ns=='lb' and argsNs['lb'] not in ['list', 'find', 'monitoring',
                                              'realization', 'delete',
                                              'path', 'config']:
        commonHandlers(obj=obj, argsNs=args.ns, subNs=argsNs[argsNs['lb']], args=args)
    elif args.ns == 'segment' and argsNs['segment'] == 'port':
        commonHandlers(obj=obj, argsNs=args.ns, subNs=argsNs[argsNs['segment']], args=args, debug=True)
    
    else:
        commonHandlers(obj=obj, argsNs=args.ns, subNs=argsNs[args.ns], args=args)
        
    if args.ns == 'cluster':
        if argsNs['cluster'] == 'info':
            obj.info()
        elif argsNs['cluster'] == 'nodes':
            obj.nodes()
        elif argsNs['cluster'] == 'status':
            obj.status()
        elif argsNs['cluster'] == 'health':
            obj.health()
        elif argsNs['cluster'] == 'groupstatus':
            obj.cbmStatus()
        elif argsNs['cluster'] == 'join':
            primary=nsxplib.PolicyNode(host=args.primary, rootpassword=args.npass,
                                adminpassword=args.npass,
                                loglevel=args.loglevel)
            secondaries=[]
            for s in args.secondaries:
                smp=nsxplib.PolicyNode(host=s, adminpassword=args.npass,loglevel=args.loglevel)
                secondaries.append(smp)
            obj.createCluster(primary=primary,secondaries=secondaries)

        elif argsNs['cluster'] == 'passwd':
            obj.setPassword(username=args.username,
                            oldpassword=args.oldpasswd,
                            newpassword=args.newpasswd,
                            node=args.node)
        elif argsNs['cluster'] == 'vip':
            if argsNs['clustervip'] == 'get':
                obj.getClusterIp()
            elif argsNs['clustervip'] == 'clear':
                obj.clearClusterIp()
            elif argsNs['clustervip'] == 'set':
                obj.setClusterIp(addr=args.ip)
        elif argsNs['cluster'] == 'detach':
            obj.detachNode(name=args.name,
                           graceful=args.graceful,
                           force=args.force,
                           ignoreRepo=args.ignore_repo)
            
        elif argsNs['cluster'] == 'cert':
            if argsNs['clustercert'] == 'get':
                obj.getCertificate()
            elif argsNs['clustercert'] == 'clear':
                obj.clearCertificate(certName=args.name)
            elif argsNs['clustercert'] == 'set':
                obj.setCertificate(certName=args.name)
        elif argsNs['cluster'] == 'fqdn':
            if argsNs['fqdn'] == 'get':
                obj.getFqdnMode(display=True)
            elif argsNs['fqdn'] == 'set':
                obj.setFqdnMode()
            elif argsNs['fqdn'] == 'unset':
                obj.unsetFqdnMode()
        elif argsNs['cluster'] == 'partial-patch':
            if argsNs['partial-patch'] == 'get':
                obj.getPartialPatch()
            elif argsNs['partial-patch'] == 'set':
                obj.setPartialPatch(val=True)
            elif argsNs['partial-patch'] == 'unset':
                obj.setPartialPatch(val=False)
                
                
        elif argsNs['cluster'] == 'deployment':
            obj=createNsxObject(objName="appliance", mp=mp, args=args)
            if argsNs['deployns'] == 'list':
                obj.list()
            elif argsNs['deployns'] == 'deploy':
                obj.deploy(hostname=args.hostname,
                           size=args.size,
                           roles=args.roles,
                           password=args.pwd,
                           vc=args.vc,
                           cluster=args.vcluster,
                           rootssh=args.rootssh,
                           ssh=args.enablessh,
                           gateway=args.gateway,
                           cidr=args.cidr,
                           network=args.network,
                           dns=args.dns,
                           dnssearch=args.dnssearch,
                           ntp=args.ntp,
                           diskprovisioning=args.diskprovisioning,
                           storage=args.storage)
                
                
    elif args.ns == 'edge':
        if argsNs['edge'] == 'deploy':
            obj.deployEdge(name=args.name, size=args.size,
                           tznames=args.tz, enableSsh=args.enableSsh,
                           allowRootSsh=args.enableRootSsh,
                           dns=args.dns, hostname=args.hostname,
                           ntp=args.ntp, domains=args.domains,
                           rootpw=args.rootpw, clipw=args.clipw,
                           auditpw=args.auditpw, vc=args.vc,
                           cluster=args.cluster, storage=args.storage,
                           fpe0=args.fpe0, fpe1=args.fpe1, fpe2=args.fpe2,
                           mgmtNet=args.mgmtNet, gateway=args.gateway,
                           mgmtIp=args.mgmtIp, mgmtMask=args.mgmtMask,
                           uplink=args.uplinkprofile, ippool=args.ippool,
                           nics=args.nics, ntype=args.ntype)
        elif argsNs['edge'] == 'state':
            obj.getState(name=args.name)
        elif argsNs['edge'] == 'teps':
            obj.getTeps(name=args.name)
        elif argsNs['edge'] == 'rteps':
            obj.getRTeps(names=args.names)
        elif argsNs['edge'] == 'inter-site':
            if argsNs['inter-site'] == 'bgpNeighbors':
                obj.getInterSiteBgpNeighbors(name=args.name)
            elif argsNs['inter-site'] == 'bgpSummary':
                obj.getInterSiteBgpSummary(name=args.name)
            elif argsNs['inter-site'] == 'stats':
                obj.getInterSiteStats(name=args.name)
                
            
    elif args.ns == 'edgecluster':
        if argsNs['edgecluster'] == 'details':
            obj.getDetail(name=args.name)
        elif argsNs['edgecluster'] == 'config':
            obj.config(name=args.name, members=args.members, fd=args.fd,
                       inter=args.inter, ha=args.ha)
        elif argsNs['edgecluster'] == 'setprofile':
            obj.setHaProfile(cluster=args.name, ha=args.profile)
        elif argsNs['edgecluster'] == 'intersite':
            obj.setInterSite(name=args.name, value=args.enable)
        elif argsNs['edgecluster'] == 'intersiteStatus':
            obj.getInterSiteStatus(name=args.name)
        elif argsNs['edgecluster'] == 'enablefd':
            obj.enableFD(name=args.name)
        elif argsNs['edgecluster'] == 'configProfile':
            obj.configEdgeClusterProfile(name=args.name,
                                         realloc=args.realloc,
                                         bfdint=args.bfdInterval,
                                         bfddead=args.bfdMultiple,
                                         bfdhop=args.bfdHops)
        
    elif args.ns == 'global':
        if argsNs['global'] == 'switch':
            obj.updateSwitchingConfig(name=args.name, desc=args.desc,
                                    mtu=args.mtu,
                                    replication=args.replication)
        elif argsNs['global'] == 'routing':
            obj.updateRoutingConfig(name=args.name, desc=args.desc,
                                    mtu=args.mtu,
                                    l3mode=args.l3mode)
        elif argsNs['global'] == 'policy':
            obj.updateGlobalConfigs(name=args.name, desc=args.desc,
                                     arp_limit=args.arp_limit,
                                     fips=args.toggleFips,
                                     l3mode=args.l3mode,
                                     mtu=args.mtu,
                                     uplink_threshold_mtu=args.uplink_mtu_threshold,
                                     allow_vdr_change=args.toggle_vdr_change,
                                     vdrMac=args.vdrMac,
                                     vdrNested=args.vdrNestedMac)
    elif args.ns == 'enforce':
        if argsNs['enforce'] == 'sync':
            obj.fullSync(site=args.site, ep=args.name)
        elif argsNs['enforce'] == 'reload':
            obj.reload(site=args.site, ep=args.name)
    elif args.ns == 'tnprofile':
        if argsNs['tnprofile'] == 'config':
            obj.config(name = args.name,
                       uplinkprofile=args.uplinkprofile,
                       pnics=args.pnics,
                       uplinknames=args.uplinknames,
                       hswname=args.hswname,
                       tz=args.tz,
                       vds=args.vds,
                       lldp=args.lldp,
                       vmks=args.vmks,
                       vmknets=args.vmknets,
                       vmkuninstall=args.vmkuninstall,
                       vmkuninstnets=args.vmkuninstnets,
                       pnicuninstalls=args.pnicuninstalls,
                       ippool=args.ippool,
                       swtype=args.swtype,
                       mode=args.mode,
                       desc=args.desc)
        elif argsNs['tnprofile'] == 'apply':
            obj.applyToCluster(cluster=args.cluster, tnprofile=args.tnp)
        
        '''
        '''
    elif args.ns == 'tncollection':
        if argsNs['tncollection'] == 'detach':
            obj.detachTnp(name=args.name)
        '''
        '''
    elif args.ns == 'pimProfile':
        if argsNs['pimProfile'] == 'config':
            obj.config(name=args.name, bsm=args.bsm, rps=args.rpmap, desc=args.desc)
            
    elif args.ns == 'tier0':
        if argsNs['tier0'] == 'config':
            obj.config(name=args.name, failover=args.failover,
                       ha=args.ha, transit=args.transit,
                       dhcprelay=args.dhcprelay, desc=args.desc)
        elif argsNs['tier0'] == 'routes':
            obj.getRouteTable(name=args.name, rtype='routing-table')
        elif argsNs['tier0'] == 'fib':
            obj.getRouteTable(name=args.name, rtype='forwarding-table')
        elif argsNs['tier0'] == 'pim':
            if argsNs['pim'] == 'get':
                obj.getPim(t0=args.t0)
            elif argsNs['pim'] == 'config':
                obj.configurePim(t0=args.t0, enable=args.pimEnable,
                                 pimProfile=args.profile,
                                 repRange=args.replicationRange,
                                 igmpProfile=args.igmpProfile,
                                 locale=args.locale)
                
        elif argsNs['tier0'] == 'interface':
            if argsNs['t0intNs'] == 'get':
                obj.getInterfaces(name=args.name, locale=args.locale,
                                  interface=args.int, display=True)
            elif argsNs['t0intNs'] == 'config':
                print(args.ec)
                obj.createInterface(name=args.name, interface=args.int,
                                    segment=args.segment, cidr=args.cidr,
                                    mtu=args.mtu, intType=args.type, ec=args.ec,
                                    edge=args.edge, desc=args.desc,
                                    pim=args.pim, pimHold=args.pimHoldTime,
                                    pimHello=args.pimHelloInterval,
                                    locale=args.locale)
            elif argsNs['t0intNs'] == 'delete':
                obj.deleteInterface(name=args.name, interface=args.int,
                                    locale=args.locale, display=True)
            elif argsNs['t0intNs'] == 'status':
                i = obj.getInterfaces(name=args.name, interface=args.int,
                                      locale=args.locale, display=False)
                if i:
                    obj.getRealizationStatus(path=i['path'], display=True)
            elif argsNs['t0intNs'] == 'stats':
                i = obj.getInterfaces(name=args.name, interface=args.int,
                                      stats=True,locale=args.locale,
                                      display=True)
                    
            elif argsNs['t0intNs'] == 'entities':
                i = obj.getInterfaces(name=args.name, interface=args.int,
                                      locale=args.locale, display=False)
                if i:
                    obj.getRealizationEntities(path=i['path'], display=True)

        elif argsNs['tier0'] == 'nat':
            if argsNs['t0natns'] == 'list':
                obj.listTier0NatRules(t0=args.t0,natid=args.natid,display=True)

            if argsNs['t0natns'] == 'get':
                obj.getNatRule(t0=args.t0, natrulename=args.natrulename, natid=args.natid,
                               display=True)
          
            if argsNs['t0natns'] == 'delete':
                obj.deleteNatRule(t0=args.t0, natrulename=args.natrulename, display=True)

            if argsNs['t0natns'] == 'config':
                obj.configNatRule(t0=args.t0, natrulename=args.natrulename,
                               action=args.action, translatedip=args.translatedip,
                               sourceip=args.sourceip, destinationip=args.destinationip,
                               desc=args.desc, service=args.service, appliedto=args.appliedto,
                               ruleenabled=args.ruleenabled, logging=args.logging,
                               translatedports=args.translatedports, firewall=args.firewall,
                               priority=args.priority, display=True)

        elif argsNs['tier0'] == 'static':
            if argsNs['t0staticns'] == 'config':
                obj.addStaticRoute(name=args.name, routename=args.routename,
                                   cidr=args.cidr, hops=args.hops, display=True)
        elif argsNs['tier0'] == 'locale':
            if argsNs['t0localens'] == 'get':
                obj.getLocale(name=args.name,display=True)
            elif argsNs['t0localens'] == 'redist':
                obj.setRouteDistribution(name=args.name, locale=args.locale, ec=args.ec,
                                         rm=args.routemap, redist=args.types)
            elif argsNs['t0localens'] == 'edgecluster':
                #print("clustername: %s" %args.cluster)
                obj.setEdgeCluster(name=args.name, locale=args.locale,
                                   clustername=args.cluster)
            elif argsNs['t0localens'] == 'preferredEdge':
                obj.setPreferredEdges(name=args.name, edges=args.edge, locale=args.locale)
                
        elif argsNs['tier0'] == 'bgp':
            if argsNs['bgpns'] == 'get':
                obj.getBgpConfig(name=args.name, locale=args.locale,display=True)
            elif argsNs['bgpns'] == 'config':
                obj.configBgp(name=args.name, locale=args.locale, localas=args.local_as,
                              enable_multipathrelax=args.enable_multipathrelax,
                              disable_multipathrelax=args.disable_multipathrelax,
                              enable_intersr=args.enable_intersr,
                              disable_intersr=args.disable_intersr,
                              enable_ecmp=args.enable_ecmp,
                              disable_ecmp=args.disable_ecmp,
                              enable_gr=args.enable_gr,
                              grmode=args.grmode,
                              gr_restart_timer=args.gr_restart_timer,
                              gr_stale_timer=args.gr_stale_timer,
                              disable_gr=args.disable_gr,
                              display=True)
            elif argsNs['bgpns'] == 'neighbor':
                if argsNs['bgpNeighborNs'] == 'get':
                    obj.getBgpNeighbors(name=args.name, locale=args.locale,display=True)
                elif argsNs['bgpNeighborNs'] == 'config':
                    obj.configBgpNeighbor(name=args.name, neighborAddr = args.address,
                                          ipv6=args.ipv6,
                                          remoteAs=args.remoteAs, neighborName = args.peer,
                                          neighborDesc=args.desc, holdtime=args.holdtime,
                                          keepalive=args.keepalive,
                                          password=args.secret,
                                          locale=args.locale,
                                          enablebfd=args.enablebfd,
                                          disablebfd=args.disablebfd,
                                          bfdInterval=args.bfdinterval,
                                          bfdMultiple=args.bfdmultiple,
                                          inPrefixList=args.inprefixlist,
                                          outPrefixList=args.outprefixlist,
                                          gr=args.gr,
                                          sourceIp=args.sourceip,
                                          ec=args.ec,
                                          display=True)
                elif argsNs['bgpNeighborNs'] == 'delete':
                    obj.deleteBgpNeighbor(name=args.name, locale=args.locale,
                                          neighborName=args.peer, display=True)
                elif argsNs['bgpNeighborNs'] == 'status':
                    obj.getBgpNeighborStatus(name=args.name, display=True)
                              
        '''
        '''
    elif args.ns == 'routemap':
        if argsNs['routemap'] == 'config':
            obj.config(name=args.name, append=args.append,
                       community=args.comm,
                       comAction=args.commAction,
                       prefix=args.prefix,
                       prefixAction=args.prefixAction,
                       asprepend=args.asPathPrepend,
                       setcomm=args.setCommunity,
                       localpref=args.localPref,
                       med=args.med,
                       preferv6nh=args.preferV6Global,
                       weight=args.weight)
        '''
        '''
    elif args.ns == 'tier1':
        if argsNs['tier1'] == 'config':
            obj.config(name=args.name, preempt=args.preempt, tier0=args.tier0,
                       standby_relocate=args.standby_relocate,
                       advertisements=args.advertisements, dhcprelay=args.dhcprelay)
        elif argsNs['tier1'] == 'pim':
            obj.setMulticast(name=args.t1, enable=args.enable, log=args.log,
                             locale=args.locale)
        elif argsNs['tier1'] == 'pimstatus':
            obj.getMulticast(name=args.t1, locale=args.locale, display=True)
        elif argsNs['tier1'] == 'remove':
            obj.deleteT1(name=args.name)
        elif argsNs['tier1'] == 'edgecluster':
            obj.setEdgeCluster(name=args.name, clustername=args.cluster,
                               edges=args.preferredEdges,
                               locale=args.locale)
        elif argsNs['tier1'] == 'locale':
            if argsNs['t1localens'] == 'get':
                obj.getLocale(name=args.name,display=True)
        elif argsNs['tier1'] == 'static':
            if argsNs['t1staticns'] == 'config':
                obj.addStaticRoute(t1=args.t1, routename=args.name,
                                   cidr=args.cidr, hops=args.hops)
        elif argsNs['tier1'] == 'interface':
            if argsNs['t1intns'] == 'list':
                obj.getInterfaces(tier1=args.name,display=True)
            elif argsNs['t1intns'] == 'add':
                obj.configInterface(tier1=args.t1, intName=args.name,
                                    segment=args.segment,
                                    addrs=args.ip, mask=args.mask)
        elif argsNs['tier1'] == 'nat':
            if argsNs['t1natns'] == 'list':
                obj.listTier1NatRules(t1=args.t1, natid=args.natid, display=True)

            if argsNs['t1natns'] == 'get':
                obj.getNatRule(t1=args.t1, natrulename=args.natrulename, natid=args.natid,
                               display=True)

            if argsNs['t1natns'] == 'delete':
                obj.deleteNatRule(t1=args.t1, natrulename=args.natrulename, display=True)

            if argsNs['t1natns'] == 'config':
                obj.configNatRule(t1=args.t1, natrulename=args.natrulename,
                                  action=args.action, translatedip=args.translatedip,
                                  sourceip=args.sourceip, destinationip=args.destinationip,
                                  desc=args.desc, service=args.service, appliedto=args.appliedto,
                                  ruleenabled=args.ruleenabled, logging=args.logging,
                                  translatedports=args.translatedports, firewall=args.firewall,
                                  priority=args.priority, display=True)
        elif argsNs['tier1'] == 'setPrimary':
            obj.setPrimarySite(name=args.name, primary=args.primary)
    elif args.ns == 'prefixlist':
        if argsNs['prefixlist'] == 'config':
            obj.config(t0=args.t0,
                       name=args.name,
                       prefix=args.prefix,
                       desc=args.desc, display=True)
        elif argsNs['prefixlist'] == 'delete':
            obj.deletePrefixList(t0=args.t0, name=args.name, display=True)

    elif args.ns == 'bgpcommunity':
        if argsNs['bgpcommunity'] == 'config':
            obj.config(t0=args.t0, name=args.name,
                       communities=args.comms)
    elif args.ns == 'segment':
        if argsNs['segment'] == 'config':
            obj.config(name=args.name,
                       tz=args.tz,
                       force=args.force,
                       admin=args.admin,
                       teaming=args.teaming,
                       connectPath=args.lr,
                       gw=args.gw,
                       dhcp=args.dhcp,
                       vlans=args.vlans,
                       mcast=args.mcast,
                       connect=args.connect,
                       vni=args.vni,
                       desc=args.desc)
        elif argsNs['segment'] == 'tagSegment':
            obj.tagSegment(segmentName=args.name, tags=args.tags,
                           replace=args.replace,
                           partial=args.partial)
        elif argsNs['segment'] == 'tagport':
            obj.tagPort(segmentName=args.name, tagSpec=args.tagSpec,
                        portName=args.portName, replace=args.replace,
                        glob=args.glob)
        elif argsNs['segment'] == 'deletePort':
            obj.deletePort(segmentName=args.name, portName=args.portname,
                           portPath=args.portpath, glob=args.glob)
        
        elif argsNs['segment'] == 'port':
            if argsNs['port'] == 'config':
                obj.config(name=args.portname,
                           vif=args.vif,
                           tagspec=args.tags)


    elif args.ns == 'cert':
        if argsNs['cert'] == 'import':
            obj.importCertificate(name=args.name,
                                  service=args.service,
                                  cert=args.certificate,
                                  key=args.key,
                                  passphrase=args.passphrase,
                                  description=args.desc)
        elif argsNs['cert'] == 'applyHttp':
            obj.applyHttpCert(name=args.name)
        elif argsNs['cert'] == 'listMp':
            obj.list(api='/api/v1/trust-management/certificates',display=True)
        elif argsNs['cert'] == 'findMp':
            obj.findByName(api='/api/v1/trust-management/certificates',
                           name=args.name, display=True)
        elif argsNs['cert'] == 'applyAph':
            obj.setAphCert(node=args.node, cert=args.certificate)
        '''
        '''

    elif args.ns == 'tz':
        if argsNs['tz'] == 'config':
            obj.config(name=args.name,
                       desc=args.desc,
                       teaming=args.teaming,
                       hswname=args.hswname,
                       isdefault=args.isdefault,
                       transportType=args.type)
        elif argsNs['tz'] == 'nested':
            obj.setNested(name=args.name,
                          enable=args.enable,
                          disable=args.disable)
            

        '''
        '''

    elif args.ns == 'ippool':
        if argsNs['ippool'] == 'subnets':
            obj.getSubnets(name=args.name)
        elif argsNs['ippool'] == 'config':
            if argsNs['ippoolcfgns'] == 'range':
                obj.config(addrType='range',
                           name=args.name,
                           ranges=args.ranges,
                           rangeName=args.rangeName,
                           cidr=args.cidr,
                           dns=args.dns,
                           domain=args.domain,
                           gateway=args.gateway)
            else:
                obj.config(addrType=None,name=args.name)

        '''
        '''


    elif args.ns == 'realizealarms':
        if argsNs['realizealarms'] == 'cleanup':
            obj.cleanup(path=args.path)
        elif argsNs['realizealarms'] == 'system':
            obj.systemList()
            
        '''
        '''

    elif args.ns == 'trust':
        if argsNs['trust'] == 'create':
            if not args.nodeid:
                args.nodeid=args.name
                
            obj.create(name=args.name, nodeid=args.nodeid,
                       role=args.role, cert=args.cert,
                       desc=args.desc, isprotected=args.protected)

        elif argsNs['trust'] == 'delete':
            obj.deletePi(name=args.name, display=True)

    elif args.ns == 'vidm':
        if argsNs['vidm'] == 'config':
            obj.config(vidmhost=args.vidmhost, client=args.client,
                       secret=args.secret, nodename=args.host,
                       enable=args.enable, lb=args.lb)
        elif argsNs['vidm'] == 'status':
            obj.getStatus()
        elif argsNs['vidm'] == 'state':
            if obj.getState():
                print("Online")
            else:
                print("Not Online")
    elif args.ns == 'domain':
        if argsNs['domain'] == 'config':
            obj.config(name=args.name, desc=args.desc)
    elif args.ns == 'group':
        if argsNs['group'] == 'config':
            obj.config(name=args.name,
                       domain=args.domain,
                       expressions=args.expressions,
                       vms=args.vm,
                       ipaddrs=args.ip,
                       macaddrs=args.mac,
                       ports=args.ports,
                       segments=args.segments,
                       vifs=args.vif,
                       groups=args.nsgroups,
                       tags=args.tags)
        elif argsNs['group'] == 'members':
            obj.getVmMembers(name=args.name)
        elif argsNs['group'] == 'ipaddrs':
            obj.getIpMembers(name=args.name)
        elif argsNs['group'] == 'consolidatedMembers':
            obj.getConsolidatedEffectiveMembers(name=args.name,
                                                site=args.site,
                                                siteid=args.siteid)
    elif args.ns == 'policy':
        if argsNs['policy'] == 'config':
            obj.config(name=args.name,
                       domain=args.domain,
                       category=args.category,
                       stateless=args.stateless,
                       tcpstrict=args.tcpstrict,
                       sequence=args.sequence,
                       scope=args.scope,
                       connectivity=args.connectivity,
                       desc=args.desc)
        elif argsNs['policy'] == 'position':
            obj.position(name=args.name, domain=args.domain,
                         anchor=args.anchor,
                         anchordomain=args.anchordomain,
                         operation=args.operation)
        elif argsNs['policy'] == 'stats':
            obj.getStats(name=args.name, rule=args.rule)
        elif argsNs['policy'] == 'delete':
            obj.delete(name=args.name)
            
    elif args.ns == 'rule':
        if argsNs['rule'] == 'config':
            obj.config(name=args.name, action=args.action,
                       src=args.src, dst=args.dst,
                       srcNegate=args.invertSrc,
                       dstNegate=args.invertDst,
                       direction=args.direction,
                       disabled=args.disabled,
                       proto=args.protocol,
                       log=args.log,
                       sequence=args.sequence,
                       services=args.services,
                       scope=args.applyto)
        
        elif argsNs['rule'] == 'position':
            obj.position(name=args.name,
                         operation=args.operation,
                         anchor=args.anchor)
        elif argsNs['rule'] == 'delete':
            obj.delete(name=args.name)
    elif args.ns == 'vm':
        if argsNs['vm'] == 'tagvm':
            obj.tag(vmname=args.vmname, tags=args.tags, replace=args.replace)
    elif args.ns == 'lb':
        if argsNs['lb'] == 'config':
            obj.config(name=args.name, size=args.size, tier1=args.tier1,
                       loglevel=args.loglevel, disable=args.disable)
        elif argsNs['lb'] == 'monitoring':
            if argsNs['lbmonitoring'] == 'status':
                obj.status(name=args.name, opType='status', source=args.source)
            if argsNs['lbmonitoring'] == 'usage':
                obj.status(name=args.name, opType='usage', source=args.source)
            if argsNs['lbmonitoring'] == 'stats':
                obj.status(name=args.name, opType='stats', source=args.source)
            elif argsNs['lbmonitoring'] == 'poolstatus':
                obj.getPoolStatus(name=args.name, pool=args.pool,
                                  opType='status', source=args.source)
            elif argsNs['lbmonitoring'] == 'poolstats':
                obj.getPoolStatus(name=args.name, pool=args.pool,
                                  opType='stats', source=args.source)
            elif argsNs['lbmonitoring'] == 'vipstatus':
                obj.getVipStatus(name=args.name, vip=args.vip,
                                  opType='status', source=args.source)
            elif argsNs['lbmonitoring'] == 'vipstats':
                obj.getVipStatus(name=args.name, vip=args.vip,
                                  opType='stats', source=args.source)
        elif argsNs['lb'] == 'appProfile':
            if argsNs['appProfile'] == 'config':
                obj.config(name=args.name, desc=args.desc,
                           appType=args.type,
                           idleTimeout=args.idleTimeout,
                           mirror=args.mirror,
                           closeTimeout=args.closeTimeout,
                           httpRedirectUrl=args.redirectUrl,
                           httpToHttps=args.httpsRedirect,
                           ntlm=args.ntlm,
                           request_body_size=args.request_body_size,
                           request_header_size=args.request_header_size,
                           response_timeout=args.response_timeout,
                           x_forwarded_for=args.x_forwarded_for)
        elif argsNs['lb'] == 'serverSslProfile':
            if argsNs['serverSslProfile'] == 'config':
                obj.config(name=args.name, ciphers=args.ciphers,
                           cipher_group=args.cipher_group,
                           protocols=args.protocols,
                           session_cache_enabled=args.cache)
        elif argsNs['lb'] == 'clientSslProfile':
            if argsNs['clientSslProfile'] == 'config':
                obj.config(name=args.name, ciphers=args.ciphers,
                           cipher_group=args.cipher_group,
                           protocols=args.protocols,
                           session_cache_enabled=args.cache,
                           prefer_server_ciphers=args.prefer_server_ciphers,
                           session_cache_timeout=args.cache_timeout)
                
        elif argsNs['lb'] == 'monitor':
            if argsNs['monitor'] == 'configActive':
                obj.configActive(name=args.name, desc=args.desc,
                                 fallCount=args.fallCount,
                                 riseCount=args.riseCount,
                                 interval=args.interval,
                                 timeout=args.timeout,
                                 port=args.port)
            elif argsNs['monitor'] == 'configPassive':
                obj.configPassive(name=args.name, desc=args.desc,
                                 maxFails=args.maxfail,
                                 fallCount=args.fallCount,
                                 riseCount=args.riseCount,
                                 interval=args.interval,
                                 timeout=args.timeout,
                                 port=args.port)
            elif argsNs['monitor'] == 'configICMP':
                obj.configIcmp(name=args.name, desc=args.desc,
                                 datalen=args.datalen,
                                 fallCount=args.fallCount,
                                 riseCount=args.riseCount,
                                 interval=args.interval,
                                 timeout=args.timeout,
                                 port=args.port)
            elif argsNs['monitor'] == 'configUdp':
                obj.configUdp(name=args.name, desc=args.desc,
                                 send=args.send,
                                 receive=args.receive,
                                 fallCount=args.fallCount,
                                 riseCount=args.riseCount,
                                 interval=args.interval,
                                 timeout=args.timeout,
                                 port=args.port)
            elif argsNs['monitor'] == 'configTcp':
                obj.configTcp(name=args.name, desc=args.desc,
                                 send=args.send,
                                 receive=args.receive,
                                 fallCount=args.fallCount,
                                 riseCount=args.riseCount,
                                 interval=args.interval,
                                 timeout=args.timeout,
                                 port=args.port)
            elif argsNs['monitor'] == 'configHttp':
                obj.configHttp(name=args.name, desc=args.desc,
                                 httpType=args.type,
                                 fallCount=args.fallCount,
                                 riseCount=args.riseCount,
                                 interval=args.interval,
                                 timeout=args.timeout,
                                 port=args.port,
                                 request_body=args.request_body,
                                 request_headers=args.request_headers,
                                 request_method=args.request_method,
                                 request_url=args.request_url,
                                 request_version=args.request_version,
                                 response_body=args.response_body,
                                 response_code=args.response_codes)
            elif argsNs['monitor'] == 'serverSslBinding':
                obj.configHttpsSslBinding(name=args.name,
                                          certDepth=args.certDepth,
                                          clientCert=args.clientCert,
                                          serverAuth=args.serverAuth,
                                          serverCA=args.serverCA,
                                          serverCRL=args.serverCRL,
                                          sslProfile=args.sslProfile)
    
        elif argsNs['lb'] == 'persistence':
            if argsNs['persistence'] == 'configSourcePersistence':
                obj.configSourcePersistence(name=args.name,
                                            desc=args.desc,
                                            shared=args.shared,
                                            purge=args.purge,
                                            timeout=args.timeout,
                                            sync=args.sync)
            if argsNs['persistence'] == 'configCookiePersistence':
                obj.configCookiePersistence(name=args.name,
                                            desc=args.desc,
                                            shared=args.shared,
                                            cookie_mode=args.mode,
                                            cookie_name=args.cookie_name,
                                            cookie_domain=args.cookie_domain,
                                            disable_fallback=args.disable_fallback,
                                            disable_garble=args.disable_garble,
                                            cookie_path=args.cookie_path,
                                            max_idle=args.max_idle,
                                            max_life=args.max_life)
        elif argsNs['lb'] == 'pool':
            if argsNs['pool'] == 'config':
                obj.config(name=args.name, desc=args.desc, update=args.update,
                           algorithm=args.algorithm,
                           member_group=args.member_group,
                           mg_ip_version=args.mg_ip_version,
                           mg_max_ip=args.mg_max_ip,
                           mg_adminDown_ips=args.mg_adminDown_ips,
                           mg_port=args.mg_port,
                           members=args.members,
                           active_monitor=args.active_monitor,
                           passive_monitor=args.passive_monitor,
                           snat_translation=args.snat_translation,
                           snat_pool=args.snat_pool,
                           tcp_multiplex_enabled=args.tcp_multiplex_enabled,
                           tcp_multiplex_number=args.tcp_multiplex_number)
        elif argsNs['lb'] == 'vip':
            if argsNs['vip'] == 'config':
                obj.config(name=args.name, desc=args.desc, update=args.update,
                           ip_address=args.ip, ports=args.ports,
                           application_profile=args.appProfile,
                           access_log_enabled=args.enable_access_log,
                           default_pool_member_ports=args.default_pool_member_ports,
                           disabled=args.disabled,
                           lb_persistence_profile=args.persistProfile,
                           lb_service=args.lb_service,
                           max_concurrent_connections=args.max_concurrent_connections,
                           max_new_connection_rate=args.max_new_connection_rate,
                           pool=args.pool,
                           sorry_pool=args.sorry_pool)
            if argsNs['vip'] == 'clientSslBinding':
                obj.configClientSslBinding(name=args.name, cert=args.cert,
                                           sslProfile=args.sslProfile,
                                           certDepth=args.certDepth,
                                           clientAuth=args.clientAuth,
                                           clientCA=args.clientCA,
                                           clientCRL=args.clientCRL,
                                           sniCerts=args.sniCerts)
            if argsNs['vip'] == 'serverSslBinding':
                obj.configServerSslBinding(name=args.name,
                                           certDepth=args.certDepth,
                                           clientCert=args.clientCert,
                                           serverCA=args.clientCA,
                                           serverCRL=args.serverCRL,
                                           sslProfile=args.sslProfile)
    elif args.ns == 'dhcprelay':
        if argsNs['dhcprelay'] == 'config':
            obj.config(name=args.name, servers=args.servers)
    elif args.ns == 'tn':
        if argsNs['tn'] == 'state':
            obj.getState(name=args.name, tnid=args.id, ip=args.ip)
        elif argsNs['tn'] == 'status':
            obj.getStatus(name=args.name, tnid=args.id, ip=args.ip)
        elif argsNs['tn'] == 'pnicStatus':
            obj.getBondStatus(name=args.name, tnid=args.id, ip=args.ip)
        elif argsNs['tn'] == 'teps':
            obj.getTeps(name=args.name, tnid=args.id, ip=args.ip)
        elif argsNs['tn'] == 'tunnels':
            obj.getTunnels(name=args.name, tnid=args.id, ip=args.ip)
        elif argsNs['tn'] == 'remoteNodesStatus':
            obj.getRemoteNodeStatus(name=args.name, tnid=args.id, ip=args.ip)
        elif argsNs['tn'] == 'resync':
            obj.reSync(name=args.name, tnid=args.id, ip=args.ip)
        elif argsNs['tn'] == 'capabilities':
            obj.getCapabilities(name=args.name, tnid=args.id, ip=args.ip)
        elif argsNs['tn'] == 'interfaces':
            obj.getInterfaces(name=args.name, tnid=args.id, ip=args.ip)
        elif argsNs['tn'] == 'interfaceStat':
            obj.getInterfaceStat(name=args.name, tnid=args.id, ip=args.ip,
                                 interface=args.interface, source=args.realtime)
        elif argsNs['tn'] == 'lldpNeighbors':
            obj.getLldpNeighbors(name=args.name, tnid=args.id, ip=args.ip,
                                 interface=args.interface)
        elif argsNs['tn'] == 'addtz':
            obj.addTz(tnname=args.node, tzname=args.tz,
                      swname=args.swname, display=True)
        elif argsNs['tn'] == 'config':
            obj.config(nodename=args.node, nics=args.nics, uplink=args.uplinkprofile,
                       lldp=args.lldpprofile, ippool=args.ippool, swname=args.hswname,
                       tzname=args.tzname)
        elif argsNs['tn'] == 'update':
            obj.update(nodename=args.node, nics=args.nics, swname=args.hswname,
                       uplink=args.uplinkprofile, lldp=args.lldpprofile,
                       ippool=args.ippool, vmklist=args.vmklist,
                       targets=args.targets)
        elif argsNs['tn'] == 'rtep':
            obj.addRtep(nodename=args.node, ippool=args.ippool,
                        vlan=args.vlan, hsw=args.hsw)
        elif argsNs['tn'] == 'setfd':
            obj.setFailureDomain(nodename=args.node, domain=args.domain)
        elif argsNs['tn'] == 'passwd':
            obj.setPassword(username=args.username, oldpassword=args.oldpasswd,
                            newpassword=args.newpasswd, node=args.node)

    elif args.ns == 'uplink':
        if argsNs['uplink'] == 'configUplinkProfile':
            obj.configUplinkHostSwitchProfile(name=args.name,
                                              uplinktype=args.type,
                                              active=args.active,
                                              policy=args.policy,
                                              standby=args.standby,
                                              vlan=args.vlan,
                                              mtu=args.mtu,
                                              named=args.named,
                                              lagmode=args.lagmode,
                                              laglb=args.laglb,
                                              laglinks=args.laglinks,
                                              lagtimeout=args.lagtimeout,
                                              desc=args.desc)
        elif argsNs['uplink'] == 'configLldpProfile':
            obj.configLldpProfile(name=args.name, lldp=args.send)
    elif args.ns == 'computeManager':
        if argsNs['computeManager'] == 'config':
            obj.register(svrName=args.name, server=args.server,
                         username=args.username, password=args.passwd,
                         thumbprint=args.thumbprint, trust=args.trust)
        elif argsNs['computeManager'] == 'listCluster':
            obj.listClusters(vc=args.vc)
        elif argsNs['computeManager'] == 'findCluster':
            obj.findCluster(cluster=args.name, vc=args.vc)
        elif argsNs['computeManager'] == 'listStorage':
            obj.listStorage(cluster=args.cluster, vc=args.vc)
        elif argsNs['computeManager'] == 'findStorage':
            obj.findStorage(cluster=args.cluster, name=args.name, vc=args.vc)
        elif argsNs['computeManager'] == 'listNetworks':
            obj.listNetworks(cluster=args.cluster, vc=args.vc, storage=args.storage)
        elif argsNs['computeManager'] == 'findNetwork':
            obj.findNetwork(cluster=args.cluster, name=args.name, vc=args.vc,
                            storage=args.storage)
                
                    
    elif args.ns == 'vidm':
        if argsNs['vidm'] == 'status':
            obj.getStatus()
        elif argsNs['vidm'] == 'config':
            obj.config(vidmhost=args.vidm.host, client=args.client,
                       secret=args.secret, nodename=args.host,
                       enable=args.enable, lb=args.lb)
    elif args.ns == 'role':
        if argsNs['role'] == 'bind':
            obj.bind(name=args.name, roles=args.roles, utype=args.type)
        elif argsNs['role'] == 'listBindings':
            obj.list(api='/policy/api/v1/aaa/role-bindings', display=True)
    elif args.ns == 'license':
        if argsNs['license'] == 'config':
            obj.config(license=args.key)
    elif args.ns == 'faultdomain':
        if argsNs['faultdomain'] == 'config':
            obj.config(name=args.name, setPrefer=args.setPrefer,
                       setNotPrefer=args.setNotPrefer, desc=args.desc)
    elif args.ns == 'federation':
        if argsNs['federation'] == 'makeActive':
            obj.makeActive(name=args.name)

    elif args.ns == 'backup':
        if argsNs['backup'] == 'config':
            obj.config(remote_server=args.sftpServer,
                       remote_user=args.sftpUser,
                       remote_password=args.sftpPassword,
                       remote_dir=args.sftpDir,
                       remote_port=args.sftpPort,
                       remote_fingerprint=args.sftpFingerprint,
                       passphrase=args.backupPassphrase,
                       inventory=args.inventory_interval,
                       backup_after_topo=args.topoChange_auto,
                       auto_weekly=args.auto_daily,
                       auto_days = args.daily_days,
                       auto_hour=args.daily_hour,
                       auto_min=args.daily_min,
                       auto_daily=args.auto_periodic,
                       auto_backup_interval=args.periodic_interval)
        elif argsNs['backup'] == 'history':
            obj.history()
        elif argsNs['backup'] == 'timestamps':
            obj.timeStamps()

    elif args.ns == 'service':
        if argsNs['service'] == 'config':
            obj.configL4PortService(name=args.name, desc=args.desc,
                                    entries=args.entries)
    elif args.ns == 'syslog':
        if argsNs['syslog'] == 'config':
            obj.setExporter(name=args.name,
                            level=args.level,
                            port=args.port,
                            protocol=args.protocol,
                            server=args.server,
                            facilities=args.facilities,
                            structured_data=args.structured_data,
                            msgids=args.msgids,
                            server_ca=args.serverCA,
                            client_cert=args.cert,
                            client_ca=args.clientCA,
                            client_key=args.key)
        elif argsNs['syslog'] == 'remove':
            obj.removeAllExporters()
        elif argsNs['syslog'] == 'verify':
            obj.verify()
        elif argsNs['syslog'] == 'status':
            obj.status()
        elif argsNs['syslog'] == 'serviceCtl':
            obj.serviceCtl(action=args.action)
        
            
    
            
if __name__=="__main__":
    main()
