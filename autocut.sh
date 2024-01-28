#!/bin/bash

set -e

cd "$(dirname "$0")"

if [ "${1}" == "--help" ]; then
    ./autocut.py "$@"
    exit
fi

git pull origin main
if [ ! -f last-install.sha1 ] || [[ "$(cat last-install.sha1)" != "$(git rev-parse HEAD)" ]]; then
    echo "Updating and installing required dependencies"
    ./install.sh
    git rev-parse HEAD > last-install.sha1
fi
./autocut.py "$@"
