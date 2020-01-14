#!/bin/sh

# Script to install SONA CNI configuration on a Kubernetes host.
# - Expects the host SONA network config path to be mounted at /host/etc/sona

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
rm -rf /host/etc/sona/*

TMP_SONA_CONF='/sona.conf.tmp'
: "${SONA_NETWORK_CONFIG:=}"
if [ "${SONA_NETWORK_CONFIG}" != "" ]; then
  echo "Using SONA config template from SONA_NETWORK_CONFIG environment variable."
  cat >$TMP_SONA_CONF <<EOF
${SONA_NETWORK_CONFIG}
EOF
fi

# Insert any of the supported "auto" parameters.
sed -i s/__TUNNEL_TYPE__/"${TUNNEL_TYPE:-VXLAN}"/g $TMP_SONA_CONF
sed -i s/__MTU_SIZE__/"${MTU_SIZE:-1400}"/g $TMP_SONA_CONF
sed -i s/__EXTERNAL_INTERFACE__/"${EXTERNAL_INTERFACE:-eth1}"/g $TMP_SONA_CONF
sed -i s/__EXTERNAL_GATEWAY_IP__/"${EXTERNAL_GATEWAY_IP:-172.16.230.1}"/g $TMP_SONA_CONF

SONA_CONF_NAME=${SONA_CONF_NAME:-sona-cni.conf}
SONA_OLD_CONF_NAME=${SONA_OLD_CONF_NAME:-sona-cni.conf}

echo "SONA config: $(cat ${TMP_SONA_CONF})"

# Delete old SONA config files for upgrades.
if [ "${SONA_CONF_NAME}" != "${SONA_OLD_CONF_NAME}" ]; then
    rm -f "/host/etc/sona/${SONA_OLD_CONF_NAME}"
fi
# Move the temporary SONA config into place.
mv "$TMP_SONA_CONF" /host/etc/sona/"${SONA_CONF_NAME}" || \
  exit_with_error "Failed to mv files. This may be caused by selinux configuration on the host, or something else."

echo "Created SONA config ${SONA_CONF_NAME}"

exit 0
