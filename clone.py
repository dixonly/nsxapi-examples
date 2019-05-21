#!/usr/bin/env python
#from __future__ import print_function
from pyVim.connect import SmartConnect,Disconnect
from pyVmomi import vim
import tasks
from parse import parse
from pprint import pprint, pformat
from netaddr import IPNetwork
from itertools import izip
import sys
import re
import atexit
import argparse
import ssl
import requests
import getpass

requests.packages.urllib3.disable_warnings()

#test comment
def parseParameters():

    parser = argparse.ArgumentParser(
            description='Cconnect to vCenter, clone VM from a template snapshot')

    vcGroup = parser.add_argument_group('vCenter/NSX authentication')
    vcGroup.add_argument('-s', '--server',
            required = True,
            action = 'store',
            help = 'Vcenter server name or IP')
    vcGroup.add_argument('-u', '--user',
             required=True,
             action='store',
             help='User name to connect to vcenter')
    vcGroup.add_argument('-p', '--password',
             required=False,
             action='store',
             help = 'Password for connection to vcenter')

    vmGroup = parser.add_argument_group('VM creation Specification')
    vmGroup.add_argument('-d', '--datacenter',
            required = True,
            action = 'store',
            help = 'Datacenter name')
    vmGroup.add_argument('-c', '--cluster',
            required = True,
            action = 'store',
            help = 'Cluster to close to')
    vmGroup.add_argument('-e', '--host',
            required = False,
            action = 'store',
            help = 'Host to deploy the VM, will be spread in all cluster hosts if not specified')
    vmGroup.add_argument('-m', '--datastore',
            required = True,
            action = 'store',
            help = 'Datastore to put the VM')
    vmGroup.add_argument('-v', '--vmfolder',
            required = True,
            action = 'store',
            help = 'Destination folder name to contain the vms')
    vmGroup.add_argument('-t', '--template',
            required = True,
            action = 'store',
            help = 'Name of VM template to clone')
    vmGroup.add_argument('--linked',
            required = False,
            default = False,
            action='store_true',
            help = 'Specify if desiring linked clone')
    vmGroup.add_argument('--snapshot',
            required=False,
            action='store',
            help = 'Snapshot name to use if specifying linked clone')
    vmGroup.add_argument('--poweron',
            '--noarg',
            action='store_true',
            default = False,
            help = 'True/False, power on after clone')
    vmGroup.add_argument('--vm_name')
    vmGroup.add_argument('--vm_domain',     help = 'VM domain name')
    vmGroup.add_argument('--vm_dnsservers', nargs='*', help = 'VM DNS servers')
    vmGroup.add_argument('--vm_dnssubfixes',help = 'VM DNS suffix')
    vmGroup.add_argument('--vm_gw',         help = 'VM default gateway')
    vmGroup.add_argument('--vm_cidr', help="VM's CIDR")

    netGroup = parser.add_argument_group('Network Specification')

    netGroup.add_argument('--network',
            help='Opaque Network to attach all the NICs, will overide --portgroup. '
                 'Overriden if --network specified')

    args = parser.parse_args()



    if not args.network:
        print('OpaqueNetwork name must be provided')
        exit(0)
    if args.linked and not args.snapshot:
        print('Linked mode specified, must provide snapshot')
        exit(0)
    return args

"""
 Get the vsphere object associated with a given text name
"""
def getObjectFromVcenterInventory(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj



def vmCreateWait(si, taskList):
    try:
        tasks.wait_for_tasks(si, taskList)
        taskList = []
    except vim.fault.DuplicateName as e:
        print(e.msg)
    except Exception as e:
        print(e)

def getVcInvObj(inv, vimTypeList, objTypeName, objName):
    obj = getObjectFromVcenterInventory(inv, vimTypeList, objName)
    if not obj:
        print('Could not find %s: %s' % (objTypeName, objName))
        exit(-1)
    return obj

def findOpaqueNetworkByName(inv, opNetName):
    opaqueNet = None
    container = inv.viewManager.CreateContainerView(inv.rootFolder, [vim.OpaqueNetwork], True)
    for i in container.view:
        if i.summary.name in [opNetName, opNetName+'@0']:
            opaqueNet = i
            break
    return opaqueNet

def attachOpaqueNetworkDevBacking(vmName, dev, opaqueNet):
    print('Attaching opaque network "%s" to network adapter' % opaqueNet.name)
    dev.backing = vim.vm.device.VirtualEthernetCard.OpaqueNetworkBackingInfo()
    dev.backing.opaqueNetworkId = opaqueNet.summary.opaqueNetworkId
    dev.backing.opaqueNetworkType = opaqueNet.summary.opaqueNetworkType
    if hasattr(dev, 'externalId') and dev.externalId:
        # initilize dev.externalId empty string to trigger creation of new VIF
        dev.externalId = None # this is the VIF, should be '' for newly cloned VM, so new VIF will be create
def shortMoid(moid):
    ''' INPUT: "vim.vm.Snapshot:snapshot-161"
        RETURN: "snapshot-161"
    '''
    if moid==None: return None
    moid = str(moid)
    l = moid.strip("'").split(':')
    return l[0] if len(l)==1 else l[1]


def walkSnapshotTree(root, depth):
    for child in root.childSnapshotList:
        yield (child, depth)
        if child.childSnapshotList:
            for (child, depth) in walkSnapshotTree(child, depth):
                yield (child, depth+1)

def walkSnapshotForrest(vm):
    if not vm.snapshot or not vm.snapshot.rootSnapshotList:
        return
    curSnapshot = shortMoid(vm.snapshot.currentSnapshot)
    for root in vm.snapshot.rootSnapshotList:
        yield(root)
        for (snap, depth) in walkSnapshotTree(root, 1):
            yield(snap)

def main():
    args = parseParameters()

    password = args.password or \
        getpass.getpass('Enter the password for vCenter %s@%s: ' % (args.user, args.server))

    if hasattr(ssl, 'SSLContext'):
        context=ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode=ssl.CERT_NONE
        si = SmartConnect(host=args.server, user=args.user, pwd=password,sslContext=context)
    else:
        si = SmartConnect(host=args.server, user=args.user, pwd=password)
        
    if not si:
        print("Could not connect to vcenter: %s" %args.server)
        return -1
    else:
        print("Connect to vcenter: %s" %args.server)
    atexit.register(Disconnect, si)

    inv = si.RetrieveContent()

    dc       = getVcInvObj(inv, [vim.Datacenter],             'datacenter',  args.datacenter)
    cluster  = getVcInvObj(inv, [vim.ClusterComputeResource], 'cluster',     args.cluster)
    ds       = getVcInvObj(inv, [vim.Datastore],              'datastore',   args.datastore)
    folder   = getVcInvObj(inv, [vim.Folder],                 'VM folder',   args.vmfolder)
    template = getVcInvObj(inv, [vim.VirtualMachine],         'VM template', args.template)
    network  = getVcInvObj(inv, [vim.OpaqueNetwork],          'OpaqueNetwork', args.network)

    if args.host:
        host     = getVcInvObj(inv, [vim.HostSystem], 'host', args.host)
    else:
        host = None

    snapshot = None
    if args.linked == True:
        for ss in walkSnapshotForrest(template):
            if args.snapshot==ss.name:
                snapshot = ss.snapshot
                break
        else:
            print("Can't find snapshot %s on VM %s" %(args.snapshot, template.name))
            exit(87)


            host = hosts[hostIndex]

        relospec = vim.vm.RelocateSpec()
        relospec.datastore = ds
        relospec.pool = cluster.resourcePool
        if host:
            relospec.host = host

        if args.linked:
            relospec.diskMoveType = \
                vim.vm.RelocateSpec.DiskMoveOptions.createNewChildDiskBacking
        adaptermaps=[]
        configSpec = vim.vm.ConfigSpec()
        for dev in filter(lambda x: x.key/4000==1, template.config.hardware.device):
            devLabel = dev.deviceInfo.label
            r = re.search(r'Network adapter (\d+)', devLabel)
            if not r:
                continue

            dev.addressType = 'assigned'
            dev.connectable.allowGuestControl = True
            dev.connectable.startConnected = True
            dev.connectable.connected=True
            attachOpaqueNetworkDevBacking(args.vm_name, dev, network)

            virdev = vim.vm.device.VirtualDeviceSpec()
            virdev.device = dev
            virdev.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
            configSpec.deviceChange.append(virdev)


            guest_map = vim.vm.customization.AdapterMapping()
            guest_map.adapter = vim.vm.customization.IPSettings()
            
            if args.vm_cidr:
                ipinfo = IPNetwork(args.vm_cidr)
                guest_map.adapter.ip = vim.vm.customization.FixedIp()
                guest_map.adapter.ip.ipAddress = str(ipinfo.ip)
                guest_map.adapter.subnetMask = str(ipinfo.netmask)
                guest_map.adapter.gateway=args.vm_gw
            else:
                guest_map.adapter.ip = vim.vm.customization.DhcpIpGenerator()
            adaptermaps.append(guest_map)
            
        cloneSpec = vim.vm.CloneSpec(location=relospec, config=configSpec,
                powerOn=args.poweron, snapshot=snapshot)

        if args.vm_dnsservers or args.vm_dnssubfixes or args.vm_domain:
            globalip = vim.vm.customization.GlobalIPSettings()
            globalip.dnsServerList = args.vm_dnsservers
            #globalip.dnsSuffixList = args.vm_dnssubfixes

            ident = vim.vm.customization.LinuxPrep()
            ident.domain = args.vm_domain
            ident.hostName = vim.vm.customization.FixedName()
            ident.hostName.name = args.vm_name

            customspec = vim.vm.customization.Specification()
            customspec.nicSettingMap = adaptermaps
            customspec.globalIPSettings = globalip
            customspec.identity = ident

            cloneSpec.customization = customspec

            customspec = vim.vm.customization.Specification()
            customspec.nicSettingMap = adaptermaps
            customspec.globalIPSettings = globalip
            customspec.identity = ident
            cloneSpec.customization = customspec
        print("Begin clone of template %s to VM %s" %(args.template, args.vm_name))
        task = template.Clone(folder=folder, name=args.vm_name, spec=cloneSpec)
        taskList=[task]

        vmCreateWait(si, taskList )

if __name__ == '__main__':
    main()

