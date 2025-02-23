#!/bin/bash

set -e

cd "$(dirname "$0")"

if [ "${1}" == "--help" ]; then
    ./autocut.py "$@"
    exit
fi

if [ -d env ]; then
    # shellcheck disable=SC1091
    . env/bin/activate
fi

git pull origin main
if [ ! -f last-install.sha1 ] || [[ "$(cat last-install.sha1)" != "$(git rev-parse HEAD)" ]]; then
    echo "Updating and installing required dependencies"
    ./install.sh
    git rev-parse HEAD > last-install.sha1
fi
python3 autocut.py "$@"
read -p "Press Enter..."