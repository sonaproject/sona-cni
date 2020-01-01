#!/usr/bin/env python
import sys, getopt
from kubernetes import client, config
def master_ip():
    config.load_kube_config()
    api_instance = client.CoreV1Api()
    master_str = "node-role.kubernetes.io/master"
    node_list = api_instance.list_node()
    for node in node_list.items:
        node_labels = node.metadata.labels
        for labels in node_labels:
            # TODO: need to check whether the given master node has SONA POD
            if master_str in labels:
                return get_node_address(node)
    return None
def get_node_address(node):
    node_status = node.status
    for address in node_status.addresses:
        if address.type == "InternalIP":
            return address.address
    return None

def main(argv):
    print(master_ip())

if __name__ == "__main__":
   main(sys.argv[1:])
