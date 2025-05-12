#!/bin/bash
set -e

is_package_installed() {
    local PACKAGE=$1
    dpkg -s "${PACKAGE}" > /dev/null 2>&1
}


check_and_install_package() {
    local PACKAGES=$1
    local TOINSTALL=""
    for p in ${PACKAGES}; do
        if ! is_package_installed "${p}"; then
            TOINSTALL="${TOINSTALL} ${p}"
        fi
    done

    if [ -n "${TOINSTALL}" ]; then
        echo "Installing missing packages: ${TOINSTALL}"
        sudo apt-get update
        # shellcheck disable=SC2086
        sudo apt-get install -y ${TOINSTALL}
    fi
}

check_repository() {
    local REPO=$1

    if ! add-apt-repository --list | grep -q "${REPO}"; then
        echo "Adding repository ppa:${REPO}."
        sudo add-apt-repository -y "ppa:${REPO}"
    fi
}

check_repository marin-m/songrec
check_and_install_package "songrec python3 python3-pip python3.12-venv ncftp lame sox openssh-client wget ffmpeg"

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
