# Autocut - Automatic processing of service recordings

This little tool identifies the intro clip in a recording, cuts everything before
it and then normalizes the rest of the recording.

## Installation

```bash
sudo apt-add-repository ppa:marin-m/songrec
sudo apt install songrec
pip install pydub
```

## Configuration

Copy the file `autoconfig.config.sample` to `autoconfig.config` and adjust the
values.
