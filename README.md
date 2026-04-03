# Dopull

## Utilities used
[dopull.sh](#dopull)
[updatehosts.py](#updatehosts)
[puller.py](#puller)
[gitpull.py](#dopull)
[Questions](#questions)

---
## dopull.sh {#dopull}
Cron task on pglaf.org to create or update an eBook on ibiblio and each of the mirrors, with the latest files from the Git repository.

---
## updatehosts.py {#updatehosts}

Executed by dopull.sh on pglaf.org to update eBook files on ibiblio and each of the mirrors.

### Arguments
- eBook number
- --update-gitpull (optional): update the gitpull script on all hosts and exit.


### Environment variables
- PRIVATE: base folder on ibiblio.
- IBIBLIO_BIN: location for the gitpull script on ibiblio.
- MIRROR_BIN: location for the gitpull script on the mirrors
- EBOOKS_DIR: the destination directory for the eBooks on the mirrors.

### Usage

```bash
python3 updatehosts.py #####
```

### Behavior

---
## puller.py {#puller}

Called by a cron task in the ibiblio context, it invokes gitpull. It looks for .zip.trig files in the system dopull directory, invokes gitpull on them to build or re-sync a source repo in the ibiblio FILES directory, and if successful, moves the .zip.trig file to the system `dopush` directory. It is intended to run in a privileged account - most accounts do not have write access to the system.

### Arguments and Configuration

- Has no arguments
- Reads three variables from its environment: PUBLIC, PRIVATE and UPSTREAM_REPO_DIR, which it uses to form a repository url and a target path for gitpull
- the default for PRIVATE is '' and for UPSTREAM_REPO_DIR is 'https://github.com/gutenbergbooks/' (which is used for testing)
- puller looks for 'trig' files named NNNNN.zip.trig in \$PRIVATE/logs/dopull', extracts NNNNN and uses that as the git repository number for gitpull. The trig file is then moved to the \$PRIVATE/logs/dopush directory, which is how indexing and ebook builds are triggered.
- these directories should be created if they do not exist. The target directories need to be writable by the user.

If the target directories are not owned by the user who runs the gitpull or puller, the directories must be configured as "safe" with the command

`git config --global safe.directory '/path/to/directory/*'`

or for older versions of git:

`git config --global safe.directory '*'`

git worries about this to protect a user from having code deployed by an unauthorized user. (It is not sufficient to for the user to have group writing privileges.)

### Behavior

---
## gitpull.py {#gitpull}
Create or update an eBook folder with the latest files from the Git repository.

### Overview

A simple Python utility that helps you keep a local folder synchronized with an eBook Git repository. It automatically clones the repository if it doesn't exist locally, or pulls the latest changes if it does.

### Installation

```bash
git clone https://github.com/gutenbergtools/gitpull.git
cd gitpull
```

for use on iBiblio, use pipenv to create an environment, then install from pypi:

for production
```
pipenv install git+https//github.com/gutenbergtools/gitpull.git
```

for local development:
```
pipenv install -e git+https//github.com/gutenbergtools/gitpull.git
```

Then copy sample.env to .env and edit the paths as appropriate.

### Usage

```bash
python3 gitpull.py <eBook #> <target_path>
```

### Arguments and configuration
- `repository_url`: Number of the eBook Git repository to clone/pull from (e.g., `12345`)
- `target_path`: The local path _containing_ the eBook folder where the repository should be cloned or updated (e.g., `servername/1/2/3/4`, to update `servername/1/2/3/4/12345`)

### Options
- `-h, --help`: Show help message and exit
- `-v, --verbose`: Enable verbose output
- `--norepo`: Do not keep Git history
- `--createdirs`: Create `target_path` if needed

### Environment variables
- UPSTREAM_REPO_DIR: location of the PG Git repository system.

### Examples for gitpull

Clone a new repository or update an existing repository:

```bash
python3 gitpull.py 12345 /path/to/target
```

or
`pipenv run gitpull 12345 /path/to/target`

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
## Questions {#questions}

- The JSON file is copied directly by dopull.py to ibiblio for cron-dopush prcessing. Would it be better to do it in puller.py, maybe using it as the trigger?
  - In other words, for the JSON file, two triggers are currently created on ibiblio, in different steps.

- dopush also does GUTINDEX processing, what do we do with it?

- Each extract to a mirror may take several minutes, timeout = 10 min. Would it be better to have a "puller" script on each mirror?

---
## Requirements

- Python 3.6 or higher
- Git command-line tool

## License

This project is part of the Gutenberg Tools collection and is licensed under GPLv3
