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
from time import sleep, time_ns
import time
import yaml


intro_length = 100000


def convert_milliseconds_to_readable(millseconds):
    seconds = (millseconds/1000) % 60
    minutes = int((millseconds/(1000*60)) % 60)
    hours = int((millseconds/(1000*60*60)) % 24)

    return f'{hours:02}:{minutes:02}:{seconds:04.1f}'


def secure_lookup(data, key1, key2=None, default=None):
    """
    Return data[key1][key2] while dealing with data being None or key1
    or key2 not existing
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
    return silence.detect_nonsilent(audio, min_silence_len=silence_len,
                                    silence_thresh=-50, seek_step=seek_step)


def detect_detailed_segments(audio_file, startMilliSeconds):
    logging.info('Detecting detailed segments')
    segmenter = Segmenter()
    return segmenter(audio_file, start_sec=startMilliSeconds / 1000)


def call_songrec(filename, attempt):
    max_attempts = 3
    if attempt > max_attempts:
        # No success in 3 attempts - give up
        logging.info(f'        No success in {max_attempts} attempts - giving up')
        return ''
    if attempt > 0:
        # Waiting for 25s seems to work
        logging.info(f'        Retry again in 25 s ({attempt}. attempt)')
        sleep(25)

    out = subprocess.Popen(['songrec', 'audio-file-to-recognized-song',
                            filename], stdout=subprocess.PIPE, text=True)
    (line, _) = out.communicate()
    if not line or out.returncode != 0:
        if out.returncode != 0:
            return call_songrec(filename, attempt + 1)
        return ''
    return line


def check_segment_for_intro(audio, start_ms, end_ms, timestamp_ns,
                            retry_ns, debug_suffix):
    filename = os.path.join(tempfile.gettempdir(), "segment.mp3")
    if debug:
        filename = os.path.join(
            tempfile.gettempdir(), f'segment{debug_suffix}.mp3')
    with open(filename, "wb") as f:
        audio[start_ms:end_ms].export(f, format="mp3")
    time_now_ns = time_ns()
    if time_now_ns < timestamp_ns + retry_ns:
        # Make sure that we don't try before the retry_ns that
        # the previous call to songrec returned from shazam
        to_wait_s = (timestamp_ns + retry_ns - time_now_ns) / 1000000000
        logging.info('        Waiting %f s', to_wait_s)
        sleep(to_wait_s)
    line = call_songrec(filename, 0)
    if not line:
        logging.warning(f'No output from songrec for segment {debug_suffix}')
        return (False, end_ms, timestamp_ns, retry_ns)
    if debug:
        with open(os.path.join(tempfile.gettempdir(),
                               f'songrec{debug_suffix}.json'), 'w') as fo:
            fo.write(line)
    data = json.loads(line)

    # Jaykar: Dior
    intro_subtitle = 'Jaykar'
    intro_title = 'Dior'
    if secure_lookup(data, 'track', 'subtitle') == intro_subtitle and secure_lookup(data, 'track', 'title') == intro_title:
        logging.info(f'Found intro in segment {debug_suffix}')
        if end_ms - start_ms > intro_length:
            logging.info('Missed end of intro segment. Re-detecting with '
                         'shorter silence.')
            segment_audio = audio[start_ms:end_ms]
            subsegments = detect_segments(segment_audio, 750,
                                          seek_step=50)
            if subsegments[0][1] - subsegments[0][0] > intro_length:
                logging.info('Still missed end of intro segment. Hard '
                             'cutting after known intro length.')
                end_ms = start_ms + intro_length
            else:
                end_ms = start_ms + subsegments[0][1]
        return (True, end_ms, timestamp_ns, retry_ns)
    retry_ms = secure_lookup(data, 'retryms')
    if retry_ms:
        retry_ns = retry_ms * 1000000
    return (False, end_ms, timestamp_ns, retry_ns)


def get_end_of_intro_segment(audio, segments):
    logging.info('Finding intro segment (in %d segments)', len(segments))
    try:
        i = -1
        timestamp_ns = 0
        retry_ns = 0
        for segment in segments:
            if args.end_intro and segment[0] > int(args.end_intro) * 60 * 1000:
                logging.info('    Intro segment not found in '
                             f'{args.end_intro} minutes; skipping rest')
                return -1
            i = i + 1
            logging.info(
                f'    Examining segment {i} ('
                f'{convert_milliseconds_to_readable(segment[0])} - '
                f'{convert_milliseconds_to_readable(segment[1])})')

            (found, end_ms, timestamp_ns, retry_ns) = check_segment_for_intro(audio, segment[0], segment[1], timestamp_ns, retry_ns, i)
            if not found:
                continue
            return end_ms
    except Exception as e:
        logging.warning('Got exception trying to find intro segment: %s', e)

    logging.error("Can't find intro segment!")
    return -1


def get_end_of_intro_segment_in_slots(audio, segments):
    slot_len = 20000  # 20s
    logging.info('Finding intro segment in slots (in %d segments)',
                 len(segments))
    try:
        i = -1
        timestamp_ns = 0
        retry_ns = 0
        found = False
        for segment in segments:
            if args.end_intro and segment[0] > int(args.end_intro) * 60 * 1000:
                logging.info(
                    f'    Intro segment not found in {args.end_intro} '
                    'minutes; skipping rest')
                return -1
            i = i + 1
            for j in range(segment[0], segment[1], slot_len):
                logging.info(
                    f'    Examining {int(slot_len / 1000)}s slot starting at '
                    f'{convert_milliseconds_to_readable(j)} in segment {i}')

                (found, end_ms, timestamp_ns, retry_ns) = check_segment_for_intro(
                    audio, j, j + slot_len, timestamp_ns, retry_ns, f'{i}-{j}')
                if not found:
                    continue
                # Now we know a segment that contains the intro, but we still
                # don't know the end of the intro. Try and find that now.
                logging.info('Found intro segment. Now looking for end of intro.')
                segment_end = j + slot_len
                segment_audio = audio[segment_end:segment_end + intro_length]
                subsegments = detect_segments(segment_audio, 250)
                end_ms = end_ms + subsegments[0][1]
                logging.info(f'    Calculated end of intro at {convert_milliseconds_to_readable(end_ms)}')
                return end_ms
    except Exception as e:
        logging.warning('Got exception trying to find intro segment: %s', e)

    logging.error("Can't find intro segment!")
    return -1


def find_start_after_intro(audio, silence_len=1000):
    introSegments = detect_segments(audio[:len(audio)/2], silence_len)

    if args.no_intro_detection:
        end_of_intro_ms = 0
        return 0
    end_of_intro_ms = get_end_of_intro_segment(audio, introSegments)
    if end_of_intro_ms >= 0:
        return end_of_intro_ms
    # We didn't find an intro segment in the regular segments. Now try
    # again with 20s long segments
    end_of_intro_ms = get_end_of_intro_segment_in_slots(
        audio, introSegments)
    if end_of_intro_ms >= 0:
        return end_of_intro_ms
    return -1


def _add_audio(existing, new):
    return existing + new if existing is not None else new


def normalize_segments(audio, segments):
    logging.info('Normalizing %d segments', len(segments))
    resultAudio = None
    i = -1
    while i < len(segments) - 1:
        i += 1
        (kind, start, stop) = segments[i]
        start = start * 1000
        stop = stop * 1000
        if kind in ['noEnergy', 'noise']:
            resultAudio = _add_audio(resultAudio, audio[start:stop])
            continue
        j = i
        for j in range(i+1, len(segments)):
            (nextkind, _, _) = segments[j]
            if nextkind in ['noEnergy', 'noise']:
                continue
            if nextkind != kind:
                break
        if j >= len(segments) - 1:
            # last segment
            (nextkind, nextstart, nextstop) = segments[j]
        else:
            (nextkind, nextstart, nextstop) = segments[j - 1]
        nextstart = nextstart * 1000
        nextstop = nextstop * 1000
        logging.info('    Normalizing segments %d-%d (%s, %s-%s, '
                     'duration: %ds)', i, j - 1, kind,
                     convert_milliseconds_to_readable(start),
                     convert_milliseconds_to_readable(nextstop),
                     (nextstop - start) / 1000)
        audioseg = audio[start:nextstop]
        i = j - 1
        normalized = effects.normalize(audioseg)
        resultAudio = _add_audio(resultAudio, normalized)
    return resultAudio


def get_info(services, date):
    service = secure_lookup(services, date)
    title = secure_lookup(service, 'name', default='Gottesdienst')
    return {'title': title,
            'announce': secure_lookup(service, 'announce', default=title),
            'artist': secure_lookup(service, 'artist',
                                    default='Rainer Heuschneider'),
            'album': 'Ev. Kirchengemeinde Niederdresselndorf',
            'trackno': '%04d%02d%02d' % (date.year, date.month, date.day),
            'year': '%04d' % date.year,
            'isodate': '%04d-%02d-%02d' % (date.year, date.month, date.day),
            'date': date,
            'start': secure_lookup(service, 'start', default='10:00')
            }


def export_result(audio, outputdir, info):
    logging.info('Exporting result')
    filename = os.path.join(
        outputdir,
        f"{info['isodate']}_{info['title']}_{info['album']}.mp3".replace(
            ' ', '_'
        ),
    )
    with open(filename, 'wb') as f:
        metadata = {'title': info['title'], 'track': info['trackno'],
                    'artist': info['artist'],
                    'album': info['album'], 'year': info['year'],
                    'genre': 'Gottesdienst'}
        audio.export(f, format='mp3', bitrate='128k', tags=metadata,
                     parameters=['-minrate', '128k', '-maxrate', '128k'])
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
    config.read(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             'autocut.config'))
    return config


def find_input_file(dir):
    # First try if there is a file with the current date in name
    today = datetime.datetime.now()
    files = glob.glob(os.path.join(dir, '%04d-%02d-%02d*' % (today.year,
                                                             today.month,
                                                             today.day)))
    files.sort()
    if files:
        # if there are multiple files with today's date, take the last one
        return files[-1]
    # Otherwise sort by name and take the last one (which if the names
    # start with the data is the newest one)
    files = glob.glob(os.path.join(dir, '[0-9]*.*'))
    files.sort()
    return files[-1] if files else ''


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
    inputDir = 'Gottesdienste'
    if os.path.exists(inputDir):
        subprocess.run(['git', 'pull', 'origin'], cwd=os.path.join(scriptDir,
                                                                   inputDir))
    else:
        subprocess.run(['git', 'clone', repo, inputDir], cwd=scriptDir)
    yml_file = os.path.join(scriptDir, inputDir, 'Gottesdienst.yml')
    if not os.path.exists(yml_file):
        logging.warning("Can't find Gottesdienst.yml")
        return {}
    with open(yml_file, 'r') as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def extract_date_from_filename(filename):
    match = re.search('^(\\d+)-(\\d+)-(\\d+) (\\d+)-(\\d+)-(\\d+)',
                      os.path.basename(filename))
    if match:
        parts = match.groups()
        if parts and len(parts) == 6:
            return datetime.datetime.fromisoformat(f'{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}T{int(parts[3]):02d}:{int(parts[4]):02d}:{int(parts[5]):02d}')
    match = re.search('^(\\d+)-(\\d+)-(\\d+)', os.path.basename(filename))
    if match:
        parts = match.groups()
        if parts and len(parts) == 3:
            return datetime.datetime.fromisoformat(f'{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}')
    match = re.search('^(\\d+)\\.(\\d+)\\.(\\d+)', os.path.basename(filename))
    if match:
        parts = match.groups()
        if not parts or len(parts) < 3:
            return datetime.date.today()
        return datetime.datetime.fromisoformat(f'{int(parts[2]):04d}-{int(parts[1]):02d}-{int(parts[0]):02d}')
    return datetime.datetime.fromisoformat(datetime.date.today().isoformat())


def save_announcement_file(info):
    months = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
              'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
    logging.info('Saving announcement file')
    filename = os.path.join(tempfile.gettempdir(), "Announce.txt")
    with open(filename, 'w') as f:
        f.write('Hallo, guten Tag! Sie hören den %s vom %d. %s %04d.' %
                (info['announce'], info['date'].day,
                 months[info['date'].month], info['date'].year))
    return filename


def upload_to_website(config, file, year):
    logging.info('Uploading to website')
    subprocess.run(
        [
            'ncftpput',
            '-m',  # Create remote directory before copying
            '-u', config['Upload']['User'],
            '-p', config['Upload']['Password'],
            config['Upload']['Server'],
            f'/Predigten/{year}/',
            file,
        ]
    )


def upload_to_phoneserver(config, file):
    logging.info('Uploading to phone server')
    subprocess.run(['bash', '-c', '%s %s %s' % (os.path.join(os.path.dirname(
        os.path.realpath(__file__)), 'upload-to-phone.sh'), file.replace(
            '(', '\\(').replace(')', '\\)'), config['Upload']['PhoneServer'])])


def upload_announcement(config, file):
    logging.info('Uploading to announcement')
    subprocess.run(['bash', '-c', '%s %s %s %s' % (os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'upload-announcement.sh'), file.replace('(', '\\(').replace(
            ')', '\\)'), config['Upload']['Key'], config[
                'Upload']['PhoneServer'])])


def cleanup(intermediate, announcement):
    logging.info('Cleanup')
    os.remove(intermediate)
    os.remove(announcement)


def get_creation_time(input_file):
    ctime = time.localtime(os.path.getctime(input_file))
    return datetime.datetime(ctime.tm_year, ctime.tm_mon,
                             ctime.tm_mday, ctime.tm_hour,
                             ctime.tm_min, ctime.tm_sec)


def get_start_in_audio(input_file, info, file_time):
    service_start_time = datetime.time.fromisoformat(info['start'])
    start_time = file_time.replace(
        hour=service_start_time.hour,
        minute=service_start_time.minute,
        second=0)
    # return 2 minutes before start_time
    early = datetime.timedelta(minutes=2)
    if file_time + early > start_time:
        return 0
    diff = start_time - file_time - early
    return diff.seconds * 1000


def process_audio(input_file, audio_file, services, use_start_time):
    date = extract_date_from_filename(input_file)
    logging.info(f'Found date {date.year:04}-{date.month:02}-{date.day:02}')
    info = get_info(services, date)

    myAudio = load_audio(audio_file)

    if use_start_time:
        start_in_audio_ms = get_start_in_audio(input_file, info, date)
        logging.info(f'Starting to look for intro after {start_in_audio_ms/1000}ms')
        myAudio = myAudio[start_in_audio_ms:]

    startMilliseconds = find_start_after_intro(myAudio)
    if startMilliseconds < 0:
        if use_start_time:
            # try again from beginning
            process_audio(input_file, audio_file, services, False)
        else:
            if not args.no_upload:
                # If we can't find intro we upload the full temp file to the website
                upload_to_website(config, audio_file, info['year'])
            input('Press Enter...')
            exit(1)

    segments = detect_detailed_segments(audio_file, startMilliseconds)

    resultAudio = normalize_segments(myAudio, segments)

    resultFile = export_result(resultAudio, config['Paths']['OutputPath'],
                               info)
    announcement = save_announcement_file(info)

    if not args.no_upload:
        upload_to_website(config, resultFile, info['year'])
        upload_to_phoneserver(config, resultFile)
        upload_announcement(config, announcement)

    cleanup(audio_file, announcement)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(tempfile.gettempdir(),
                                             "autocut.log")),
            logging.StreamHandler()
        ]
    )
    logging.info('STARTING AUTOCUT')

    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true', help='debug')
    parser.add_argument('--no-preconvert', action='store_true',
                        help='don\'t do conversion to mp3 as first step')
    parser.add_argument('--no-upload', action='store_true',
                        help='don\'t upload to servers')
    parser.add_argument('--no-intro-detection', action='store_true',
                        help='don\'t try to detect intro. Instead use '
                        'entire file.')
    parser.add_argument('--end-intro', action='store',
                        help='stop intro detection x minutes')
    parser.add_argument('--autostart', action='store_true')

    args = parser.parse_args()
    debug = bool(args.debug)
    config = read_config()

    from pydub import AudioSegment, effects, silence
    from inaSpeechSegmenter import Segmenter

    services = read_services(config['Paths']['Services'])

    input_file = find_input_file(config['Paths']['InputPath'])
    if input_file:
        date = extract_date_from_filename(input_file)
        today = datetime.date.today()
        if (date.year != today.year or date.month != today.month or \
                date.day != today.day) and args.autostart:
            # If automatically started we don't want to process if input_file
            # is not from today
            logging.info(
                'Skipping %s since it is not from today and we were autostarted',
                input_file)
            exit(1)
    else:
        if args.autostart:
            # If automatically started we don't want to process if
            # input_file is not from today
            logging.info(
                'Skipping %s since it is not from today and we were autostarted',
                input_file)
            exit(1)
        input_file = os.path.join(config['Paths']['InputPath'], 'Godi.mp4')

    if args.no_preconvert:
        audio_file = input_file
    else:
        audio_file = convert_video_to_mp3(input_file)

    try:
        process_audio(input_file, audio_file, services, True)
    except Exception as e:
        logging.warning('Got exception processing audio: %s', e)

    logging.info('AUTOCUT FINISHED!')
    input('Press Enter...')
