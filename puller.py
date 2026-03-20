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


def scan_dopull_log():
    """ 
    Scan the dopull log directory for new files.
    """
    for filename in sorted(os.listdir(DOPULL_LOG_DIR)):
        mode = os.stat(os.path.join(DOPULL_LOG_DIR, filename))[stat.ST_MODE]
        # skip directories JIC
        if stat.S_ISDIR(mode):
            continue

        ebook_num = 0
        m = re.match(r'^(\d+)\.zip\.trig$', filename)
        if m:
            ebook_num = int(m.group(1))
            logging.info(ebook_num)
            origin = f'{UPSTREAM_REPO_DIR}{ebook_num}.git/'
            target_path = os.path.join(FILES, str(ebook_num))
            logging.info(f'origin: {origin}, target_path: {target_path}')
             
            if update_folder(origin, target_path):
                shutil.move(os.path.join(DOPULL_LOG_DIR, filename),
                             os.path.join(DOPUSH_LOG_DIR, filename))
            else:
                logging.error(f'failed to update {ebook_num}')
    return

def main():
    sys.exit(scan_dopull_log())

if __name__ == '__main__':
    main()
