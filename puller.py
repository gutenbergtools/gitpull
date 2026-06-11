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
    2. Moves .json files to JSON_LOG_DIR for database processing, and creates an .info.txt trigger file.
    3. Moves .zip.trig files to DOPUSH_LOG_DIR for database updates.
    Both directories are processed by FileInfo.py. In the future, it should be updated to do the appropriate
    processing for each file type, but for now this is a simple way to get the files where they need to go
    without needing to change FileInfo.py.

    If both .zip.trig and .json files are present for the same ebook number:
    (Workflow creates a .json, file, then Errata Workbench creates a .zip.trig file)
    should be OK, the repo has all the changes, and we need the trigger file in any case.
    Repo pull will occur twice, but the second will have no changes, and this should be too rare to worry about.
    """
    for filename in sorted(os.listdir(DOPULL_LOG_DIR)):
        mode = os.stat(os.path.join(DOPULL_LOG_DIR, filename))[stat.ST_MODE]
        # skip directories JIC
        if stat.S_ISDIR(mode):
            continue

        ebook_num = 0
        m = re.match(r'^(\d+)\.(zip\.trig|json)$', filename)
        if m:
            ebook_num = m.group(1)
            if not ebook_num.isdigit():
                logging.error(f'Skipping invalid filename (non-numeric book number): {filename}')
                continue
            logging.info(ebook_num)
            origin = f'{UPSTREAM_REPO_DIR}{ebook_num}.git/'
            target_path = os.path.join(FILES, ebook_num)
            logging.info(f'origin: {origin}, target_path: {target_path}')

            # Get the latest files from the upstream repo
            if not update_folder(origin, target_path):
                logging.error(f'failed to get files for {ebook_num}')
                continue

            # Now trigger database/catalog update
            try:
                if filename.endswith('.json'):
                    # For .json files, move them to the JSON_LOG_DIR to add to the database
                    shutil.move(os.path.join(DOPULL_LOG_DIR, filename),
                                 os.path.join(JSON_LOG_DIR, filename))
                    logging.info(f'moved {filename} to JSON log directory for processing.')

                    # Create a corresponding .zip.trig trigger file
                    trigger_file = os.path.join(DOPULL_LOG_DIR, ebook_num + '.zip.trig')
                    if not os.path.exists(trigger_file):
                        with open(trigger_file, 'w') as file:
                            pass

                # Move file to the DOPUSH_LOG_DIR to trigger updating
                shutil.move(os.path.join(DOPULL_LOG_DIR, filename),
                                 os.path.join(DOPUSH_LOG_DIR, filename))
            except Exception as e:
                logging.error(f'failed to trigger update for {ebook_num}: {e}')

    return


def main():
    sys.exit(scan_dopull_log())

if __name__ == '__main__':
    main()
