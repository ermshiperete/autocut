#!/usr/bin/python3
# Requirements:
# pip install pydub
# sudo apt-add-repository ppa:marin-m/songrec
# sudo apt install songrec

import configparser
import datetime
import glob
import json
import logging
import os
import re
import subprocess
import tempfile
from pydub import AudioSegment, effects, silence
import yaml


def secure_lookup(data, key1, key2=None, default=None):
    """
    Return data[key1][key2] while dealing with data being None or key1 or key2 not existing
    """
    if not data:
        return None
    if key1 in data:
        if not key2:
            return data[key1]
        if key2 in data[key1]:
            return data[key1][key2]
    return default


def load_audio(file):
    logging.info('Loading %s', file)
    if not os.path.exists(file):
        logging.error('File %s not found', file)
        exit(2)
    return AudioSegment.from_file(file)


def detect_segments(audio):
    logging.info('Detecting segments')
    return silence.detect_nonsilent(audio, min_silence_len=5000, silence_thresh=-50, seek_step=100)


def get_index_of_intro_segment(audio, segments):
    logging.info('Finding intro segment (in %d segments)', len(segments))
    i = -1
    for segment in segments:
        i = i + 1
        logging.info('    Examining segment %d', i)
        filename = os.path.join(tempfile.gettempdir(), "segment.mp3")
        with open(filename, "wb") as f:
            audio[segment[0]:segment[1]].export(f, format="mp3")
        out = subprocess.Popen(['songrec', 'audio-file-to-recognized-song',
                            filename], stdout=subprocess.PIPE, text=True)
        (line, _) = out.communicate()
        data = json.loads(line)

        # Jaykar: Dior
        if secure_lookup(data, 'track', 'subtitle') == 'Jaykar' and secure_lookup(data, 'track', 'title') == 'Dior':
            logging.info('Found intro in segment %d', i)
            return i
    logging.error("Can't find intro segment!")
    return -1


def normalize_segments(audio, segments, introIndex):
    logging.info('Normalizing %d segments', len(segments) - introIndex - 1)
    resultAudio = None
    for j in range(introIndex + 1, len(segments)):
        logging.info('    Processing segment %d', j)
        normalized = effects.normalize(audio[segments[j][0]:segments[j][1]])
        if resultAudio is None:
            resultAudio = normalized
        else:
            resultAudio = resultAudio + normalized

        if j + 1 < len(segments):
            resultAudio = resultAudio + audio[segments[j][1]:segments[j+1][0]]
    return resultAudio


def get_info(services, date):
    service = secure_lookup(services, date)
    return { 'title': secure_lookup(service, 'name', None, 'Gottesdienst'),
             'artist': secure_lookup(service, 'artist', None, 'Rainer Heuschneider'),
             'album': 'Ev. Kirchengemeinde Niederdresselndorf',
             'trackno': '%04d%02d%02d' % (date.year, date.month, date.day),
             'year': '%04d' % date.year,
             'isodate': '%04d-%02d-%02d' % (date.year, date.month, date.day),
             'date': date
    }


def export_result(audio, outputdir, info):
    logging.info('Exporting result')
    filename = os.path.join(outputdir, ('%s_%s_%s.mp3' % (
        info['isodate'], info['title'], info['album'])).replace(' ', '_'))
    with open(filename, 'wb') as f:
        metadata = {'title': info['title'], 'track': info['trackno'], 'artist': info['artist'],
                    'album': info['album'], 'year': info['year'], 'genre': 'Gottesdienst'}
        audio.export(f, format='mp3', bitrate='128k', tags=metadata, parameters=[
                        '-minrate', '128k', '-maxrate', '128k'])


def read_config():
    tempdir = tempfile.gettempdir()
    config = configparser.ConfigParser()
    config.read_string("""
    [Paths]
    InputPath=%s
    OutputPath=%s
    Services=
    """ % (tempdir, tempdir))
    config.read(os.path.join(os.path.basename(os.path.realpath(__file__)), 'autocut.config'))
    return config


def find_input_file(dir):
    # First try if there is a file with the current date in name
    today = datetime.datetime.now()
    files = glob.glob(os.path.join(dir, '%04d-%02d-%02d*' % (today.year, today.month, today.day)))
    files.sort()
    if len(files) >= 1:
        return files[0]
    # Otherwise sort by name and take the last one (which if the names start with the data is
    # the newest one)
    files = glob.glob(os.path.join(dir, '*'))
    files.sort()
    if len(files) >= 1:
        return files[len(files) - 1]
    return ''


def read_services(repo):
    if not repo:
        return {}
    logging.info('Getting Gottesdienste metadata')
    dir = 'Gottesdienste'
    if os.path.exists(dir):
        subprocess.run(['git', 'pull', 'origin'], cwd=dir)
    else:
        subprocess.run(['git', 'clone', repo, dir])
    yml_file = os.path.join(dir, 'Gottesdienst.yml')
    if not os.path.exists(yml_file):
        logging.warning("Can't find Gottesdienst.yml")
        return {}
    with open(yml_file, 'r') as f:
        yml = yaml.load(f, Loader=yaml.FullLoader)
        return yml


def extract_date_from_filename(filename):
    match = re.search('^(\d+)-(\d+)-(\d+)', os.path.basename(filename))
    if not match:
        return datetime.date.today()
    parts = match.groups()
    if not parts or len(parts) < 3:
        return datetime.date.today()
    return datetime.date.fromisoformat('%s-%s-%s' % (parts[0], parts[1], parts[2]))


def save_announcement_file(info):
    months = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
              'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
    logging.info('Saving announcement file')
    filename = os.path.join(tempfile.gettempdir(), "Announce.txt")
    with open(filename, 'w') as f:
        f.write('Guten Tag! Sie hören den %s vom %d. %s %04d.' % (info['title'], info['date'].day, months[info['date'].month], info['date'].year))
    return filename


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(tempfile.gettempdir(), "autocut.log")),
            logging.StreamHandler()
        ]
    )
    logging.info('STARTING AUTOCUT')

    config = read_config()

    services = read_services(config['Paths']['Services'])

    audio_file = find_input_file(config['Paths']['InputPath'])
    date = extract_date_from_filename(audio_file)
    if not audio_file:
        audio_file = os.path.join(config['Paths']['InputPath'], 'Godi.mp4')
    myAudio = load_audio(audio_file)

    segments = detect_segments(myAudio)

    introIndex = get_index_of_intro_segment(myAudio, segments)
    if introIndex < 0:
        exit(1)

    resultAudio = normalize_segments(myAudio, segments, introIndex)

    info = get_info(services, date)
    export_result(resultAudio, config['Paths']['OutputPath'], info)
    save_announcement_file(info)
    logging.info('AUTOCUT FINISHED!')
