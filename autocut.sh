#!/bin/bash

set -e

cd "$(dirname "$0")"

if [ -d env ]; then
    # shellcheck disable=SC1091
    . env/bin/activate
fi

if [ "${1}" == "--help" ]; then
    python3 autocut.py "$@"
    exit
fi

git pull origin main
if [ ! -f last-install.sha1 ] || [[ "$(cat last-install.sha1)" != "$(git rev-parse HEAD)" ]]; then
    echo "Updating and installing required dependencies"
    ./install.sh
    git rev-parse HEAD > last-install.sha1
fi
python3 autocut.py "$@"
# shellcheck disable=SC2162
read -p "Press Enter..."
