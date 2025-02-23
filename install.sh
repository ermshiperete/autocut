#!/bin/bash
set -e

if (( $(lsb_release -r -s | cut -d'.' -f1) >= 24 )); then
    [ ! -d env ] && python3 -m venv env
    # shellcheck disable=SC1091
    . env/bin/activate
fi

if (( $(python3 --version | cut -d' ' -f2 | cut -d'.' -f2) >= 12)); then
    NUMPY_VERSION=1.26.4
    PYAML_VERSION=""
else
    NUMPY_VERSION=1.23.5
    PYAML_VERSION="==5.4.1"
fi

pip3 install --upgrade numpy==${NUMPY_VERSION}
pip3 install inaSpeechSegmenter
pip3 install pydub
pip3 install --upgrade PyYAML${PYAML_VERSION}
