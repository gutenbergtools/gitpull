#!/usr/bin/env python3
#-*- coding: utf-8 -*-
"""Process .txt/.json trigger files for each eBook."""

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

VERSION = "2026.06.09"

SCRIPT_DIR = Path(__file__).resolve().parent
# Parent directory of where to look for files to push out.
PUSHDIR = Path(os.getenv("PUSHDIR", "/home/push"))
# Where to move files after uploading them.
DONE = Path(os.getenv("DONE", "/home/DONE"))
# Output file.
OUTFILE = Path(os.getenv("OUTFILE", str(Path("/tmp") / str(os.getpid()))))
# Last run log.
LASTRUNFILE = Path(os.getenv("LASTRUNFILE", str(SCRIPT_DIR / "logs/lastrun.txt")))
LOGFILE = Path(os.getenv("LOGFILE", str(SCRIPT_DIR / "logs/dopull.log")))
# Lock file to prevent multiple dopulls running at the same time.
PULLRUNNING = Path(os.getenv("PULLRUNNING", str(SCRIPT_DIR / ".dopull-running")))
IBIBLIO = "gutenberg.login.ibiblio.org"
PRIVATE = os.getenv('PRIVATE') or ''
IBIBLIO_DOPULL_DIR = os.path.join(PRIVATE, 'logs', 'dopull')
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
    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
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
        print(f"dopull postponed at {dt.datetime.now().isoformat(sep=' ', timespec='seconds')}")
        sys.exit(0)
    PULLRUNNING.write_text(f"{dt.datetime.now().isoformat()}\n", encoding="utf-8")
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)


def send_email(subject: str, recipient: str, body: str) -> None:
    """Send an email using smtplib."""
    try:
        msg = MIMEMultipart()
        msg['From'] = 'pgww@lists.pglaf.org'
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('localhost') as server:  # Replace 'localhost' with your SMTP server
            server.send_message(msg)
        LOGGER.info(f"Email sent to {recipient} with subject: {subject}")
    except Exception as e:
        LOGGER.error(f"Failed to send email to {recipient}: {e}")


def main() -> int:
    """ Main function to process trigger files.
    • For each trigger file found in "push" directory,
        ◦ Get owner of file (user)
        ◦ Trigger ebook update by copying it to the ibiblio dopull dir.
        ◦ Move file to DONE archive
        ◦ Send success/fail email to user
    """
    # Default, process_trigger_file() will attempt to get the file owner
    user = BOSS

    def send_notification(filename: str, user: str, result: str) -> None:
        """Send email notification to the user about the processing result."""
        subject = f"{filename} processed {result}"
        try:
            with OUTFILE.open("r", encoding="utf-8") as fh:
                log_content = fh.read()
            send_email(subject, user, log_content)
        except Exception as e:
            append_out(f"Failed to send email to {user}: {e}")
        finally:
            # Keep notifications per-file; do not leak prior content into later runs.
            OUTFILE.unlink(missing_ok=True)

    def process_trigger_file(trigger_file: Path) -> str:
        """Process a single trigger file and return the result status.
        If anything fails, return failure, we will retry next time.
        """
        nonlocal user
        filename = trigger_file.name
        append_out(f"Processing file: {filename}")

        # Get owner of file (user).
        try:
            user = get_file_owner(trigger_file)
            append_out(f"Owner of file: {user}")
        except Exception as e:
            user = BOSS
            append_out(f"Failed to get owner of file: {e}; falling back to {user}")

        # Extract book number from filename.
        book_number = trigger_file.stem
        if not book_number.isdigit():
            append_out(f"Skipping invalid trigger file (non-numeric book number): {filename}")
            return "failure"

        # Trigger ibiblio update by copying the trigger file to the dopull directory.
        try:
            if not PRIVATE:
                append_out("PRIVATE is not set; cannot build ibiblio destination path.")
                return "failure"
            dest = f"{IBIBLIO}:{IBIBLIO_DOPULL_DIR}"
            subprocess.run(["scp", str(trigger_file), dest], check=True)
            append_out(f"Triggered processing of #{book_number} on ibiblio.")
        except Exception as e:
            append_out(f"Failed to trigger ibiblio update for {filename}: {e}")
            return "failure"

        # If we got to here, all is OK, move trigger file to the DONE directory,
        # otherwise, it will be retried on the next run.
        try:
            shutil.move(str(trigger_file), str(DONE / filename))
            append_out(f"Moved {filename} to DONE directory")
        except Exception as e:
            append_out(f"Failed to move {filename} to DONE directory: {e}")
            return "failure"

        return "success"

    # Mark the start of this run and acquire lock.
    acquire_lock()
    setup_logging()
    LOGGER.info("Starting dopull version %s", VERSION)

    # Ensure DONE directory exists.
    DONE.mkdir(parents=True, exist_ok=True)

    # Find trigger files, both .txt and .json.
    trig_files = sorted(PUSHDIR.glob("*.txt")) + sorted(PUSHDIR.glob("*.json"))
    if not trig_files:
        if LOGGER.handlers:
            LOGGER.info("No files found, exiting.")
        return 0

    had_failure = False
    for trigger_file in trig_files:
        # Clear output file, so we only capture logs relevant to this file's processing.
        OUTFILE.unlink(missing_ok=True)
        result = process_trigger_file(trigger_file)
        if result != "success":
            had_failure = True
        send_notification(trigger_file.name, user, result)

    return 1 if had_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
