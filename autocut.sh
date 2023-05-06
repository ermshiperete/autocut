#!/bin/bash

set -e

cd "$(dirname "$0")"
current=$(git rev-parse HEAD)
git pull origin main
if [[ $(git diff $current.. -- install.sh | wc -l) > 0 ]]; then
    echo "Updating and installing required dependencies"
    ./install.sh
fi

./autocut.py "$@"
