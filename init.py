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
BRIDGE_NAME = "kbr-int"
EXT_BRIDGE = "kbr-ex"

EXTERNAL_GW_IP = "external.gateway.ip"
EXTERNAL_INTF_NAME = "external.interface.name"
EXTERNAL_BR_IP = "external.bridge.ip"

DEFAULT_TRANSIENT_CIDR = "172.10.0.0/16"
DEFAULT_SERVICE_CIDR = "10.96.0.0/12"

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
        of_result = ovs_ofctl('show', BRIDGE_NAME)

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
    try:
        cf = ConfigParser.ConfigParser()
        cf.read(SONA_CONFIG_FILE)
        return cf.get("network", "cidr");

    except Exception as e:
        raise SonaException(102, "failure get CIDR " + str(e))

def get_global_cidr():
    '''
    Obtains the network global CIDR.

    :return     network global CIDR
    '''
    try:
        cf = ConfigParser.ConfigParser()
        cf.read(SONA_CONFIG_FILE)
        return cf.get("network", "global_cidr");

    except Exception as e:
        raise SonaException(102, "failure get global CIDR " + str(e))

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

    if is_interface_up(ex_intf) is False:
        return

    intfs = ovs_vsctl('list-ifaces', EXT_BRIDGE)
    if ex_intf in intfs:
        return

    try:
        ovs_vsctl('add-port', EXT_BRIDGE, ex_intf)
        ip_address = netifaces.ifaddresses(ex_intf)[netifaces.AF_INET][0]['addr']
        intf_desc = ovs_ofctl('dump-ports-desc', EXT_BRIDGE)
        keyword = '(' + ex_intf + '): addr:'
        mac_address = intf_desc.split(keyword, 1)[1][:17]
        ovs_vsctl('set', 'Interface', EXT_BRIDGE,
                         'external-ids:ip_address=%s' % ip_address, 
                         'external-ids:ext_interface=%s' % ex_intf, 
                         'external-ids:ext_gw_ip_address=%s' % ex_gw_ip)

    except Exception as e:
        raise SonaException(108, "failure activate external interface " + str(e))

def activate_gw_intf():
    '''
    Activates the host default gateway interface.
    '''
    ipdb = pyroute2.IPDB(mode='explicit')
    cidr = get_cidr()
    network = ipaddress.ip_network(cidr.decode('unicode_escape'))
    gw_ip = str(network[1])
    global_cidr = get_global_cidr()
    transient_cidr = get_transient_cidr()
    service_cidr = get_service_cidr()

    try:
        with ipdb.interfaces[BRIDGE_NAME] as bridge_iface:
            if bridge_iface.operstate != "up":
                bridge_iface.add_ip(gw_ip + '/' + cidr.split('/')[1])
                bridge_iface.up()

        local_found = False
        global_found = False
        transient_found = False
        service_found = False
        for route in ipdb.routes:
            if route['dst'] == cidr:
                local_found = True
            if route['dst'] == global_cidr:
                global_found = True
            if route['dst'] == transient_cidr:
                transient_found = True
            if route['dst'] == service_cidr:
                service_found = True

        if not local_found:
            ipdb.routes.add(dst=cidr, oif=ipdb.interfaces[BRIDGE_NAME].index).commit()

        if not global_found:
            ipdb.routes.add(dst=global_cidr, oif=ipdb.interfaces[BRIDGE_NAME].index).commit()

        if not transient_found:
            ipdb.routes.add(dst=transient_cidr, oif=ipdb.interfaces[BRIDGE_NAME].index).commit()

        if not service_found:
            ipdb.routes.add(dst=service_cidr, oif=ipdb.interfaces[BRIDGE_NAME].index).commit()

    except Exception as e:
        raise SonaException(108, "failure activate gateway interface " + str(e))

def addAnnotationToNode(api_instance, node_name, annot_key, annot_value):
    node = api_instance.read_node(name=node_name)
    node.metadata.annotations[annot_key] = annot_value
    return api_instance.patch_node(name=node_name, body=node)

def main():

    ex_gw_ip = get_external_gateway_ip()
    ex_br_ip = get_external_bridge_ip()
    ex_gw_intf = get_external_interface()
    hostname = socket.gethostname()

    # Configs can be set in Configuration class directly or using helper utility
    config.load_kube_config()

    v1 = client.CoreV1Api()
 
    if hostname is not None:
        # add external gateway IP address
        addAnnotationToNode(v1, hostname, EXTERNAL_GW_IP, ex_gw_ip)

        # add external interface name
        addAnnotationToNode(v1, hostname, EXTERNAL_INTF_NAME, ex_gw_intf)

        # add external bridge IP
        addAnnotationToNode(v1, hostname, EXTERNAL_BR_IP, ex_br_ip)

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
