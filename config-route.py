#! /usr/bin/python

'''
 Copyright 2019-present SK Telecom
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
     http://www.apache.org/licenses/LICENSE-2.0
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
'''

import os
import shlex
import sys
import time
import json
import requests
import subprocess
import pyroute2
import ConfigParser
import socket
import struct
import random
import netifaces
import ipaddress
from netaddr import *
from random import randint
from kubernetes import client, config

SONA_CONFIG_FILE = "/etc/sona/sona-cni.conf"
INT_BRIDGE = "kbr-int"
EXT_BRIDGE = "kbr-ex"
LOCAL_BRIDGE = "kbr-local"

DEFAULT_TRANSIENT_CIDR = "172.10.0.0/16"
DEFAULT_TRANSIENT_LOCAL_CIDR = "172.11.0.0/16"
DEFAULT_SERVICE_CIDR = "10.96.0.0/12"
DEFAULT_FAKE_MAC = "fe:00:00:00:00:20"

def call_popen(cmd):
    '''
    Executes a shell command.

    :param    cmd: shell command to be executed
    :return    standard output of the executed result
    '''
    child = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    output = child.communicate()
    if child.returncode:
        raise RuntimeError("Fatal error executing %s" % (cmd))
    if len(output) == 0 or output[0] is None:
        output = ""
    else:
        output = output[0].decode("utf8").strip()
    return output

def call_prog(prog, args_list):
    '''
    Executes shell command along with a set of arguments.

    :param    prog:      program binary path
                args_list: arguments of the program
    :return    standard output of the executed result
    '''
    cmd = [prog, "--timeout=5", "-vconsole:off"] + args_list
    return call_popen(cmd)

def ovs_vsctl(*args):
    '''
    A helper method to execute ovs-vsctl.

    :param    args:     arguments pointer
    :return    executed result of ovs-vsctl
    '''
    print list(args)
    return call_prog("ovs-vsctl", list(args))

def ovs_ofctl(*args):
    '''
    A helper method to execute ovs-ofctl.

    :param    args:    arguments pointer
    :return    executed result of ovs-ofctl
    '''
    return call_prog("ovs-ofctl", list(args))

def get_dpid():
    '''
    Obtains the data plane identifier.

    :return    data plane identifier
    '''
    try:
        of_result = ovs_ofctl('show', INT_BRIDGE)

        if "dpid:" in of_result:
            first_line = of_result.splitlines()[0]
            return "of:" + first_line.split("dpid:", 1)[1]
        else:
            return None

    except Exception as e:
        raise SonaException(105, "failure get DPID " + str(e))

def get_cidr():
    '''
    Obtains the network CIDR.

    :return     network CIDR
    '''
    node_name = socket.gethostname()
    config.load_kube_config()
    v1 = client.CoreV1Api()
    node = v1.read_node(name=node_name)
    if node is not None:
        return node.spec.pod_cidr
    else:
        return None

def get_gateway_ip():
    '''
    Obtains the overlay gateway IP address.

    :return     gateway IP address
    '''
    cidr = get_cidr()

    if cidr is not None:
        network = ipaddress.ip_network(cidr.decode('unicode_escape'))
        return  str(network[1])

def get_global_cidr():
    '''
    Obtains the network global CIDR.

    :return     network global CIDR
    '''
    cidr = get_cidr()

    if cidr is not None:
        network = ipaddress.ip_network(cidr.decode('unicode_escape'))
        super_net = network.supernet(new_prefix=16)
        return str(super_net)

def get_transient_cidr():
    '''
    Obtains the transient network CIDR.

    :return     transient network CIDR
    '''
    try:
        cf = ConfigParser.ConfigParser()
        cf.read(SONA_CONFIG_FILE)
        if cf.has_option("network", "transient_cidr") is True:
            return cf.get("network", "transient_cidr")
        else:
            return DEFAULT_TRANSIENT_CIDR

    except Exception as e:
        raise SonaException(102, "failure get transient CIDR " + str(e))

def get_transient_local_cidr():
    '''
    Obtains the transient local network CIDR.

    :return     transient local network CIDR
    '''
    try:
        cf = ConfigParser.ConfigParser()
        cf.read(SONA_CONFIG_FILE)
        if cf.has_option("network", "transient_local_cidr") is True:
            return cf.get("network", "transient_local_cidr")
        else:
            return DEFAULT_TRANSIENT_LOCAL_CIDR

    except Exception as e:
        raise SonaException(102, "failure get transient local CIDR " + str(e))

def get_service_cidr():
    '''
    Obtains the service network CIDR.

    :return     service network CIDR
    '''
    try:
        cf = ConfigParser.ConfigParser()
        cf.read(SONA_CONFIG_FILE)
        if cf.has_option("network", "service_cidr") is True:
            return cf.get("network", "service_cidr")
        else:
            return DEFAULT_SERVICE_CIDR

    except Exception as e:
        raise SonaException(102, "failure get service CIDR " + str(e))

def get_external_interface():
    '''
    Obtains the external interface name.

    :return     external interface name
    '''
    try:
        cf = ConfigParser.ConfigParser()
        cf.read(SONA_CONFIG_FILE)
        if cf.has_option("network", "external_interface") is True:
            return cf.get("network", "external_interface")
        else:
            return None

    except Exception as e:
        raise SonaException(102, "failure get external interface " + str(e))

def get_external_bridge_ip():
    '''
    Obtains the external IP address.

    :return	external IP address
    '''
    return netifaces.ifaddresses(EXT_BRIDGE)[netifaces.AF_INET][0]['addr']

def get_external_gateway_ip():
    '''
    Obtains the external gateway IP address.

    :return    external gateway IP address
    '''
    try:
        cf = ConfigParser.ConfigParser()
        cf.read(SONA_CONFIG_FILE)
        if cf.has_option("network", "external_gateway_ip") is True:
            return cf.get("network", "external_gateway_ip")
        else:
            return None

    except Exception as e:
        raise SonaException(102, "failure get external gateway IP " + str(e))

def is_interface_up(interface):
    '''
    Checks whether the given network interface is up or not.
    '''
    addr = netifaces.ifaddresses(interface)
    return netifaces.AF_INET in addr

def has_interface(interface):
    '''
    Checks whether the machine has the given network interface.
    '''
    detail = netifaces.ifaddresses(interface)
    if detail is None:
        return False
    else:
        return True

def activate_ex_intf():
    '''
    Activates the external interface.
    '''
    ipdb = pyroute2.IPDB(mode='explicit')
    ex_intf = get_external_interface()
    ex_gw_ip = get_external_gateway_ip()

    if ex_intf is None:
        return

    if ex_gw_ip is None:
        return

    if has_interface(ex_intf) is False:
        return

    try:
        ext_ip_address = "127.0.0.1/24"
        ext_mac_address = "02:11:22:33:44:55"
        empty_ip_address = "0.0.0.0"
        with ipdb.interfaces[ex_intf] as ext_iface:
            ipv4_addr = ext_iface.ipaddr.ipv4
            if not ipv4_addr:
                print "External interface does not have any IP address"
                return
            ext_ip_address = ipv4_addr[0]["address"] + '/' + str(ipv4_addr[0]["prefixlen"])
            ext_mac_address = ext_iface.address
            for addr in ext_iface.ipaddr:
                addr_str = '/'.join(map(str, addr))
                ext_iface.del_ip(addr_str)

        with ipdb.interfaces[EXT_BRIDGE] as ext_bridge_iface:
            for addr in ext_bridge_iface.ipaddr:
                addr_str = '/'.join(map(str, addr))
                ext_bridge_iface.del_ip(addr_str)

            ext_bridge_iface.add_ip(ext_ip_address)
            addr_config_str = 'other-config:hwaddr=\"' + ext_mac_address + '\"'
            if ext_bridge_iface.operstate == "DOWN":
                ext_bridge_iface.up()

            ovs_vsctl('set', 'bridge', EXT_BRIDGE, addr_config_str)

        intfs = ovs_vsctl('list-ifaces', EXT_BRIDGE)
        if ex_intf not in intfs:
            ovs_vsctl('add-port', EXT_BRIDGE, ex_intf)

    except Exception as e:
        raise SonaException(108, "failure activate external interface " + str(e))

def activate_gw_intf():
    '''
    Activates the host default gateway interface.
    '''
    ipdb = pyroute2.IPDB(mode='explicit')
    cidr = get_cidr()
    gw_ip = get_gateway_ip()
    global_cidr = get_global_cidr()
    transient_cidr = get_transient_cidr()
    transient_local_cidr = get_transient_local_cidr()
    service_cidr = get_service_cidr()

    try:
        with ipdb.interfaces[INT_BRIDGE] as bridge_iface:
            for addr in bridge_iface.ipaddr:
                addr_str = '/'.join(map(str, addr))
                bridge_iface.del_ip(addr_str)

            bridge_iface.add_ip(gw_ip + '/' + cidr.split('/')[1])
            if bridge_iface.operstate == "DOWN":
                bridge_iface.up()

	with ipdb.interfaces[LOCAL_BRIDGE] as bridge_iface:
            if bridge_iface.operstate == "DOWN":
                bridge_iface.up()

            addr_config_str = 'other-config:hwaddr=\"' + DEFAULT_FAKE_MAC + '\"'
            ovs_vsctl('set', 'bridge', LOCAL_BRIDGE, addr_config_str)

        local_found = False
        global_found = False
        transient_found = False
        service_found = False
	transient_local_found = False

        for route in ipdb.routes:
            if route['dst'] == cidr:
                local_found = True
            if route['dst'] == global_cidr:
                global_found = True
            if route['dst'] == transient_cidr:
                transient_found = True
            if route['dst'] == service_cidr:
                service_found = True
            if route['dst'] == transient_local_cidr:
                transient_local_found = True

        if not local_found:
            ipdb.routes.add(dst=cidr, oif=ipdb.interfaces[INT_BRIDGE].index).commit()

        if not global_found:
            ipdb.routes.add(dst=global_cidr, oif=ipdb.interfaces[INT_BRIDGE].index).commit()

        if not transient_found:
            ipdb.routes.add(dst=transient_cidr, oif=ipdb.interfaces[INT_BRIDGE].index).commit()

        if not service_found:
            ipdb.routes.add(dst=service_cidr, oif=ipdb.interfaces[INT_BRIDGE].index).commit()

	if not transient_local_found:
            ipdb.routes.add(dst=transient_local_cidr, oif=ipdb.interfaces[LOCAL_BRIDGE].index).commit()

    except Exception as e:
        raise SonaException(108, "failure activate gateway interface " + str(e))

def main():
    activate_gw_intf()
    activate_ex_intf()

class SonaException(Exception):

    def __init__(self, code, message, details=None):
        '''
        The exception constructor which handles the SONA related exceptions.

        :param  code:       exception code
                message:    exception message
                details:    detailed message of this exception
        '''
        super(SonaException, self).__init__("%s - %s" % (code, message))
        self._code = code
        self._msg = message
        self._details = details

    def sona_error(self):
        '''
        Handles the SONA related errors.

        :return  exception details including error code and message
        '''
        error_data = {'code': self._code, 'message': self._msg}
        if self._details:
            error_data['details'] = self._details
        return json.dumps(error_data)

if __name__ == '__main__':
    try:
        main()
    except SonaException as e:
        print(e.sona_error())
        sys.exit(1)
    except Exception as e:
        error = {'code': 200, 'message': str(e)}
        print(json.dumps(error))
        sys.exit(1)
