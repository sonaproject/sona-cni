#!/bin/sh

# Script to install SONA CNI configuration on a Kubernetes host.
# - Expects the host CNI network config path to be mounted at /host/etc/cni/net.d

# Ensure all variables are defined, and that the script fails when an error is occured.
set -u -e

# Capture the usual signals and exit from the script
trap 'echo "INT received, simply exiting..."; exit 0' INT
trap 'echo "TERM received, simply exiting..."; exit 0' TERM
trap 'echo "HUP received, simply exiting..."; exit 0' HUP

# Helper function for raising errors
# Usage:
# some_command || exit_with_error "some_command_failed: maybe try..."
exit_with_error(){
  echo "$1"
  exit 1
}

# Clean up all existing configs.
rm -rf /host/etc/cni/net.d/*

TMP_CNI_CONF='/cni.conf.tmp'
: "${CNI_NETWORK_CONFIG:=}"
if [ "${CNI_NETWORK_CONFIG}" != "" ]; then
  echo "Using CNI config template from CNI_NETWORK_CONFIG environment variable."
  cat >$TMP_CNI_CONF <<EOF
${CNI_NETWORK_CONFIG}
EOF
fi

CNI_CONF_NAME=${CNI_CONF_NAME:-1-sona-net.conf}
CNI_OLD_CONF_NAME=${CNI_OLD_CONF_NAME:-1-sona-net.conf}

echo "CNI config: $(cat ${TMP_CNI_CONF})"

# Delete old CNI config files for upgrades.
if [ "${CNI_CONF_NAME}" != "${CNI_OLD_CONF_NAME}" ]; then
    rm -f "/host/etc/cni/net.d/${CNI_OLD_CONF_NAME}"
fi
# Move the temporary CNI config into place.
mv "$TMP_CNI_CONF" /host/etc/cni/net.d/"${CNI_CONF_NAME}" || \
  exit_with_error "Failed to mv files. This may be caused by selinux configuration on the host, or something else."

echo "Created CNI config ${CNI_CONF_NAME}"

exit 0
