# Autocut - Automatic processing of service recordings

This little tool identifies the intro clip in a recording, cuts everything before
it and then normalizes the rest of the recording.

## Installation

```bash
sudo apt-add-repository ppa:marin-m/songrec
sudo apt install songrec python3 python3-pip
pip install pydub
```

### Create Shortcut

To create a shortcut on Windows to the script in WSL:

```bash
C:\Windows\System32\wsl.exe -d Ubuntu-20.04 -- bash -c /path/to/autocut/autocut.py
```

## Configuration

Copy the file `autoconfig.config.sample` to `autoconfig.config` and adjust the
values.
