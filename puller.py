#!/usr/bin/env python3
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

Puller.py

Copyright 2025 by Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

Use git to pull files from an upstream repo into the corresponding folder in the FILES directory

- Puller.py looks for files named [number].zip.trig in the dopull "log" directory. If it finds
  one, it uses utils.gitpull to sync the repo with the FILES/[number] directory.
- When finished, the .trig files are moved to the dopush "log" directory (triggering FileInfo.py so
  that it can index and process the files, as if pglaf-dopush (same triggering as present))

"""
import logging
import os
import re
import shutil
import stat
import sys


# Configure logging
logging.basicConfig(filename='puller.log', level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from gitpull import update_folder

PUBLIC  = os.getenv ('PUBLIC')  or ''

# This is where ibiblio source files for books reside:
FILES = os.path.join(PUBLIC, 'files/')

PRIVATE = os.getenv('PRIVATE') or ''
UPSTREAM_REPO_DIR = os.getenv('UPSTREAM_REPO_DIR') or 'https://github.com/gutenbergbooks/'

# These are where .zip.trig files go on ibiblio :
DOPULL_LOG_DIR = os.path.join(PRIVATE, 'logs', 'dopull')
DOPUSH_LOG_DIR = os.path.join(PRIVATE, 'logs', 'dopush')
JSON_LOG_DIR = os.path.join(PRIVATE, 'logs', 'json')


def scan_dopull_log():
    """
    Scan DOPULL_LOG_DIR for new files.
    Note: this does 3 things:
    1. For all trigger files, it pulls the latest files from the upstream repo into the FILES directory.
    2. Copies .json files to JSON_LOG_DIR for database processing, and renames them as .info.txt trigger files.
    3. Copies .zip.trig (all) files to DOPUSH_LOG_DIR for database updates.
    Both directories are processed by FileInfo.py. In the future, it should be updated to do the appropriate
    processing for each file type, but for now this is a simple way to get the files where they need to go
    without needing to change FileInfo.py.
    """
    for filename in sorted(os.listdir(DOPULL_LOG_DIR)):
        mode = os.stat(os.path.join(DOPULL_LOG_DIR, filename))[stat.ST_MODE]
        # skip directories JIC
        if stat.S_ISDIR(mode):
            continue

        ebook_num = 0
        m = re.match(r'^(\d+)\.(zip\.trig|json)$', filename)
        if m:
            ebook_num = int(m.group(1))
            logging.info(ebook_num)
            origin = f'{UPSTREAM_REPO_DIR}{ebook_num}.git/'
            target_path = os.path.join(FILES, str(ebook_num))
            logging.info(f'origin: {origin}, target_path: {target_path}')

            # Get the latest files from the upstream repo
            if not update_folder(origin, target_path):
                logging.error(f'failed to get files for {ebook_num}')
                continue

            try:
                if filename.endswith('.json'):
                    # For .json files, copy them to the JSON_LOG_DIR to add to the database
                    shutil.copy(os.path.join(DOPULL_LOG_DIR, filename),
                                 os.path.join(JSON_LOG_DIR, filename))
                    logging.info(f'copied {filename} to JSON log directory for processing.')
                    # Rename it as a trigger file
                    newfilename = os.path.splitext(filename)[0] + '.info.txt'
                    os.rename(os.path.join(DOPULL_LOG_DIR, filename),
                            os.path.join(DOPULL_LOG_DIR, newfilename))
                    filename = newfilename

                # Move all files to the DOPUSH_LOG_DIR to trigger updating
                shutil.move(os.path.join(DOPULL_LOG_DIR, filename),
                                 os.path.join(DOPUSH_LOG_DIR, filename))
            except Exception as e:
                logging.error(f'failed to trigger update for {ebook_num}: {e}')

    return

def main():
    sys.exit(scan_dopull_log())

if __name__ == '__main__':
    main()
