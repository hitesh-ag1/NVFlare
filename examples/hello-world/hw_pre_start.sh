#!/usr/bin/env bash

# NVFLARE INSTALL
NVFLARE_VERSION="2.3.0rc3"
pip install 'nvflare>=${NVFLARE_VERSION}'

# set NVFLARE_HOME
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
export NVFLARE_HOME="$SCRIPT_DIR/../../"

# set NVFLARE_POC_WORKSPACE
NVFLARE_POC_WORKSPACE="/tmp/nvflare/poc"
export NVFLARE_POC_WORKSPACE

echo "y" | nvflare poc --prepare -n 2

if [ ! -L "${NVFLARE_POC_WORKSPACE}/admin/transfer" ]; then
     echo "'nvflare poc --prepare' did not generate symlink '${NVFLARE_POC_WORKSPACE}/admin/transfer'"
     exit 1
fi

nvflare poc --start -ex admin



