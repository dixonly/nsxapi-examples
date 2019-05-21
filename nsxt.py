#!/usr/bin/env python

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

    #subparsers is the NameSpace for all first level commands
    subparsers = parser.add_subparsers(dest='ns')
    
    #Parser for remote session creation
    sessionParser = subparsers.add_parser('session')
    sessionNs = sessionParser.add_subparsers(dest='session')
    session = sessionNs.add_parser('create')
    session.add_argument('--filename', required=True,
                         help='Filename to store the session cookie')
    
    clusterSpace = subparsers.add_parser('cluster')
    clusterNs = clusterSpace.add_subparsers(dest='cluster')
    cluster_parser = clusterNs.add_parser('info')
    cluster_parser = clusterNs.add_parser('nodes')
    cluster_parser = clusterNs.add_parser('status')
    cluster_parser = clusterNs.add_parser('health')
    cluster_parser = clusterNs.add_parser('join')
    cluster_parser.add_argument('--primary', required=True,
                                help='IP/hostname of current cluster member')
    cluster_parser.add_argument('--secondaries', required=True, nargs='+',
                                help='IP/hostname of one more secondary node')
    cluster_parser = clusterNs.add_parser('vip')
    cluster_vipns = cluster_parser.add_subparsers(dest='clustervip')
    cluster_vipns_parser = cluster_vipns.add_parser('get')
    cluster_vipns_parser = cluster_vipns.add_parser('clear')
    cluster_vipns_parser = cluster_vipns.add_parser('set')
    cluster_vipns_parser.add_argument('--ip', required=True)

    cluster_parser = clusterNs.add_parser('cert')
    cluster_certns = cluster_parser.add_subparsers(dest='clustercert')
    cluster_certns_parser = cluster_certns.add_parser('get')
    cluster_certns_parser = cluster_certns.add_parser('set')
    cluster_certns_parser.add_argument('--name', required=True,
                                       help="Name of certificate")
    cluster_certns_parser = cluster_certns.add_parser('clear')
    cluster_certns_parser.add_argument('--name', required=True,
                                            help="Name of certificate")

    globalSpace = subparsers.add_parser('global')
    globalNs = globalSpace.add_subparsers(dest='global')
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
    

    tnprofileSpace = subparsers.add_parser('tnprofile')
    tnprofileNs = tnprofileSpace.add_subparsers(dest='tnprofile')
    createCommonParsers(parser=tnprofileNs,
                        names=['list', 'find'])
    tnp_parser = tnprofileNs.add_parser('delete')
    tnp_parser.add_argument('--name', required=True,
                            help="Name of the TransportNode Profile")
    tnp_parser = tnprofileNs.add_parser('update')
    tnp_parser.add_argument('--name', required=True,
                            help="Name of the TransportNode Profile")
    tnp_parser.add_argument('--desc', required=False, default=None,
                            help="Description of the TransportNode Profile")

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
    '''
    '''
    siteSpace = subparsers.add_parser('site')
    siteNs = siteSpace.add_subparsers(dest='site')
    createCommonParsers(parser=siteNs,
                        names=['list', 'find', 'path'])
    '''
    '''
    enforceSpace = subparsers.add_parser('enforce')
    enforceNs = enforceSpace.add_subparsers(dest='enforce')
    createCommonParsers(parser=enforceNs,
                        names=['list', 'find', 'path'])
    '''
    '''
    tzSpace = subparsers.add_parser('tz')
    tzNs = tzSpace.add_subparsers(dest='tz')
    createCommonParsers(parser=enforceNs,
                        names=['list', 'find', 'path'])
    '''
    '''
    ippoolSpace = subparsers.add_parser('ippool')
    ippoolNs = ippoolSpace.add_subparsers(dest='ippool')
    createCommonParsers(parser=ippoolNs,
                        names=['list', 'find', 'path', 'realization'])
    '''
    '''
    realizeSpace = subparsers.add_parser('realizealarms')
    realizeNs = realizeSpace.add_subparsers(dest='realizealarms')
    createCommonParsers(parser=realizeNs,
                        names=['list'])
    alarm_parser = realizeNs.add_parser('cleanup')
    alarm_parser.add_argument('--path', required=True,
                              help="Actual path of alarm, see policy logs, or combined alarm's source_reference with relative_path")
    alarm_parser = realizeNs.add_parser('system')
    '''
    '''
    segmentSpace = subparsers.add_parser('segment')
    segmentNs = segmentSpace.add_subparsers(dest='segment')
    createCommonParsers(parser=segmentNs,
                        names=['list', 'find', 'path', 'realization', "delete"])
    seg_parser = segmentNs.add_parser('config')
    seg_parser.add_argument('--name', required=True)
    seg_parser.add_argument('--tz', required=True,help="Name of TZ")
    seg_parser.add_argument('--lr', required=False, default=None,
                            help="Logical router to connect to, default none")
    seg_parser.add_argument('--gw', required=False, default=None, 
                            help='CIDR of gateway, means LR interface IP')
    seg_parser.add_argument('--dhcp', required=False, default=None, 
                            help="DHCP range")
    seg_parser.add_argument('--vlans', required=False, default=None, nargs='*', help="List of vlans")
    seg_parser.add_argument('--desc', required=False)

    pfxSpace = subparsers.add_parser('prefixlist')
    pfxNs = pfxSpace.add_subparsers(dest='prefixlist')
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
                            help="List of prefixes, format: CIDR:GE:LE:ACTION, \
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
    rmapNs = rmapSpace.add_subparsers(dest='routemap')
    createCommonParsers(parser=rmapNs,
                        names=['list', 'find', 'path', 'realization', "delete"],
                        arguments=['t0'])
    
    t0Space = subparsers.add_parser('tier0')
    t0Ns = t0Space.add_subparsers(dest='tier0')
    createCommonParsers(parser=t0Ns,
                        names=['list', 'find', 'path', 'realization', "delete"])
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
    t0_intNs = t0_parser.add_subparsers(dest='t0intNs')
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

    t0_int = t0_intNs.add_parser('delete')
    t0_int.add_argument('--name', required=True)
    t0_int.add_argument('--int', required=True)
    t0_int.add_argument('--locale', default='default')
    t0_int = t0_intNs.add_parser('status')
    t0_int.add_argument('--name', required=True)
    t0_int.add_argument('--int', required=True)
    t0_int.add_argument('--locale', default='default')
    t0_int = t0_intNs.add_parser('entities')
    t0_int.add_argument('--locale', default='default')
    t0_int.add_argument('--name', required=True)
    t0_int.add_argument('--int', required=True)

    t0_parser = t0Ns.add_parser('locale')
    t0_localeNs = t0_parser.add_subparsers(dest='t0localens')
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
    t0_bgpNs = t0_parser.add_subparsers(dest='bgpns')
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
    
    t0_bgp = t0_bgpNs.add_parser('neighbor')
    t0_bgpNeighborNs = t0_bgp.add_subparsers(dest='bgpNeighborNs')
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
    t0_neighbor.add_argument('--remoteAs', required=True,
                             help="Neighbor AS number")
    t0_neighbor.add_argument('--holdtime', required=False,
                             default=None,
                             help="BGP hold down time, default 180s")
    t0_neighbor.add_argument('--keepalive', required=False,
                             default=None,
                             help="BGP keepalive timer, default 60s")
    t0_neighbor.add_argument('--password', required=False,
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
    
    t0_neighbor.add_argument('--desc', required=False,
                             default=None,
                             help="Neighbor description")
    t0_neighbor = t0_bgpNeighborNs.add_parser('delete')                            
    t0_neighbor.add_argument('--name', required=True,
                             help="name of Tier0 router")
    t0_neighbor.add_argument('--locale', default='default',
                             help="Tier0 locale, default is 'default'")
    
    t0_neighbor.add_argument('--peer', required=True,
                             help="Peer name")

    t1Space = subparsers.add_parser('tier1')
    t1Ns = t1Space.add_subparsers(dest='tier1')
    createCommonParsers(parser=t1Ns,
                        names=['list', 'find', 'path', 'realization', "delete"])
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
    

    domainSpace = subparsers.add_parser('domain')
    domainNs = domainSpace.add_subparsers(dest='domain')
    createCommonParsers(parser=domainNs,
                        names=['list', 'find'])
    domain = domainNs.add_parser('config')
    domain.add_argument('--name', required=True,
                        help="Name - will also be used for ID")
    domain.add_argument('--desc', default=None,
                        help="Description")
    groupSpace = subparsers.add_parser('group')
    groupNs = groupSpace.add_subparsers(dest='group')
    createCommonParsers(parser=groupNs,
                        names=['list', 'find', 'realization', 'path', "delete"],
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
                       
    serviceSpace = subparsers.add_parser('service')
    serviceNs = serviceSpace.add_subparsers(dest='service')
    createCommonParsers(parser=serviceNs,
                        names=['list', 'find', 'realization', 'path', "delete"])

    policySpace = subparsers.add_parser('policy')
    policySpace.add_argument('--domain', default='default',
                             help="Domain for this policy, default is 'default'")
    policyNs = policySpace.add_subparsers(dest='policy')
    createCommonParsers(parser=policyNs,
                        names=['list', 'find', 'realization', 'path', "delete"])
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
    ruleNs = ruleSpace.add_subparsers(dest='rule')
    createCommonParsers(parser=ruleNs,
                        names=["list", "find", "realization", "path", "delete"])
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
    vmNs = vmSpace.add_subparsers(dest='vm')
    createCommonParsers(parser=vmNs,
                        names=["list", "find"])
    vm = vmNs.add_parser('tag')
    vm.add_argument('--vmname', required=True)
    vm.add_argument('--tags', required=True,
                    nargs='*',
                    help="Tags in format of <scope:><tag>, use quoted empty to clear all tags")

    certSpace=subparsers.add_parser('cert')
    certNs = certSpace.add_subparsers(dest='cert')
    createCommonParsers(parser=certNs,
                        names=["list", "find", "realization", "path", "delete"])
    cert = certNs.add_parser('import')
    cert.add_argument('--name', required=True)
    cert.add_argument('--certificate', required=True,
                      help="Certificate PEM file")
    cert.add_argument('--key', required=False,
                      help="Certificate key PEM file")
    cert.add_argument('--passphrase', required=False, default=None,
                      help="Pass phrase")
    cert.add_argument('--desc', required=False, default=None,
                      help="Description for cert")
                      
                      
                      
                      
    
    lbSpace = subparsers.add_parser('lb')
    lbNs = lbSpace.add_subparsers(dest='lb')
    createCommonParsers(parser=lbNs,
                        names=["list", "find", "realization", "path", "delete"])
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

    lbmonitorNs=lbmonitorSpace.add_subparsers(dest='lbmonitoring')
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
    appProfileNs = appProfileSpace.add_subparsers(dest='appProfile')
    createCommonParsers(parser=appProfileNs,
                        names=["list", "find", "realization", "path", "delete"])
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
    monitorNs = monitorSpace.add_subparsers(dest='monitor')
    createCommonParsers(parser=monitorNs,
                        names=["list", "find", "realization", "path", "delete"])
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
    serverSslNs = serverSslSpace.add_subparsers(dest='serverSslProfile')
    createCommonParsers(parser=serverSslNs,
                        names=["list", "find", "realization", "path", "delete"])
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
    clientSslNs = clientSslSpace.add_subparsers(dest='clientSslProfile')
    createCommonParsers(parser=clientSslNs,
                        names=["list", "find", "realization", "path", "delete"])

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
    persistNs = persistSpace.add_subparsers(dest='persistence')
    createCommonParsers(parser=persistNs,
                        names=["list", "find", "realization", "path", "delete"])
                           
    persist = persistNs.add_parser('configSourcePersistence')
    persist.add_argument('--name', required=True)
    persist.add_argument('--desc', required=False)
    persist.add_argument('--shared', required=False, default=None,
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
    persist.add_argument('--shared', required=False, default=None,
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
    poolNs = poolSpace.add_subparsers(dest='pool')
    createCommonParsers(parser=poolNs,
                        names=["list", "find", "realization", "path", "delete"])
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
    vipNs = vipSpace.add_subparsers(dest='vip')
    createCommonParsers(parser=vipNs,
                        names=["list", "find", "realization", "path", "delete"])
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
        rns = r.add_subparsers(dest="realizationns")
        if arguments:
            for i in arguments:
                arg='--'+i
                r.add_argument(arg)

        p = rns.add_parser('entities')
        p.add_argument('--name', required=True)

        p = rns.add_parser('status')
        p.add_argument('--name', required=True)


def commonHandlers(obj, argsNs, subNs, args):
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
        obj.delete(name=args.name)
    elif subNs == 'realization':
        if args.realizationns == 'entities':
            obj.getRealizationEntities(name=args.name,display=True)
        elif args.realizationns == 'status':
            obj.getRealizationStatus(name=args.name,display=True)
    elif subNs == 'vm':
        pass
            

def createNsxObject(objName, mp, args):
    '''
    For every object that inherits from Policy_object to be used from nsxplib, create it here
    '''

    if objName=='cluster':
        return nsxobjects.Cluster(mp=mp)
    elif objName=='global':
        return nsxobjects.GlobalConfigs(mp=mp)
    elif objName=='tnprofile':
        return nsxobjects.TNProfile(mp=mp)
    elif objName=='site':
        return nsxobjects.Sites(mp=mp)
    elif objName=='enforce':
        return nsxobjects.EnforcementPoints(mp=mp)
    elif objName=='tz':
        return nsxobjects.TransportZone(mp=mp)
    elif objName=='segment':
        return nsxobjects.Segments(mp=mp)
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
        return nsxobjects.Group(mp=mp, domain=args.domain)
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

    '''
    elif objectName=='':
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
                              timeout=args.sessiontimeout)

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
            
    if not obj:
        print("Object name %s not handled by createNsxObject()" %args.ns)
        return

    if args.ns=='lb' and argsNs['lb'] not in ['list', 'find', 'monitoring',
                                              'realization', 'delete',
                                              'path', 'config']:
        commonHandlers(obj=obj, argsNs=args.ns, subNs=argsNs[argsNs['lb']], args=args)
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
        elif argsNs['cluster'] == 'join':
            primary=nsxplib.PolicyNode(host=args.primary, rootpassword=args.npass,
                                adminpassword=args.npass,
                                loglevel=args.loglevel)
            secondaries=[]
            for s in args.secondaries:
                smp=nsxplib.PolicyNode(host=s, adminpassword=args.npass,loglevel=args.loglevel)
                secondaries.append(smp)
            obj.createCluster(primary=primary,secondaries=secondaries)

        elif argsNs['cluster'] == 'vip':
            if argsNs['clustervip'] == 'get':
                obj.getClusterIp()
            elif argsNs['clustervip'] == 'clear':
                obj.clearClusterIp()
            elif argsNs['clustervip'] == 'set':
                obj.setClusterIp(addr=args.ip)
        elif argsNs['cluster'] == 'cert':
            if argsNs['clustercert'] == 'get':
                obj.getCertificate()
            elif argsNs['clustercert'] == 'clear':
                obj.clearCertificate(certName=args.name)
            elif argsNs['clustercert'] == 'set':
                obj.setCertificate(certName=args.name)
                
    elif args.ns == 'global':
        if argsNs['global'] == 'switch':
            obj.updateSwitchingConfig(name=args.name, desc=args.desc,
                                    mtu=args.mtu,
                                    replication=args.replication)
        elif argsNs['global'] == 'routing':
            obj.updateRoutingConfig(name=args.name, desc=args.desc,
                                    mtu=args.mtu,
                                    l3mode=args.l3mode)
    elif args.ns == 'tnprofile':
        if argsNs['tnprofile'] == 'config':
            obj.config(name = args.name,
                       uplinkprofile=args.uplinkprofile,
                       pnics=args.pnics,
                       uplinknames=args.uplinknames,
                       hswname=args.hswname,
                       tz=args.tz,
                       lldp=args.lldp,
                       vmks=args.vmks,
                       vmknets=args.vmknets,
                       vmkuninstall=args.vmkuninstall,
                       vmkuninstnets=args.vmkuninstnets,
                       pnicuninstalls=args.pnicuninstalls,
                       ippool=args.ippool,
                       desc=args.desc)
    elif args.ns == 'tncollection':
        if argsNs['tncollection'] == 'config':
            obj.config(computecollection=args.computecollection,
                        tnprofile=args.tnprofile,
                        name=args.name,
                        desc=args.desc)    
        
        '''
        '''
    elif args.ns == 'tier0':
        if argsNs['tier0'] == 'config':
            obj.config(name=args.name, failover=args.failover,
                       ha=args.ha, transit=args.transit,
                       dhcprelay=args.dhcprelay, desc=args.desc)
            
        elif argsNs['tier0'] == 'interface':
            if argsNs['t0intNs'] == 'get':
                obj.getInterfaces(name=args.name, locale=args.locale,
                                  interface=args.int, display=True)
            elif argsNs['t0intNs'] == 'config':
                obj.createInterface(name=args.name, interface=args.int,
                                    segment=args.segment, cidr=args.cidr,
                                    mtu=args.mtu, intType=args.type,
                                    edge=args.edge, desc=args.desc,
                                    locale=args.locale)
            elif argsNs['t0intNs'] == 'delete':
                obj.deleteInterface(name=args.name, interface=args.int,
                                    locale=args.locale, display=True)
            elif argsNs['t0intNs'] == 'status':
                i = obj.getInterfaces(name=args.name, interface=args.int,
                                      locale=args.locale, display=False)
                if i:
                    obj.getRealizationStatus(path=i['path'], display=True)
            elif argsNs['t0intNs'] == 'entities':
                i = obj.getInterfaces(name=args.name, interface=args.int,
                                      locale=args.locale, display=False)
                if i:
                    obj.getRealizationEntities(path=i['path'], display=True)
            
        elif argsNs['tier0'] == 'locale':
            if argsNs['t0localens'] == 'get':
                obj.getLocale(name=args.name,display=True)
            elif argsNs['t0localens'] == 'redist':
                obj.setRouteDistribution(name=args.name, locale=args.locale,
                                         redist=args.types)
            elif argsNs['t0localens'] == 'edgecluster':
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
                              display=True)
            elif argsNs['bgpns'] == 'neighbor':
                if argsNs['bgpNeighborNs'] == 'get':
                    obj.getBgpNeighbors(name=args.name, locale=args.locale,display=True)
                elif argsNs['bgpNeighborNs'] == 'config':
                    obj.configBgpNeighbor(name=args.name, neighborAddr = args.address,
                                          remoteAs=args.remoteAs, neighborName = args.peer,
                                          neighborDesc=args.desc, holdtime=args.holdtime,
                                          keepalive=args.keepalive,
                                          password=args.password,
                                          locale=args.locale,
                                          enablebfd=args.enablebfd,
                                          disablebfd=args.disablebfd,
                                          bfdInterval=args.bfdinterval,
                                          bfdMultiple=args.bfdmultiple,
                                          display=True)
                elif argsNs['bgpNeighborNs'] == 'delete':
                    obj.deleteBgpNeighbor(name=args.name, locale=args.locale,
                                          neighborName=args.peer, display=True)
                              
        '''
        '''
    elif args.ns == 'tier1':
        if argsNs['tier1'] == 'config':
            obj.config(name=args.name, preempt=args.preempt, tier0=args.tier0,
                       advertisements=args.advertisements)
        elif argsNs['tier1'] == 'edgecluster':
            obj.setEdgeCluster(name=args.name, clustername=args.cluster,
                               edges=args.preferredEdges,
                               locale=args.locale)
    elif args.ns == 'prefixlist':
        if argsNs['prefixlist'] == 'config':
            obj.config(t0=args.t0,
                       name=args.name,
                       prefix=args.prefix,
                       desc=args.desc, display=True)
        elif argsNs['prefixlist'] == 'delete':
            obj.deletePrefixList(t0=args.t0, name=args.name, display=True)
            
    elif args.ns == 'segment':
        if argsNs['segment'] == 'config':
            obj.config(name=args.name,
                       tz=args.tz,
                       connectPath=args.lr,
                       gw=args.gw,
                       dhcp=args.dhcp,
                       vlans=args.vlans,
                       desc=args.desc)

        '''
        '''

    elif args.ns == 'cert':
        if argsNs['cert'] == 'import':
            obj.importCertificate(name=args.name,
                       cert=args.certificate,
                       key=args.key,
                       passphrase=args.passphrase,
                       description=args.desc)
                       
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
    elif args.ns == 'role':
        if argsNs['role'] == 'bindings':
            if argsNs['bindingsns'] == 'add':
                obj.bind(name=args.name, roles=args.roles,
                         utype=args.type, display=True)

            elif argsNs['bindingsns'] == 'list':
                obj.list(restUrl='/policy/api/v1/aaa/role-bindings',display=True)
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
            
    elif args.ns == 'policy':
        if argsNs['policy'] == 'config':
            obj.config(name=args.name,
                       domain=args.domain,
                       category=args.category,
                       stateless=args.stateless,
                       tcpstrict=args.tcpstrict,
                       sequence=args.sequence,
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
        if argsNs['vm'] == 'tag':
            obj.tag(vmname=args.vmname, tags=args.tags)
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

 
    
if __name__=="__main__":
    main()
