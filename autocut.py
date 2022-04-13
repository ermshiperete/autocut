#!/usr/bin/python3
# Requirements:
# pip install pydub
# sudo apt-add-repository ppa:marin-m/songrec
# sudo apt install songrec

import configparser
import datetime
import json
import logging
import os
import subprocess
import tempfile
from pydub import AudioSegment, effects, silence


def secure_lookup(data, key1, key2=None):
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
    return None


def load_audio(file):
    logging.info('Loading %s', file)
    return AudioSegment.from_file(file)


def detect_segments(audio):
    logging.info('Detecting segments')
    return silence.detect_nonsilent(audio, min_silence_len=5000, silence_thresh=-50, seek_step=100)


def get_index_of_intro_segment(segments):
    logging.info('Finding intro segment')
    i = -1
    for segment in segments:
        i = i + 1
        logging.info('\tExamining segment %d', i)
        filename = os.path.join(tempfile.gettempdir(), "segment.mp3")
        with open(filename, "wb") as f:
            myAudio[segment[0]:segment[1]].export(f, format="mp3")
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
        logging.info('\tProcessing segment %d', j)
        normalized = effects.normalize(audio[segments[j][0]:segments[j][1]])
        if resultAudio is None:
            resultAudio = normalized
        else:
            resultAudio = resultAudio + normalized

        if j + 1 < len(segments):
            resultAudio = resultAudio + audio[segments[j][1]:segments[j+1][0]]
    return resultAudio


def export_result(audio, outputdir):
    logging.info('Exporting result')
    with open(os.path.join(outputdir, 'result.mp3'), 'wb') as f:
        today = datetime.datetime.now()
        trackno = '%04d%02d%02d' % (today.year, today.month, today.day)
        metadata = {'title': 'Gottesdienst Niederdresselndorf', 'track': trackno,
                    'year': today.year, 'genre': 'Gottesdienst'}  # 'artist': 'Song Artist',
        audio.export(f, format='mp3', bitrate='128k', tags=metadata, parameters=[
                        '-minrate', '128k', '-maxrate', '128k'])


def read_config():
    tempdir = tempfile.gettempdir()
    config = configparser.ConfigParser()
    config.read_string("""
    [Paths]
    InputPath=%s
    OutputPath=%s
    """ % (tempdir, tempdir))
    config.read('autocut.config')
    return config

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

    #myAudio = AudioSegment.from_file("/tmp/Godi.mp4", format="mp4")
    myAudio = load_audio(os.path.join(config['Paths']['InputPath'], 'Godi.mp4'))

    # segments = silence.detect_nonsilent(myAudio, min_silence_len=5000, silence_thresh=-50, seek_step=100)
    segments = detect_segments(myAudio)

    introIndex = get_index_of_intro_segment(segments)
    if introIndex < 0:
        logging.error("Can't find intro segment!")
        exit(1)

    resultAudio = normalize_segments(myAudio, segments, introIndex)

    export_result(resultAudio, config['Paths']['OutputPath'])
    logging.info('AUTOCUT FINISHED!')
