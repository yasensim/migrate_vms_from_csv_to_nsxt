#!/usr/bin/env python
#
# Author Yasen Simeonov
#
__author__ = 'yasensim'

import sys, csv, argparse, getpass
from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnectNoSSL, Disconnect

def get_args():
    parser = argparse.ArgumentParser(
        description='Standard Arguments for talking to vCenter')

    # because -h is reserved for 'help' we use -s for service
    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSphere service to connect to')

    # because we want -p for password, we use -o for port
    parser.add_argument('-o', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='Port to connect on')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='User name to use when connecting to host')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use when connecting to host')

    parser.add_argument('-f', '--file',
                        required=True,
                        action='store',
                        help='Specify CSV file containing vm_name,LogicalSwitch per line')

    args = parser.parse_args()
    prompt_for_password(args)
    return args


def prompt_for_password(args):
    """
    if no password is specified on the command line, prompt for it
    """
    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password for host %s and user %s: ' %
                   (args.host, args.user))
    return args


def wait_for_tasks(service_instance, tasks):
    property_collector = service_instance.content.propertyCollector
    task_list = [str(task) for task in tasks]
    obj_specs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task)
                 for task in tasks]
    property_spec = vmodl.query.PropertyCollector.PropertySpec(type=vim.Task,
                                                               pathSet=[],
                                                               all=True)
    filter_spec = vmodl.query.PropertyCollector.FilterSpec()
    filter_spec.objectSet = obj_specs
    filter_spec.propSet = [property_spec]
    pcfilter = property_collector.CreateFilter(filter_spec, True)
    try:
        version, state = None, None
        while len(task_list):
            update = property_collector.WaitForUpdates(version)
            for filter_set in update.filterSet:
                for obj_set in filter_set.objectSet:
                    task = obj_set.obj
                    for change in obj_set.changeSet:
                        if change.name == 'info':
                            state = change.val.state
                        elif change.name == 'info.state':
                            state = change.val
                        else:
                            continue

                        if not str(task) in task_list:
                            continue

                        if state == vim.TaskInfo.State.success:
                            task_list.remove(str(task))
                        elif state == vim.TaskInfo.State.error:
                            raise task.info.error
            version = update.version
    finally:
        if pcfilter:
            pcfilter.Destroy()

def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj

def editVM(vm_name, ls, s):

    try:
        net = get_obj(s.RetrieveContent(), [vim.Network], ls)
        opequeId = net.summary.opaqueNetworkId
        vm = get_obj(s.RetrieveContent(), [vim.VirtualMachine], vm_name)
        device_change = []
        for device in vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualEthernetCard):
                nicspec = vim.vm.device.VirtualDeviceSpec()
                nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
                nicspec.device = device
                nicspec.device.wakeOnLanEnabled = True
                nicspec.device.addressType = 'assigned'
                nicspec.device.key = 4000
                nicspec.device.backing = vim.vm.device.VirtualEthernetCard.OpaqueNetworkBackingInfo()
                nicspec.device.backing.opaqueNetworkType = 'nsx.LogicalSwitch'
                nicspec.device.backing.opaqueNetworkId = opequeId
                nicspec.device.deviceInfo.summary = 'nsx.LogicalSwitch: %s' % (opequeId)
                nicspec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
                nicspec.device.connectable.startConnected = True
                nicspec.device.connectable.connected = True
                nicspec.device.connectable.allowGuestControl = True
                device_change.append(nicspec)
                break
        config_spec = vim.vm.ConfigSpec(deviceChange=device_change)
        task = vm.ReconfigVM_Task(config_spec)
        wait_for_tasks(s, [task])
        print("Successfully changed to network %s for VM %s" % (ls, vm_name))
    except vmodl.MethodFault as error:
        print("Caught vmodl fault : %s" % (error.msg))
        return -1
    return 0



def main():

    args = get_args()

    s = SmartConnectNoSSL(host=args.host,
                          user=args.user,
                          pwd=args.password,
                          port=int(args.port))
    with open(args.file, 'rt') as ifile:
        reader = csv.reader(ifile)
        for row in reader:
            editVM(row[0], row[1], s)
    Disconnect(s)


if __name__ == "__main__":
    main()
