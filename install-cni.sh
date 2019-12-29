#!/bin/sh

# Script to install SONA CNI on a Kubernetes host.
# - Expects the host CNI binary path to be mounted at /host/opt/cni/bin.

# Ensure all variables are defined, and that the script fails when an error is hit.
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

# Clean up any existing binaries assets.
rm -f /host/opt/cni/bin/sona

if [ ! -w "$dir" ];
then
  echo "$dir is non-writeable, skipping"
else
  cp /sona /host/opt/cni/bin || exit_with_error "Failed to copy sona binary to /host/opt/cni/bin. This may be caused by selinux configuration on the host, or something else."
fi

echo "Wrote SONA CNI binaries to /host/opt/cni/bin"

exit 0
