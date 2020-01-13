#! /usr/bin/python

'''
 Copyright 2020-present SK Telecom
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


import json, yaml, sys, getopt
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
   inputfile = ''
   outputfile = ''
   try:
      opts, args = getopt.getopt(argv,"ht:i:o:",["ifile=","ofile="])
   except getopt.GetoptError:
      print ('replace-master-ip.py -i <inputfile> -o <outputfile>')
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print ('replace-master-ip.py -i <inputfile> -o <outputfile>')
         sys.exit()
      elif opt in ("-i", "--ifile"):
         inputfile = arg
      elif opt in ("-o", "--ofile"):
         outputfile = arg
   with open(inputfile, 'r') as stream:
      try:
         raw = json.load(stream)
         name = raw["name"]
         storage = raw["storage"]
         node_port = raw["node"]["port"]
         cluster = {
            "node": {
                "ip": master_ip(),
                "id": master_ip(),
                "port": node_port
            },
            "storage": storage,
            "name": name
         }
      except yaml.YAMLError as exc:
         print(exc)
   with open(outputfile, "w") as jsonfile:
      json.dump(cluster, jsonfile)
if __name__ == "__main__":
   main(sys.argv[1:])
