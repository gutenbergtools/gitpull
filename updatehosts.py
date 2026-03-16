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

# Configure logging
logging.basicConfig(filename='updatehosts.log', level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PRIVATE = os.getenv('PRIVATE') or ''
# These are where .zip.trig files go on ibiblio :
DOPULL_LOG_DIR = os.path.join(PRIVATE, 'logs', 'dopull')
IBIBLIO_BIN = os.getenv('IBIBLIO_BIN') or ''
MIRROR_BIN = os.getenv('MIRROR_BIN') or ''

ibiblio = "gutenberg.login.ibiblio.org"
mirrors = ["inferno.pglaf.org",
           "aleph.pglaf.org",
           "readingroo.ms"]

def load_env_file(env_file='.env'):
    """
    Load environment variables from a .env file.
    Assumes the file is in the current directory and contains key=value pairs.
    Skips lines starting with # (comments) and empty lines.
    """
    if not os.path.exists(env_file):
        logger.warning(f".env file not found: {env_file}")
        return
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
                logger.info(f"Loaded env var: {key.strip()}")

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
    for host in mirrors + [ibiblio]:
        logger.info(f"Updating gitpull.py script on {host}...")
        if not os.path.exists('gitpull.py'):
            print("gitpull.py script not found in the current directory.")
            return 1
        if not IBIBLIO_BIN or not MIRROR_BIN:
            print("IBIBLIO_BIN or MIRROR_BIN environment variable not set.")
            return 1
        try:
            if host == ibiblio:
                result = run_ssh_command(host, "scp", ["gitpull.py", f"{host}:{IBIBLIO_BIN}"])
            else:
                result = run_ssh_command(host, "scp", ["gitpull.py", f"{host}:{MIRROR_BIN}"])
            print(f"Successfully updated gitpull script on {host}")
        except Exception as e:
            result = f"Failed to update gitpull script on {host}: {str(e)}"
            logger.error(result)
            return 1

        print(f"Finished updating gitpull.py on {host}, result = {result}\n")
        return 0

def main():
    """Main entry point for the script."""
    load_env_file()  # Load .env variables at the start
    parser = argparse.ArgumentParser(
        description="Update an eBook directory on the mirrors with the latest files from the Git repository",
        epilog="Example: %(prog)s 12345"
    )
    parser.add_argument(
        "ebook_number",
        help="Number of the eBook Git repository to pull from"
    )
    args = parser.parse_args()

    # Get the destination path for the eBook number
    destination = get_ebook_path(args.ebook_number)
    print(f"{args.ebook_number} goes to {destination}\n")
    destination = "~/ftp/" + destination
    for host in mirrors:
        print("Copying to " + host + "...")
        # Call gitpull.py on the host, creating the target directory if it doesn't exist, no history
        sargs = ["--norepo", "--createdir", f"{args.ebook_number}", f"{destination}"]
        run_python_script_via_ssh(host, f"{MIRROR_BIN}/gitpull.py", sargs)
        print("Success!\n")

    # ibiblio is a special case, it needs to trigger other actions after the pull,
    # so we just trigger the pull there and let it do the rest
    print(f"Trigger processing of #{args.ebook_number} on ibiblio...")
    run_ssh_command(ibiblio, "touch", [f"{DOPULL_LOG_DIR}{args.ebook_number}.zip.trig"])
    print("Success!\n")


if __name__ == "__main__":
    main()
