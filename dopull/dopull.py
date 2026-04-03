#!/usr/bin/env python3
#-*- coding: utf-8 -*-
"""Process .txt/.json trigger files and run updatehosts.py for each eBook."""

import atexit
import datetime as dt
import logging
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    import pwd
except ImportError:
    pwd = None

VERSION = "2026.04.02"

SCRIPT_DIR = Path(__file__).resolve().parent

# Parent directory of where to look for files to push out.
PUSHDIR = Path(os.getenv("PUSHDIR", "/home/push"))
# Where to move files after uploading them.
DONE = Path(os.getenv("DONE", "/home/DONE"))
# Output file.
OUTFILE = Path(os.getenv("OUTFILE", str(Path("/tmp") / str(os.getpid()))))
# Last run log.
LASTRUNFILE = Path(os.getenv("LASTRUNFILE", "/home/htdocs/dopull/logs/lastrun.txt"))
LOGFILE = Path(os.getenv("LOGFILE", "/home/htdocs/dopull/logs/dopull.log"))
# Lock file to prevent multiple dopulls running at the same time.
PULLRUNNING = Path(os.getenv("PULLRUNNING", str(SCRIPT_DIR / "/home/htdocs/dopull/.dopull-running")))
# Trigger directory for JSON processing on ibiblio (kept for compatibility with shell config).
IBIBLIO = "gutenberg.login.ibiblio.org"
IBIBLIO_JSON_DIR = Path(os.getenv("IBIBLIO_JSON_DIR", "/public/vhost/g/gutenberg/private/logs/json"))
# Email address to send trouble reports to.
BOSS = os.getenv("BOSS", "pterodactyl@fastmail.com")
LOGGER = logging.getLogger("dopull")


def setup_logging() -> None:
    """Configure logging output to LOGFILE, with stderr fallback."""
    LOGGER.setLevel(logging.INFO)
    LOGGER.handlers.clear()
    LOGGER.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    try:
        LOGFILE.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(LOGFILE, encoding="utf-8")
    except Exception:
        handler = logging.StreamHandler(sys.stderr)

    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)


def get_file_owner(path: Path) -> str:
    """Return the file owner name when available, otherwise fall back to the uid."""
    stat_info = path.stat()
    uid = stat_info.st_uid
    if pwd is None:
        return str(uid)

    getpwuid = getattr(pwd, "getpwuid", None)
    if getpwuid is None:
        return str(uid)

    return getpwuid(uid).pw_name


def append_out(message: str) -> None:
    """Append a line to the output file, creating parent folders as needed."""
    with OUTFILE.open("a", encoding="utf-8") as fh:
        fh.write(f"{message}\n")
    if LOGGER.handlers:
        LOGGER.info(message)


def cleanup(*_args: object) -> None:
    """Remove lock file on exit."""
    try:
        PULLRUNNING.unlink(missing_ok=True)
    except Exception:
        pass
    if LOGGER.handlers:
        LOGGER.info("Cleanup complete, lock removed")


def acquire_lock() -> None:
    """Acquire singleton lock for this process."""
    if PULLRUNNING.exists():
        # Notify that another dopull is active and exit.
        print(f"dopull postponed at {dt.datetime.now().isoformat(sep=' ', timespec='seconds')}")
        sys.exit(0)

    PULLRUNNING.write_text(f"{dt.datetime.now().isoformat()}\n", encoding="utf-8")
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)


def run_updatehosts(book_number: str) -> int:
    """Run updatehosts.py for a single eBook and append output to OUTFILE."""
    cmd = [sys.executable, str(SCRIPT_DIR / "updatehosts.py"), book_number]
    LOGGER.info(f"Running command: {' '.join(cmd)}")

    try:
        with OUTFILE.open("a", encoding="utf-8") as fh:
            proc = subprocess.run(
                cmd,
                cwd=str(SCRIPT_DIR),
                stdout=fh,
                stderr=subprocess.STDOUT,
                check=True,
            )
        return proc.returncode
    except subprocess.CalledProcessError as e:
        LOGGER.error(f"Command failed with return code {e.returncode}: {e}")
        return e.returncode

def send_email(subject: str, recipient: str, body: str) -> None:
    """Send an email using smtplib."""
    try:
        msg = MIMEMultipart()
        msg['From'] = 'gbnewby@pglaf.org'
        msg['To'] = recipient
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('localhost') as server:  # Replace 'localhost' with your SMTP server
            server.send_message(msg)
        LOGGER.info(f"Email sent to {recipient} with subject: {subject}")
    except Exception as e:
        LOGGER.error(f"Failed to send email to {recipient}: {e}")

def main() -> int:
    """ Main function to process trigger files and update hosts.
    • For each trigger file found in "push" directory,
        ◦ Get owner of file (user)
        ◦ Call updatehosts.py to create/update book on hosts, and trigger ibiblio update.
        ◦ If file is .json, trigger ebook indexing by copying it to the ibiblio JSON dir.
        ◦ Move file to DONE archive
        ◦ Send success/fail email to user
    """

    # Mark the start of this run and acquire lock.
    setup_logging()
    LOGGER.info("Starting dopull version %s", VERSION)
    LASTRUNFILE.write_text(f"{dt.datetime.now().isoformat()}\n", encoding="utf-8")
    acquire_lock()

    # Ensure DONE directory exists.
    DONE.mkdir(parents=True, exist_ok=True)

    # Find trigger files, both .txt and .json.
    trig_files = sorted(PUSHDIR.glob("*.txt")) + sorted(PUSHDIR.glob("*.json"))
    if not trig_files:
        append_out("No files found, exiting.")
        return 0

    bombed = False
    for trigger_file in trig_files:
        filename = trigger_file.name
        append_out(f"Processing file: {filename}")

        # Get owner of file (user).
        user = BOSS
        try:
            user = get_file_owner(trigger_file)
            append_out(f"Owner of file: {user}")
        except Exception as e:
            append_out(f"Failed to get owner of file: {e}; falling back to {user}")

        # Extract book number from filename (assuming format like "12345.txt" or "12345.json").
        book_number = trigger_file.stem
        if not book_number.isdigit():
            append_out(f"Skipping invalid trigger file (non-numeric book number): {filename}")
            bombed = True
            continue

        rc = run_updatehosts(book_number)
        if rc != 0:
            append_out(f"Got {rc} exit status, this file did not go!")
            bombed = True
            continue

        append_out("Success updating mirrors!\n")

        if not bombed:
            if trigger_file.suffix.lower() == ".json":
                try:
                    dest = f"{IBIBLIO}:{IBIBLIO_JSON_DIR}/{filename}"
                    subprocess.run(
                        ["scp", str(trigger_file), dest],
                        check=True,
                    )
                    append_out(f"Copied {filename} to ibiblio to trigger ebook indexing.")
                except Exception as e:
                    append_out(f"Failed to copy {filename} to {IBIBLIO_JSON_DIR}: {e}")
                    bombed = True
                    continue

            # Move the trigger file to the DONE directory.
            append_out(f"Moving {filename} to DONE directory")
            shutil.move(str(trigger_file), str(DONE / filename))

        result = "success" if not bombed else "failure"
        subject = f"{filename} processed {result}"
        # Send email to user notifying of success/failure.
        try:
            with OUTFILE.open("r", encoding="utf-8") as fh:
                log_content = fh.read()
            send_email(subject, user, log_content)
            OUTFILE.unlink(missing_ok=True)
        except Exception as e:
            append_out(f"Failed to send email to {user}: {e}")

    append_out("")
    return 1 if bombed else 0


if __name__ == "__main__":
    raise SystemExit(main())
