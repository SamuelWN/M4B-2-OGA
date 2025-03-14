#!/usr/bin/env python3

# Converts m4b audio file to an opus oga + cue file
#
# Adapted from script by TheMetalCenter:
#   https://github.com/TheMetalCenter/m4b-mp3-chapters-from-cuesheets/blob/main/export-cue.py
#
# Usage:
#  m4b2oga.py <input>.m4b
#
# Requires:
#  ffmpeg-python


import argparse
import datetime
import logging
import os
import sys
import ffmpeg

try:
    from ffmpeg import probe as ffprobe
except ImportError:
    from ffmpeg import _probe
    ffprobe = _probe.probe



def m4b2opus(m4b_file):
    """
    Generate a Ogg Audio (.oga) file from the provided M4B audio file.

    Parameters:
    m4b_file (str): The path to the input M4B audio file.

    Returns:
    str: The path to the generated OGA audio file.
    """
    oga_file = os.path.splitext(m4b_file)[0] + '.oga'
    (
        ffmpeg
        .input(m4b_file)
        .output(oga_file,
                acodec='libopus', audio_bitrate='48k',
                map_metadata=0 #, loglevel='warning'
            )
        .overwrite_output()
        .run()
    )
    return oga_file


def get_chapters(m4b_file):
    """
    Retrieve the chapters from the specified m4b file.

    Parameters:
    m4b_file (str): The path to the m4b file.

    Returns:
    list: A list of chapters extracted from the m4b file.
    """
    return ffprobe(m4b_file, show_chapters=None)['chapters']



def book_info(file):
    """
    Extracts the performer and title information from an audio file using ffprobe.

    Parameters:
        file (str): The path to the audio file.

    Returns:
        tuple: A tuple containing the performer (str) and title (str) extracted from the audio file.
               If the performer cannot be extracted, an empty string is returned.
               If the title cannot be extracted, the basename of the audio file is used.
    """
    tags = ffprobe(file)['format']['tags']
    keys = list(tags.keys())
    keys_upper = list(map(str.upper, keys))

    title = "placeholder"

    try:
        performer=tags[keys[keys_upper.index('ARTIST')]]
    except ValueError:
        try:
            performer=tags[keys[keys_upper.index('PERFORMER')]]
        except ValueError:
            try:
                performer=str(tags['performer'])
            except ValueError:
                performer=''
    try:
        title=tags[keys[keys_upper.index('ALBUM')]]
    except ValueError:
        try:
            title=tags[keys[keys_upper.index('TITLE')]]
        except ValueError:
            title=os.path.splitext(os.path.basename(file))[0]
    return performer, title

def create_cue_sheet(names, track_times, timebases, start_time=datetime.timedelta(seconds=0)):
    """Yields the next cue sheet entry given the track names, times.

    Args:
        names: List of track names.
        track_times: List of timdeltas containing the track times.
        timebases: List of timebases per track
        performers: List of performers to associate with each cue entry.
        start_time: The initial time to start the first track at.

    The lengths of names and track times should be the same.
    """
    accumulated_time = start_time


    for track_index, (name, track_time, timebase) in enumerate(
            zip(names, track_times, timebases)):
        minutes = int(accumulated_time.total_seconds() / (timebase*60))
        seconds = int((int(accumulated_time.total_seconds() % (timebase*60))) / timebase)
        frames = int(float(float((int(accumulated_time.total_seconds() % (timebase*60))) / timebase) % 1) * 75)

        cue_sheet_entry = '''  TRACK {:02} AUDIO
    TITLE "{}"
    INDEX 01 {:02d}:{:02d}:{:02d}'''.format(track_index, name, minutes, seconds, frames)
        accumulated_time += track_time
        yield cue_sheet_entry

def extract_cover_art(m4b_file):
    """
    Extract the embedded cover art from the M4B file, if present.

    Parameters:
    m4b_file (str): The path to the input M4B audio file.

    Returns:
    str: The path to the extracted cover art file, or None if no cover art is present.
    """
    cover_art_file = os.path.splitext(m4b_file)[0] + '_cover.jpg'
    try:
        (
            ffmpeg
            .input(m4b_file)
            .output(cover_art_file, map='0:v', vframes=1)
            .overwrite_output()
            .run(quiet=True)
        )
        if os.path.isfile(cover_art_file):
            return cover_art_file
    except ffmpeg.Error as e:
        logging.warning(f"No cover art found or extraction failed for {m4b_file}: {e}")
    return None


def extract_description(m4b_file):
    """
    Extract the description metadata from the M4B file by checking multiple common fields.

    Parameters:
    m4b_file (str): The path to the input M4B audio file.

    Returns:
    str: The description metadata, or None if no relevant field is found.
    """
    try:
        metadata = ffprobe(m4b_file)['format']['tags']
        
        # List of fields to check (all lowercase for case-insensitive comparison)
        fields_to_check = [
            'description',  # Most common field
            'comment',      # Common alternative
            'title_more',  # Another common field
            'synopsis',    # Sometimes used
            'summary'       # Another possible field
        ]
        
        # Normalize metadata keys to lowercase for case-insensitive comparison
        metadata_lower = {k.lower(): v for k, v in metadata.items()}
        
        # Iterate through the fields and return the first non-empty value
        for field in fields_to_check:
            if field in metadata_lower and metadata_lower[field].strip():
                return metadata_lower[field].strip()
        
        # If no field is found, return None
        return None
    
    except Exception as e:
        logging.warning(f"Failed to extract description from {m4b_file}: {e}")
        return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Creates a cue sheet given a track list.')
    parser.add_argument('audio_file', nargs='+', type=argparse.FileType('r'),
                        default=sys.stdin,
                        help='The audio file corresponding to cue sheet this '
                        'script will generate. This file will be used to infer '
                        'its name for the cue sheet FILE attribute.')
    parser.add_argument('--debug', dest='log_level', default=logging.WARNING,
                        action='store_const', const=logging.DEBUG,
                        help='Print debug log statements.')
    args = parser.parse_args()
    logging.basicConfig(stream=sys.stderr, level=args.log_level)
    logger = logging.getLogger(__name__)

    for file in args.audio_file:
        performer, title = book_info(file.name)
        oga_file = os.path.splitext(file.name)[0] + '.oga'

        if not os.path.isfile(oga_file):
            oga_file = m4b2opus(file.name)

        # Extract cover art
        cover_art_file = extract_cover_art(file.name)
        if cover_art_file:
            logging.info(f"Cover art extracted to: {cover_art_file}")
        else:
            logging.info("No cover art found or extracted.")

        # Extract description and write to info.txt
        description = extract_description(file.name)
        if description:
            info_file = os.path.splitext(file.name)[0] + '_info.txt'
            with open(info_file, 'w') as f:
                f.write(description)
            logging.info(f"Description extracted to: {info_file}")
        else:
            logging.info("No description found or extracted.")


        track_times = []
        names = []
        performers = []
        timebases = []



        REPLACE_CUE=True
        CUE_PATH=os.path.splitext(oga_file)[0] + '.cue'

        audio_file_extension = os.path.splitext(oga_file)[1][1:].upper()
        FILE_LINE_OGA='FILE "{}" {}\n'.format(os.path.basename(oga_file), audio_file_extension)
        CUE_CONTENTS=''

        # If a `cue` file already exists and is associated with the M4B file: do not replace it
        if os.path.isfile(CUE_PATH):
            with open(CUE_PATH, 'r') as CUE_FILE:
                for line in CUE_FILE:
                    if line == FILE_LINE_OGA:
                        REPLACE_CUE = True
                        break
                    elif line.startswith('FILE '):
                        # Sometimes, the value does not perfectly match `M4B` file name 
                        #   (due to special characters, etc.)
                        REPLACE_CUE = False
                        continue
                    else:
                        CUE_CONTENTS+=line

            if not REPLACE_CUE:
                CUE_PATH=os.path.splitext(oga_file)[0] + '_oga.cue'

        if REPLACE_CUE:
            # Extract CUE info from file:
            for aChap in get_chapters(file.name):
                try:
                    names.append(aChap['tags']['title'])
                    performers.append(performer)
                    track_times.append(
                                    datetime.timedelta(
                                        seconds=(int(aChap['end']) - int(aChap['start']))
                                    )
                                )
                    timebase = int(aChap['time_base'].split('/')[1])
                    if timebase > 10000:
                        timebase=1000
                    timebases.append(timebase)
                except ValueError as v:
                   logger.error(v)

            CUE_CONTENTS=''.join(cue_entry for cue_entry in create_cue_sheet(
                            names, track_times, timebases
                        ))

        with open(CUE_PATH, 'w') as output_file:
            output_file.writelines('PERFORMER "{}"\n'.format(performer))
            output_file.writelines('TITLE "{}"\n'.format(title))

            output_file.writelines(FILE_LINE_OGA)
            output_file.writelines(CUE_CONTENTS)
