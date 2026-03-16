#!/usr/bin/env python3
"""
from gutenbergtools/pglaf-gitpull: Update a folder with the latest files from a Git repository

This tool clones or pulls the latest changes from a Git repository into a
specified target folder.
"""

import argparse
import os
import subprocess
import sys
import logging
from pathlib import Path
import shutil

VERSION = "2026.03.16"
UPSTREAM_REPO_DIR = os.getenv('UPSTREAM_REPO_DIR') or 'https://github.com/gutenbergbooks/'
# Configure logging
logging.basicConfig(filename='gitpull.log', level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def run_command(cmd, cwd=None, noerror=False):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout:
            result.stdout = result.stdout.strip()
        return result.stdout
    except subprocess.CalledProcessError as e:
        if not noerror:
            logger.error(f"Error running command: {' '.join(cmd)}")
            logger.error(f"Error message: [{e.stderr}]")
        raise


def is_git_repo(path):
    """Check if a directory is a Git repository."""
    git_dir = Path(path) / ".git"
    return git_dir.exists() and git_dir.is_dir()


def get_remote_url(repo_path, noerror=False):
    """Get the remote URL of a Git repository."""
    try:
        return run_command(["git", "config", "--get", "remote.origin.url"], cwd=repo_path, noerror=noerror)
    except subprocess.CalledProcessError:
        return None


def clone_repo(repo_url, target_path):
    """Clone a Git repository to the target path."""
    logger.info(f"Cloning repository from {repo_url}...")
    run_command(["git", "clone", repo_url, str(target_path)])
    logger.info(f"Repository cloned successfully to {target_path}")


def pull_repo(repo_path):
    """Pull latest changes in an existing Git repository."""
    logger.info(f"Pulling latest changes in {repo_path}...")
    run_command(["git", "pull"], cwd=repo_path)
    run_command(["git", "clean", "-fdx"], cwd=repo_path)
    run_command(["git", "restore", "."], cwd=repo_path)
    logger.info(f"Repository updated successfully")


def copy_git_history(repo_url, target_path):
    """
    Copy a Git repository's history to a directory, update current files, remove untracked files.

    This function initializes a Git repository in the target directory (if it doesn't exist),
    adds the remote, fetches the repository's history, and checks out the files without
    overwriting existing ones.
    """
    target_path = Path(target_path).resolve()

    # Ensure the target directory exists
    if not target_path.exists():
        logger.info(f"Creating target directory: {target_path}")
        target_path.mkdir(parents=True)

    # Initialize a Git repository if it doesn't exist
    if not is_git_repo(target_path):
        logger.info(f"Initializing a new Git repository in {target_path}")
        run_command(["git", "init"], cwd=target_path)

    # Add the remote if it doesn't exist
    current_remote = get_remote_url(target_path, noerror=True)
    if not current_remote:
        logger.info(f"Adding remote origin: {repo_url}")
        run_command(["git", "remote", "add", "origin", repo_url], cwd=target_path)
    elif current_remote != repo_url:
        logger.warning(f"Remote URL mismatch. Current: {current_remote}, Requested: {repo_url}")
        return False

    # Fetch the repository's history
    logger.info(f"Fetching repository history from {repo_url}")
    run_command(["git", "fetch", "--all"], cwd=target_path)

    # Checkout the files, overwriting existing ones
    logger.info("Checking out files, overwriting existing ones")
    run_command(["git", "checkout", "-f", "origin/main"], cwd=target_path)

    # Restore state to main branch
    logger.info("Restore state to main branch")
    run_command(["git", "switch", "main"], cwd=target_path)

    # Remove untracked files - force, include directories & ignored (.zip) files
    logger.info("Remove untracked files")
    run_command(["git", "clean", "-fdx"], cwd=target_path)

    # Restore deleted files
    logger.info("Restore deleted files")
    run_command(["git", "restore", "."], cwd=target_path)

    logger.info(f"Git repository history copied successfully to {target_path}")
    return True


def update_folder(repo_url, target_path):
    """
    Update a folder with the latest files from a Git repository.

    If the target folder doesn't exist or isn't a Git repository, clone the repository.
    If it exists and is a Git repository with the same remote, pull the latest changes.
    """
    target_path = Path(target_path).resolve()

    # Check if target exists and is a directory
    if target_path.exists():
        if not target_path.is_dir():
            logger.error(f"{target_path} exists but is not a directory")
            return False

        # Check if it's a Git repository
        if is_git_repo(target_path):
            # Check if the remote URL matches
            current_remote = get_remote_url(target_path)
            if current_remote and current_remote != repo_url:
                logger.warning(f"{target_path} is a Git repository with a different remote URL")
                logger.warning(f"  Current remote: {current_remote}")
                logger.warning(f"  Requested remote: {repo_url}")
                logger.warning("Skipping update to avoid overwriting existing repository")
                return False

            # Pull latest changes
            try:
                pull_repo(target_path)
                return True
            except subprocess.CalledProcessError:
                return False
        else:
            # Directory exists but is not a Git repository
            if list(target_path.iterdir()):
                try:
                    # Attempt to copy git history and update existing files
                    copy_git_history(repo_url, target_path)
                    return True
                except subprocess.CalledProcessError:
                    return False
            else:
                # Empty directory, we can clone into it
                try:
                    clone_repo(repo_url, target_path)
                    return True
                except subprocess.CalledProcessError:
                    return False
    else:
        # Target doesn't exist, clone the repository
        try:
            clone_repo(repo_url, target_path)
            return True
        except subprocess.CalledProcessError:
            return False


def remove_git_history(target_path):
    """
    Remove Git history from the target path.
    Deletes the .git directory and common Git-related files like .gitignore, .gitattributes,
      README.md, and LICENSE.txt if they exist.
    It might be cleaner to use "git archive" to export only the files without Git history,
      but our server does not support the protocol. Would also need to remove untracked files.
      Any existing unchanged files should not be updated.
    """
    git_dir = Path(target_path) / ".git"
    if git_dir.exists() and git_dir.is_dir():
        shutil.rmtree(git_dir)
        logger.info("Git history removed successfully")
    else:
        logger.info("No Git history found to remove")
    files_to_remove = [".gitignore", ".gitattributes", "README.md", "LICENSE.txt"]
    for filename in files_to_remove:
        file_path = Path(target_path) / filename
        if file_path.exists():
            file_path.unlink()
            logger.info(f"{filename} removed successfully")
    return True


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Update an eBook folder with the latest files from the Git repository",
        epilog="Example: %(prog)s 12345 /path/to/target"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information"
    )
    parser.add_argument(
        "ebook_number",
        help="Number of the eBook Git repository to clone/pull from"
    )
    parser.add_argument(
        "target_path",
        help="Path to the target folder to update"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--norepo",
        action="store_true",
        help="Do not keep Git history"
    )
    parser.add_argument(
        "--createdirs",
        action="store_true",
        help="Create target directories if they don't exist"
    )

    args = parser.parse_args()

    if args.version:
        print(f"gitpull version {VERSION}")
        sys.exit(0)
    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Check if target exists and is a directory
    target_path = Path(args.target_path).resolve()
    if not target_path.exists() or not target_path.is_dir():
        if args.createdirs:
            # Create the target directory if it doesn't exist
            logger.info(f"Creating target directory: {target_path}")
            try:
                target_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create target directory: {e}")
                print(f"Failed: unable to create target directory {target_path}, see log.")
                sys.exit(1)
        else:
            logger.error(f"{args.target_path} does not exist or is not a directory")
            print(f"Failed: {args.target_path} does not exist or is not a directory")
            sys.exit(1)

    # Update the directory
    origin = f"{UPSTREAM_REPO_DIR}{args.ebook_number}.git/"

    # destination is a directory named with the ebook number under the target path
    destination = f"{args.target_path}/{args.ebook_number}"
    logger.info(f"Pulling from {origin} to {destination}")

    success = update_folder(origin, destination)
    # Remove Git history if not needed, but only if the update was successful to avoid
    # deleting existing files on failure
    if args.norepo and success:
        success = remove_git_history(destination)

    if success:
        print(f"Success: eBook {args.ebook_number} copied to {destination}.")
    else:
        print(f"Failed: unable to copy eBook {args.ebook_number}, see log.")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
