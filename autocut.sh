#!/bin/bash

set -e

cd "$(dirname "$0")"
git pull origin main
./autocut.py "$@"
