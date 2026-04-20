# Dopull

## Utilities provided

[dopull.py](#dopull)
[updatehosts.py](#updatehosts)
[puller.py](#puller)
[gitpull.py](#dopull)

[Overall process](#process)
[Server locations](#server-locations-locations)
[Questions](#questions)

---
## dopull.py {#dopull}

Creates or updates an eBook on ibiblio and each of the mirrors, with the latest files from the Git repository.

- Called by trivial dopull.sh cron task.
- For each trigger file found in "push" directory,
  - Get owner of file (user)
  - Call updatehosts.py to create/update the book on the mirrors, and trigger an ibiblio update.
    - If file is .json (a new book), trigger ebook indexing by copying it to the ibiblio JSON directory.
  - Move file to DONE archive
  - Send success/fail email to the user


---
## updatehosts.py {#updatehosts}

Executed by dopull.py on pglaf.org to update eBook files on ibiblio and each of the mirrors.

### Arguments

- eBook number
- --update-gitpull (optional): update the gitpull.py script on all hosts and exit. eBook number is still required but not used, just use '0'.

### Environment variables

- PRIVATE: base folder on ibiblio.
- IBIBLIO_BIN: location for the gitpull script on ibiblio.
- MIRROR_BIN: location for the gitpull script on the mirrors
- EBOOKS_DIR: the destination directory for the eBooks on the mirrors.

### Usage

`python3 updatehosts.py #####`

### Behavior

- Execute gitpull.py on each mirror to update the eBook file structure.
- Create a trigger file on ibiblio for puller.py processing.

---
## puller.py {#puller}

Called by a cron task in the ibiblio context. It looks for .zip.trig files in the system `dopull` directory, invokes gitpull on them to build or re-sync a source repo in the ibiblio FILES directory, and if successful, moves the .zip.trig file to the system `dopush` directory. It is intended to run in a privileged account - most accounts do not have write access to the system.

### Arguments - none

### Environment variables

- PUBLIC: destination file system
- PRIVATE: base folder on ibiblio.
- UPSTREAM_REPO_DIR: location of the PG Git repository system.

### Behavior

- Looks for trigger files named NNNNN.zip.trig in `$PRIVATE/logs/dopull'`, extracts NNNNN and uses that as the git repository number for gitpull. The trig file is then moved to the `$PRIVATE/logs/dopush` directory, which is how indexing and ebook builds are triggered.
- These directories should be created if they do not exist. The target directories need to be writable by the user.

If the target directories are not owned by the user who runs the gitpull or puller, the directories must be configured as "safe" with the command

`git config --global safe.directory '/path/to/directory/*'`

or for older versions of git:

`git config --global safe.directory '*'`

Git worries about this to protect a user from having code deployed by an unauthorized user. (It is not sufficient to for the user to have group writing privileges.)

---
## gitpull.py {#gitpull}

Create or update an eBook folder with the latest files from the PG Git repository.

### Overview

A simple Python utility that helps you keep a local folder synchronized with an eBook Git repository. It automatically clones the repository if it doesn't exist locally, or pulls the latest changes if it does. Optionally, do not keep Git history.

### Usage

`python3 gitpull.py <eBook #> <target_path>`

### Arguments and configuration

- `eBook #`: Number of the eBook Git repository to clone/pull from (e.g., `12345`)
- `target_path`: The local path to _contain_ the cloned or updated eBook folder (e.g., `servername/1/2/3/4`, to update `servername/1/2/3/4/12345`)

### Options

- `-h, --help`: Show help message and exit
- `-v, --verbose`: Enable verbose output
- `--norepo`: Do not keep Git history
- `--createdirs`: Create `target_path` if needed

### Environment variables

- UPSTREAM_REPO_DIR: location of the PG Git repository system.

### Example

`python3 gitpull.py 12345 /path/to/target`

### Behavior

- **The files will be pulled to a folder named with the eBook number in the target folder**: This prevents pulling to a folder that does not match the eBook number.
- **If the target folder doesn't exist**: The application will exit, unless `--createdir` is specified.
- **If the eBook folder doesn't exist in the target folder**: The repository will be cloned to the target path.
- **If the eBook folder exists but is empty**: the repository will be cloned
- **If the eBook folder exists and is a Git repository**:
  - If it has the same remote URL, the latest changes will be pulled.
  - If it has a different remote URL, an error will be displayed and no changes will be made.
- **If the eBook folder exists, but is not a Git repository** (the typical case in the 1/2/3 filesystem):
  - Initialize the repository.
    - `git init`
  - Connect to origin.
    - `git remote add origin https://r.pglaf.org/git/76044.git/`
  - Get the history (may take a while).
    - `git fetch --all`
  - Check out main branch with overwrite - updates changed files, but we are in 'detached HEAD' state.
    - `git checkout -f origin/main`
  - Restore state
    - `git switch main`
  - Remove untracked files - force, include directories, & ignored (.zip) files
    - `git clean -fdx`

#### The eBook folder will now contain the current source files (only).

- Unless `--norepo` was specified. it will also contain the Git history.

---
## Overall process {#process}

- Workflow or Errata Workbench puts a trigger file in push.
- Hourly, dopull.sh is executed to run dopull.py.
- [dopull.py](#dopull):
  - Calls updatehosts.py for each trigger file
- [updatehosts.py](#updatehosts):
  - Executes [gitpull.py](#dopull) locally on each mirror to update the eBook file structure.
  - Creates a trigger file on ibiblio for puller.py processing.
- Hourly, puller.sh calls puller.py to process trigger files.
- [puller.py](#puller):
  - Executes [gitpull.py](#dopull) locally on ibiblio to update the eBook file structure.
  - Copies trigger file to dopush to trigger catalog update.
- Hourly, cron-dopush.sh performs catalog updates and runs ebookconverter.


---
## Questions {#questions}

- The JSON file is copied directly by dopull.py to ibiblio for cron-dopush processing. Would it be better to do it in puller.py, maybe using it as the trigger?
  - In other words, for the JSON file, dopull.py calls updatehosts.py, which creates an empty trigger file for puller.py, then dopull.py copies the JSON file to ibiblio, to trigger cataloging. Two scripts creating two trigger files. It would be simpler to just use the JSON file.

- Each extract to a mirror may take several minutes, timeout = 10 min. Would it be better to have a "puller" script on each mirror?

---
## Requirements

- Python 3.6 or higher
- Git command-line tool

## License

This project is part of the Gutenberg Tools collection and is licensed under GPLv3
