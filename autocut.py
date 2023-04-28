#!/usr/bin/python3
# Requirements:
# pip install pydub
# sudo apt-add-repository ppa:marin-m/songrec
# sudo apt install songrec

import argparse
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
from inaSpeechSegmenter import Segmenter


def secure_lookup(data, key1, key2=None, default=None):
    """
    Return data[key1][key2] while dealing with data being None or key1 or key2 not existing
    """
    if not data:
        return default
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


def detect_segments(audio, silence_len=1000, seek_step=100):
    logging.info('Detecting segments')
    return silence.detect_nonsilent(audio, min_silence_len=silence_len, silence_thresh=-50, seek_step=seek_step)


def detect_detailed_segments(audio_file, startMilliSeconds):
    logging.info('Detecting detailed segments')
    segmenter = Segmenter()
    segmentation = segmenter(audio_file, start_sec=startMilliSeconds / 1000)
    return segmentation


def get_index_of_intro_segment(audio, segments):
    logging.info('Finding intro segment (in %d segments)', len(segments))
    i = -1
    for segment in segments:
        i = i + 1
        logging.info('    Examining segment %d', i)
        filename = os.path.join(tempfile.gettempdir(), "segment.mp3")
        if debug:
            filename = os.path.join(tempfile.gettempdir(), "segment%d.mp3" % i)
        with open(filename, "wb") as f:
            audio[segment[0]:segment[1]].export(f, format="mp3")
        out = subprocess.Popen(['songrec', 'audio-file-to-recognized-song',
                            filename], stdout=subprocess.PIPE, text=True)
        (line, _) = out.communicate()
        if debug:
            with open(os.path.join(tempfile.gettempdir(), "songrec%d.json" % i), 'w') as fo:
                fo.write(line)
        data = json.loads(line)

        # Jaykar: Dior
        intro_subtitle = 'Jaykar'
        intro_title = 'Dior'
        intro_length = 100000
        if secure_lookup(data, 'track', 'subtitle') == intro_subtitle and secure_lookup(data, 'track', 'title') == intro_title:
            logging.info('Found intro in segment %d', i)
            if segment[1] - segment[0] > intro_length:
                logging.info('Missed end of intro segment. Re-detecting with shorter silence.')
                segment_audio = audio[segment[0]:segment[1]]
                subsegments = detect_segments(segment_audio, 750, seek_step=50)
                if subsegments[0][1] - subsegments[0][0] > intro_length:
                    logging.info('Still missed end of intro segment. Hard cutting after known intro length.')
                    segments.insert(i + 1, [segment[0] + intro_length, segment[1]])
                    segment[1] = segment[0] + intro_length
                else:
                    segments.insert(i + 1, [segment[0] + subsegments[1][0], segment[1]])
                    segment[1] = segment[0] + subsegments[0][1]
            return i

    logging.error("Can't find intro segment!")
    return -1


def _add_audio(existing, new):
    if existing is None:
        return new
    return existing + new

def normalize_segments(audio, segments):
    logging.info('Normalizing %d segments', len(segments))
    resultAudio = None
    i = -1
    while i < len(segments) - 1:
        i += 1
        (kind, start, stop) = segments[i]
        start = start * 1000
        stop = stop * 1000
        if kind == 'noEnergy' or kind == 'noise':
            resultAudio = _add_audio(resultAudio, audio[start:stop])
            continue
        j = i
        for j in range(i+1, len(segments)):
            (nextkind, _, _) = segments[j]
            if nextkind == 'noEnergy' or nextkind == 'noise':
                continue
            if nextkind != kind:
                break
        (nextkind, nextstart, nextstop) = segments[j - 1]
        nextstart = nextstart * 1000
        nextstop = nextstop * 1000
        logging.info('    Normalizing segments %d-%d (%s, %ds-%ds, duration: %ds)',
                    i, j - 1, kind, start / 1000, nextstop/ 1000, (stop - start) / 1000)
        audioseg = audio[start:nextstop]
        i = j - 1
        normalized = effects.normalize(audioseg)
        resultAudio = _add_audio(resultAudio, normalized)
    return resultAudio


def get_info(services, date):
    service = secure_lookup(services, date)
    title = secure_lookup(service, 'name', default='Gottesdienst')
    return { 'title': title,
             'announce': secure_lookup(service, 'announce', default=title),
             'artist': secure_lookup(service, 'artist', default='Rainer Heuschneider'),
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
    return filename


def read_config():
    tempdir = tempfile.gettempdir()
    config = configparser.ConfigParser()
    config.read_string("""
    [Paths]
    InputPath=%s
    OutputPath=%s
    Services=
    [Upload]
    User=
    Password=
    Server=
    PhoneServer=
    Key=
    """ % (tempdir, tempdir))
    config.read(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'autocut.config'))
    return config


def find_input_file(dir):
    # First try if there is a file with the current date in name
    today = datetime.datetime.now()
    files = glob.glob(os.path.join(dir, '%04d-%02d-%02d*' % (today.year, today.month, today.day)))
    files.sort()
    if len(files) >= 1:
        # if there are multiple files with today's date, take the last one
        return files[len(files) - 1]
    # Otherwise sort by name and take the last one (which if the names start with the data is
    # the newest one)
    files = glob.glob(os.path.join(dir, '[0-9]*.*'))
    files.sort()
    if len(files) >= 1:
        return files[len(files) - 1]
    return ''


def convert_video_to_mp3(file):
    outfile = tempfile.NamedTemporaryFile(suffix='.mp3')
    outfilename = outfile.name
    outfile.close()
    subprocess.run(['ffmpeg', '-i', file, '-f', 'mp3', outfilename])
    return outfilename


def read_services(repo):
    if not repo:
        return {}
    logging.info('Getting Gottesdienste metadata')
    scriptDir = os.path.dirname(os.path.realpath(__file__))
    dir = 'Gottesdienste'
    if os.path.exists(dir):
        subprocess.run(['git', 'pull', 'origin'], cwd=os.path.join(scriptDir, dir))
    else:
        subprocess.run(['git', 'clone', repo, dir], cwd=scriptDir)
    yml_file = os.path.join(scriptDir, dir, 'Gottesdienst.yml')
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
        f.write('Hallo, guten Tag! Sie hören den %s vom %d. %s %04d.' % (info['announce'], info['date'].day, months[info['date'].month], info['date'].year))
    return filename


def upload_to_website(config, file, year):
    logging.info('Uploading to website')
    subprocess.run(['ncftpput', '-u', config['Upload']['User'], '-p', config['Upload']['Password'], config['Upload']['Server'], '/Predigten/%s/' % year, file])


def upload_to_phoneserver(config, file):
    logging.info('Uploading to phone server')
    subprocess.run(['bash', '-c', '%s %s %s' % (os.path.join(os.path.dirname(os.path.realpath(__file__)), 'upload-to-phone.sh'), file.replace('(', '\\(').replace(')', '\\)'), config['Upload']['PhoneServer'])])


def upload_announcement(config, file):
    logging.info('Uploading to announcement')
    subprocess.run(['bash', '-c', '%s %s %s %s' % (os.path.join(os.path.dirname(os.path.realpath(__file__)), 'upload-announcement.sh'), file.replace('(', '\\(').replace(')', '\\)'), config['Upload']['Key'], config['Upload']['PhoneServer'])])


def cleanup(intermediate, announcement):
    logging.info('Cleanup')
    os.remove(intermediate)
    os.remove(announcement)


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

    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true', help='debug')
    parser.add_argument('--no-preconvert', action='store_true', help='don\'t do conversion to mp3 as first step')
    parser.add_argument('--no-upload', action='store_true', help='don\'t upload to servers')
    parser.add_argument('--no-intro-detection', action='store_true', help='don\'t try to detect intro. Instead use entire file.')

    args = parser.parse_args()
    if args.debug:
        debug = True
    else:
        debug = False

    config = read_config()

    services = read_services(config['Paths']['Services'])

    input_file = find_input_file(config['Paths']['InputPath'])
    if not input_file:
        input_file = os.path.join(config['Paths']['InputPath'], 'Godi.mp4')

    date = extract_date_from_filename(input_file)
    if args.no_preconvert:
        audio_file = input_file
    else:
        audio_file = convert_video_to_mp3(input_file)
    myAudio = load_audio(audio_file)

    segments = detect_segments(myAudio[0:len(myAudio)/2])

    if args.no_intro_detection:
        introIndex = -1
    else:
        introIndex = get_index_of_intro_segment(myAudio, segments)
        if introIndex < 0:
            input('Press Enter…')
            exit(1)
        segments = detect_detailed_segments(audio_file, segments[introIndex][1])

    resultAudio = normalize_segments(myAudio, segments)

    info = get_info(services, date)
    resultFile = export_result(resultAudio, config['Paths']['OutputPath'], info)
    announcement = save_announcement_file(info)

    if not args.no_upload:
        upload_to_website(config, resultFile, info['year'])
        upload_to_phoneserver(config, resultFile)
        upload_announcement(config, announcement)

    cleanup(audio_file, announcement)

    logging.info('AUTOCUT FINISHED!')
    input('Press Enter…')
