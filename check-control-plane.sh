#!/bin/bash
set -e

# Script to check whether the control plane is ready (ON_BOARDED state).

while true
do
  master_ip=$(/master-ip 2>&1)
  check_status_str='curl -sL --user onos:rocks -w "%{http_code}\\n" "http://'$master_ip':8181/onos/k8snode/configure/state/'$KUBERNETES_NODE_NAME'" -o /dev/null'
  if [ $(eval $check_status_str) = "200" ];
  then
    response_str='curl -sL --user onos:rocks http://'$master_ip':8181/onos/k8snode/configure/state/'$KUBERNETES_NODE_NAME
    number=$(echo $(eval $response_str) | grep "ON_BOARDED" | wc -l)
    if [ $number = 0 ];
    then
      echo "Control plane is not ready!"
      sleep 5s
    else
      echo "Control plane is ready now!"
      break
    fi
  else
    echo "Failed to connect to control plane!"
    sleep 5s
  fi
done

exit 0
