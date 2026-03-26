#!/usr/bin/env python3
"""
from gutenbergtools/pglaf-gitpull: Update a folder with the latest files from a Git repository

This tool clones or pulls the latest changes from a Git repository into a
specified target folder.
"""
import argparse
import os
import subprocess
import logging
import sys

VERSION = "2026.03.25"

def load_env_file(filepath=".env"):
    """
    Reads an .env file and sets environment variables.
    Expected format:    THEKEY=the_value
    """
    if not os.path.exists(filepath):
        # User could set them manually...
        return

    with open(filepath, "r") as file:
        for line in file:
            line = line.strip()
            # Skip empty lines, comments, invalid lines
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            # Strip blanks & quotes
            value = value.strip().strip('\'\"')
            os.environ[key] = value


# Load the variables from the.env file
load_env_file()

PRIVATE = os.getenv('PRIVATE') or ''
# These are the locations for the gitpull script on the hosts
IBIBLIO_BIN = os.getenv('IBIBLIO_BIN') or ''
MIRROR_BIN = os.getenv('MIRROR_BIN') or ''
# This is the destination directory for the eBooks on the hosts, typically something like '~/ftp/'
EBOOKS_DIR = os.getenv('EBOOKS_DIR') or ''

# Configure logging
logging.basicConfig(filename='updatehosts.log', level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ibiblio = "gutenberg.login.ibiblio.org"
mirrors = ["inferno.pglaf.org",
           "aleph.pglaf.org",
           "readingroo.ms"]

def run_python_script_via_ssh(host, script_path, script_args=None, timeout=60):
    """Run a Python script on a remote server via SSH."""
    if script_args is None:
        script_args = []

    remote_command = f"python3 {script_path}"
    try:
        logger.info(f"[START] Running Python script on {host}: {remote_command} {' '.join(script_args)}")
        output = run_ssh_command(host, remote_command, arguments=script_args, timeout=timeout)
        logger.info(f"[SUCCESS] Output from {host}: {output}")
        return output
    except Exception as e:
        logger.error(f"[ERROR] Failed to run Python script on {host}: {str(e)}")
        raise


def run_ssh_command(host, command, arguments=None, timeout=60):
    """Run a shell command on a remote host via SSH with optional arguments."""
    if arguments is None:
        arguments = []

    # Append arguments to the command
    full_command = f"{command} {' '.join(arguments)}"
    try:
        logger.info(f"[START] Running command on {host}: {full_command}")
        result = subprocess.run(
            ["ssh", host, full_command],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        logger.info(f"[SUCCESS] Command output from {host}: {result.stdout}")
        if result.stderr:
            logger.warning(f"[WARNING] Command stderr from {host}: {result.stderr}")
        return result.stdout
    except subprocess.TimeoutExpired:
        logger.error(f"[TIMEOUT] Command timed out after {timeout} seconds on {host}: {full_command}")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"[FAILURE] Command failed on {host}: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"[ERROR] Unexpected error while running command on {host}: {str(e)}")
        raise


def get_ebook_path(number):
    """Get PG directory path: 12345 --> 1/2/3/4/"""
    outdir = '/'.join(number) + '/'

    # Ditch the last digit to make the target subdirectory
    if len(outdir) == 2:  # Special case: Single digit filenames will prefix with '0/'
        outdir = '0/'
    else:
        where = outdir.rfind('/')
        if where != -1:
            outdir = outdir[:where - 1]  # It's always 1 digit
    return outdir


def update_gitpull_to_hosts():
    """
    Update the gitpull script on all hosts.
    Assumes the source script is named 'gitpull.py' and is located in the current directory.
    """
    if not os.path.exists('gitpull.py'):
        logger.error("gitpull.py script not found in the current directory.")
        print("gitpull.py script not found in the current directory.")
        return False
    if not IBIBLIO_BIN or not MIRROR_BIN:
        logger.error("IBIBLIO_BIN or MIRROR_BIN environment variable not set.")
        print("IBIBLIO_BIN or MIRROR_BIN environment variable not set.")
        return False
    for host in mirrors + [ibiblio]:
        logger.info(f"Updating gitpull.py script on {host}...")
        remote_target = IBIBLIO_BIN if host == ibiblio else MIRROR_BIN
        try:
            result = subprocess.run(
                ["scp", "gitpull.py", f"{host}:{remote_target}"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
            )
            logger.info(f"[SUCCESS] scp output for {host}: {result.stdout}")
            if result.stderr:
                logger.warning(f"[WARNING] scp stderr for {host}: {result.stderr}")
            print(f"Successfully updated gitpull script on {host}")
        except subprocess.TimeoutExpired:
            msg = f"Timed out updating gitpull script on {host}"
            logger.error(msg)
            print(msg)
            return False
        except subprocess.CalledProcessError as e:
            msg = f"Failed to update gitpull script on {host}: {e.stderr.strip()}"
            logger.error(msg)
            print(msg)
            return False
        except Exception as e:
            msg = f"Failed to update gitpull script on {host}: {str(e)}"
            logger.error(msg)
            print(msg)
            return False

        print(f"Finished updating gitpull.py on {host}\n")
    return True


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Update an eBook directory on the mirrors with the latest files from the Git repository",
        epilog="Example: %(prog)s 12345"
    )
    parser.add_argument(
        "ebook_number",
        help="Number of the eBook Git repository to pull from"
    )
    parser.add_argument(
        "--update-gitpull",
        action="store_true",
        help="Update the gitpull script on all hosts"
    )
    args = parser.parse_args()

    if args.update_gitpull:
        if not update_gitpull_to_hosts():
            print("Failed to update gitpull script on all hosts.")
            sys.exit(1)
        print("Successfully updated gitpull script on all hosts.")
        sys.exit(0)

    if not MIRROR_BIN or not PRIVATE or not EBOOKS_DIR:
        logger.error("One or more required environment variables are not set.")
        print("One or more required environment variables are not set.")
        sys.exit(1)
        
    # This is where .zip.trig files go on ibiblio :
    DOPULL_LOG_DIR = os.path.join(PRIVATE, 'logs', 'dopull')

    # Get the destination path for the eBook number
    destination = get_ebook_path(args.ebook_number)
    print(f"{args.ebook_number} goes to {destination}\n")
    destination = os.path.join(EBOOKS_DIR, destination)
    for host in mirrors:
        print("Copying to " + host + "...")
        # Call gitpull.py on the host, creating the target directory if it doesn't exist, no history
        sargs = ["--norepo", "--createdirs", f"{args.ebook_number}", f"{destination}"]
        run_python_script_via_ssh(host, f"{MIRROR_BIN}/gitpull.py", sargs)
        print("Success!\n")

    # ibiblio is a special case, it needs to trigger other actions after the pull,
    # so we just trigger the pull there and let it do the rest
    print(f"Trigger processing of #{args.ebook_number} on ibiblio...")
    run_ssh_command(ibiblio, "touch", [f"{DOPULL_LOG_DIR}/{args.ebook_number}.zip.trig"])
    print("Success!\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
