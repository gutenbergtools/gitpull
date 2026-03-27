#!/bin/bash

# Seek files to "pull" to the Gutenberg servers

# Parent directory of where to look for files to push out:
STARTDIR=/home/push
GETPATH=/home/gbnewby/.bin/pgpath.pl
today=`date +%m%d%Y`
export VERSION_CONTROL=numbered # For --backup, below.

# Output:
OUTFILE=/tmp/$$
LOGFILE=/home/gbnewby/logs/dopull-log.txt
LASTRUNFILE=/home/gbnewby/logs/dopull-lastrun

# Where to move files after uploading them:
DONE=/home/DONE

# Where to scp to -- note, we presume all permissions and the right directories etc. are in place there.
IBIBLIOHOST="gutenberg.login.ibiblio.org"
TOHOSTS="$IBIBLIOHOST inferno.pglaf.org aleph.pglaf.org readingroo.ms"

# Make it easier to change/add options:
SSH="/usr/bin/ssh"
SCP="/usr/bin/scp"
TMPLOC=/tmp/.pg-upload

# unzip is missing on ftp.archive.org and I don't have root there.  So...
archiveunzip="/local/home/gbnewby/.bin/unzip"
# same on snowy, readingroo:
ibibliounzip="/usr/bin/unzip"

# Per correspondence with Eric Feb 15 2024, when we are pushing a book that already exists:
# 1. If there is a JSON, any credit lines will replace the 508 entry
#    in the database. All other JSON payload will be silently ignored.
# 2. If a .trig file is created, the book's generated files will be rebuilt
IBIBLIO_TRIGGER_DIR="/public/vhost/g/gutenberg/private/logs/dopush"
IBIBLIO_JSON_DIR="/public/vhost/g/gutenberg/private/logs/json"

#LIMIT="-l 1000"
BOSS="pterodactyl@fastmail.com" # for failure messages

# First: is there another dopull running?
PULLRUNNING=/home/gbnewby/.dopull-running
if [ -f ${PULLRUNNING} ] ; then
  echo "dopull postponed at `date`" > /tmp/$$
  /bin/ps -ef > /tmp/${$}.p
  /bin/grep -i dopull /tmp/${$}.p >> /tmp/$$
  /bin/grep -i ${SCP} /tmp/${$}.p >> /tmp/$$
  /bin/rm -f /tmp/$$.p
  /bin/cat /tmp/$$ | /usr/bin/mail -s "dopull postponed" gbnewby@pglaf.org
  /bin/rm -f /tmp/$$
  exit
else
  /bin/date > ${PULLRUNNING}
fi

# Section 2: For post-10K files
# Note that Section 1 was removed from service on August 3 2020.
cd $STARTDIR

# Assume anything ending in .zip is needed
if [ `/bin/ls -l | grep -c zip` != 0 ] ; then
  for i in *.zip ; do
		# Track whether an error happened:
		BOMBED='no'

		# Who do we sent notification email to?

		# First check whether file is group owned by www-data:
		# $3 is nfenwick, $4 is www-data when using Workflow3
		ME=`/bin/ls -l $i | head -2 | tail -1 | awk '{print $3}'`

		# If owned by www-data or nfenwick, there should be a record in the workflow tool:
		getwwemail=""
		repocheck="YES" # Check if not owned by nenwick

		if [ x${ME} = xnfenwick ] ; then
			getwwemail=${ME}
			repocheck="NO"  # Don't need to check
		fi
		if [ x${ME} = xwww-data ] ; then
			getwwemail=${ME}
		fi

		# Note: wwemail gets the original poster. If someone else on errata team pushes by hand to /home/push,
		# the original poster gets notified not the errata team member. So, 'getwwemail' tells us whether to
		# notify the owner of the file in /home/push/
		if [ x${getwwemail} != x ] ; then
				K=`echo "$i" | cut -d'.' -f1` # Just the eBook number
				FILE="/htdocs/workflow/e/$K/wwemail"
				if test -f "$FILE"; then
					ME=`cat $FILE`
				fi
				FILE="/htdocs/workflow3/d/$K/wwemail"
				if test -f "$FILE"; then
					# gbn Jan 26 2024: ajhaines has a bare <cr>. Where is it coming from?
					# https://www.geeklab.info/2024/01/552-5-2-0-message-contains-bare-cr-and-is-violating-822-bis-section-2-3-in-reply-to-end-of-data-command/
					ME=`cat $FILE`
				fi
		fi

		# Note that if sent to www-data, it will go to someone who will investigate why the above didn't work.

		# Get the remote directory path, exit on error if it fails
		remotedirs=`$GETPATH $i`
		if [ $? -ne 0 ] ; then
	    echo "$GETPATH failed for ${i}.  Skipping." >> $OUTFILE
	    BOMBED='ERROR'
		else
	    echo "${i} goes to $remotedirs" >> $OUTFILE
	    destdirs=$remotedirs/`echo $i | sed 's/\.zip//'`
	    jsonroot=${destdirs}/`echo $i | sed 's/\.zip//'`
	    for j in ${TOHOSTS}; do
				echo "" >> ${OUTFILE}
				echo "Copying and unzipping on ${j}..." >> ${OUTFILE}
				# gbn: my 'gbnewby' went away June 3 2022... temp, I needed
				# to explicitly use a different username
				if [ "${j}" = "${IBIBLIOHOST}" ] ; then
						j=gbnewby@${j}
				fi
				# Create destination directory for the .zip
				${SSH} ${j} mkdir -p ${TMPLOC}/
				# Upload:
				${SCP} -q ${i} ${j}:${TMPLOC}/${i}

				if [ $? -ne 0 ] ; then
					echo "Got $? exit status, this file did not go!" >> $OUTFILE; BOMBED='ERROR'
				else
					# ibiblio needs chgrp as well as chmod
					# we'll run fixperm.sh (recursive chmod) rather than separate commands:
					bn=`echo $i | /usr/bin/sed 's/\.zip//'`
					${SSH} ${j} "chmod 700 ${TMPLOC}/${i}; mkdir -p ~/ftp/${remotedirs}; cd ~/ftp/${remotedirs}; ${ibibliounzip} -o ${TMPLOC}/${i}; rm -f ${TMPLOC}/${i}; /usr/bin/chgrp -R pg ~/ftp/${destdirs}; ~/.bin/fixperms.sh ~/ftp/${remotedirs}${bn}" >> $OUTFILE 2>&1
					if [ $j = gbnewby@"$IBIBLIOHOST" ] ; then
						${SSH} $j "touch $IBIBLIO_TRIGGER_DIR/$i.trig"
						# Move to JSON metadata staging directory:
						# If there was no .json, then create xxxxx.txt with the username of the WWer:
						${SSH} $j "if [ -f ~/ftp/${jsonroot}.json ]; then /bin/cp ~/ftp/${jsonroot}.json ${IBIBLIO_JSON_DIR}/; /bin/rm -f ~/ftp/${jsonroot}.json; else /usr/bin/echo ${ME} > ${IBIBLIO_JSON_DIR}/`/usr/bin/basename ${jsonroot}`.txt; fi"
					else
						# Remove the JSON metadata from the other hosts:
						${SSH} $j "if [ -f ~/ftp/${jsonroot}.json ]; then /bin/rm ~/ftp/${jsonroot}.json; fi"
					fi
					echo "Success!" >> $OUTFILE; echo "" >> $OUTFILE
				fi      # $? != 0
	    done        # for j in ${TOHOSTS}; do
	    if [ $BOMBED = 'no' ] ; then
				PD=`/bin/date --iso-8601`
				# Rename any older existing files:
				if [ -f ${DONE}/${i} ] ; then
		      mv -f --backup ${DONE}/${i} ${DONE}/${i}.${PD}
	      fi
        mv -f ${i} ${DONE}/
	    fi                  # $? -ne 0 ] then; else;
		fi

		# Any files sent?  Send output:
		if [ -f $OUTFILE ] ; then
				if [ $BOMBED != 'no' ] ; then
					/usr/bin/mail -s "${i} pushed failure $BOMBED" $BOSS,$ME< ${OUTFILE}
				else
					/usr/bin/mail -s "${i} pushed success" $ME < $OUTFILE
				fi
				# Append to logfile:
				cat $OUTFILE >> $LOGFILE
				rm -f $OUTFILE
		fi

  done # for i in *.zip ; do
fi  # End of .zip files

# Bye...
rm -f ${PULLRUNNING}
exit
