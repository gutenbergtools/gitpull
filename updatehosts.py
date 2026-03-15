#!/usr/bin/env python3
"""
from gutenbergtools/pglaf-gitpull: Update a folder with the latest files from a Git repository

This tool clones or pulls the latest changes from a Git repository into a
specified target folder.
"""
import argparse
import subprocess
import logging

# Configure logging
logging.basicConfig(filename='updatehosts.log', level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ibiblio = "gutenberg.login.ibiblio.org"
ibiblio_trigger_dir = "/public/vhost/g/gutenberg/private/logs/dopull/"
hosts = ["inferno.pglaf.org",
         "aleph.pglaf.org",
         "readingroo.ms"]
update_command = "/home/gbnewby/.bin/gitpull.py"

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

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Update eBook directories on mirrors with the latest files from the Git repository",
        epilog="Example: %(prog)s 12345"
    )
    parser.add_argument(
        "ebook_number",
        help="Number of the eBook Git repository to clone/pull from"
    )
    args = parser.parse_args()

    # Get the destination path for the eBook number
    destination = get_ebook_path(args.ebook_number)
    print(f"{args.ebook_number} goes to {destination}\n")
    destination = "~/ftp/9/" + destination
    for host in hosts:
        print("Copying to " + host + "...")
        run_ssh_command(host, "mkdir", ["-p", destination])
        sargs = ["--norepo", f"{args.ebook_number}", f"{destination}"]
        #sargs = ["--norepo", "--createdir", f"{args.ebook_number}", f"{destination}"]
        run_python_script_via_ssh(host, update_command, sargs)
        print("Success!\n")

    print(f"Trigger processing of #{args.ebook_number} on ibiblio...")
    run_ssh_command(ibiblio, "touch", [f"{ibiblio_trigger_dir}{args.ebook_number}.zip.trig"])
    print("Success!\n")


if __name__ == "__main__":
    main()
