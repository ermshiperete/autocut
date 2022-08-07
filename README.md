# Autocut - Automatic processing of service recordings

This little tool identifies the intro clip in a recording, cuts everything before
it and then normalizes the rest of the recording.

## Installation

```bash
sudo apt-add-repository ppa:marin-m/songrec
sudo apt install songrec python3 python3-pip ncftp lame sox openssh-client wget ffmpeg
pip install pydub
```

### Create Shortcut

To create a shortcut on Windows to the script in WSL:

```bash
C:\Windows\System32\wsl.exe -d Ubuntu-20.04 -- bash -c /path/to/autocut/autocut.sh
```

## How it works

`autocut.py` is the main file that does the autocutting. `autocut.sh` is a little
shell script that allows to automatically update to the lastest version. This allows
to fix bugs without requiring access to the machine where the cutting is done.

`upload-announcement.sh` and `upload-to-phone.sh` are used by `autocut.py` to upload
the recording to the website and to the phone server.

`autocut.config` and `Gottesdienst.yml` are two files used to customize the behaviour
and provide additional information about the services.

## Configuration

Copy the file `autoconfig.config.sample` to `autoconfig.config` and adjust the
values.

The metadata for the services can be configured by specifying a git repository in
`Paths/Services` in the `.config` file:

```config
[Paths]
Services=https://gist.github.com/1234567890deadbeef09876543210123.git
```

The git repo should have a file `Gottesdienst.yml` with the date and properties
for the individual services. These properties will be used for the filename as
well as the MP3 tags. For example:

```yml
2022-08-28:
    name: eXtrakt-Gottesdienst
    announce: What to call the service in the phone intro
    artist: Preacher
```

`announce` allows to specify a slightly different title for the service
which is used for the phone announcement. This can be useful for special
services with additional information.

If `announce` is not set `name` will be used. If `name` is not set,
`Gottesdienst` will be used instead.
