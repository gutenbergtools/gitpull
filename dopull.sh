#!/bin/bash

# Seek files to "push" to the Gutenberg servers
# gbn 06/13/2016: added "-4" because inet6 to login.ibiblio.org is problematic.  Removed 2017-01-16
# gbn 12/13/2002
# May 2003: added backup copy
# Nov 2003: Added section for root files, post-10K
# Sep 2004: Added sections for GUTINDEX* files
# Jun 2006: Removed ftp.archive.org, reinstated snowy; added readingroo.ms
# Apr 2012: Added ${LIMIT}; Sep 2014: removed
# Dec 2019: login.ibiblio.org -> login2.ibiblio.org
# Jun 2020: add BOM if needed
# Aug 2020: old saved in DONE with datestamp when replaced (rfrank)
# Oct 2020: Updated logic for 'me' to email results, also changed
#           from /bin/sh to /bin/bash
# Aug 2021: JSON logic added
#           xxxxx.txt for WWer email logic added
# Aug 2023: Get email from /htdocs/workflow3/d/71336/wwemail
# Aug 2023: Added check-for-repo.sh
# Apr 2024: check-for-repo removed; now all calls to dopush call nfenwick's dorepo code.

# Parent directory of where to look for files to push out:
STARTDIR=/home/push
GETPATH=/home/gbnewby/.bin/pgpath.pl
ADDBOM=/home/gbnewby/.bin/bomrezip.sh
today=`date +%m%d%Y`
export VERSION_CONTROL=numbered # For --backup, below.

# Output:
OUTFILE=/tmp/$$
LOGFILE=/home/gbnewby/logs/dopush-log.txt
LASTRUNFILE=/home/gbnewby/logs/dopush-lastrun

# Where to move files after uploading them:
DONE=/home/DONE

# Where to scp to -- note, we presume all permissions and
# the right directories etc. are in place there.
IBIBLIOHOST="gutenberg.login.ibiblio.org"
TOHOSTS="$IBIBLIOHOST inferno.pglaf.org aleph.pglaf.org readingroo.ms"

# Make it easier to change/add options:
# 2022-12-2:remove -4 -- hopefully not needed, and problematic for aleph.pglaf.org
SSH="/usr/bin/ssh"
SCP="/usr/bin/scp"
# TMPLOC=/export/sunsite/users/gbnewby/.tmp/pg-upload
TMPLOC=/tmp/.pg-upload

# Check whether a github repo exists for a book:
# removed [11-Apr-2024 05:45AM] .rfrank
# REPOCHECK=/home/gbnewby/.bin/check-for-repo.sh

# unzip is missing on ftp.archive.org and I don't have root
# there.  So...
archiveunzip="/local/home/gbnewby/.bin/unzip"
# same on snowy, readingroo:
ibibliounzip="/usr/bin/unzip"

# Per correspondence with Eric Feb 15 2024, when we are pushing a book
# that already exists:
# 1. If there is a JSON, any credit lines will replace the 508 entry
#    in the database. All other JSON payload will be silently ignored.
# 2. If a .trig file is created, the book's generated files will be rebuilt
IBIBLIO_TRIGGER_DIR="/public/vhost/g/gutenberg/private/logs/dopush"
IBIBLIO_JSON_DIR="/public/vhost/g/gutenberg/private/logs/json"

#LIMIT="-l 1000"
#BOSS="gbnewby@pglaf.org" # for failure messages
# Changing this address per gbnewby -dlowe
BOSS="dan@tangledhelix.com" # for failure messages

# First: is there another dopush running?
PUSHRUNNING=/home/gbnewby/.dopush-running
if [ -f ${PUSHRUNNING} ] ; then
  echo "dopush postponed at `date`" > /tmp/$$
  /bin/ps -ef > /tmp/${$}.p
  /bin/grep -i dopush /tmp/${$}.p >> /tmp/$$
  /bin/grep -i ${SCP} /tmp/${$}.p >> /tmp/$$
  /bin/rm -f /tmp/$$.p
  /bin/cat /tmp/$$ | /usr/bin/mail -s "dopush postponed" gbnewby@pglaf.org
  /bin/rm -f /tmp/$$
  exit
else
  /bin/date > ${PUSHRUNNING}
fi


#####
# Section 2: For post-10K files
# Note that Section 1 was removed from service on August 3 2020. See
# "Section 1" below.
cd $STARTDIR

# Assume anything ending in .zip is needed

if [ `/bin/ls -l | grep -c zip` != 0 ] ; then
    for i in *.zip ; do

	# new 31-Oct-2025 removed the scp. all work in WF or EWB. .rfrank
	# scp "${i}" git@inferno.pglaf.org:/home/git/staging/
	
        # Track whether an error happened:
	BOMBED='no'

	# Who do we sent notification email to?
	
	# First check whether file is group owned by www-data:
	# $3 is nfenwick, $4 is www-data when using Workflow3
	ME=`/bin/ls -l $i | head -2 | tail -1 | awk '{print $3}'`

	# If owned by www-data or nfenwick, there should be a record in the
	# workflow tool:
	getwwemail=""
	repocheck="YES" # Check if not owned by nenwick
	
	if [ x${ME} = xnfenwick ] ; then
	    getwwemail=${ME}
	    repocheck="NO"  # Don't need to check
	fi
	if [ x${ME} = xwww-data ] ; then
	    getwwemail=${ME}
	fi

	# Note: wwemail gets the original poster. If someone
	# else on errata team pushes by hand to /home/push,
	# the original poster gets notified not the errata
	# team member. So, 'getwwemail' tells us whether to
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
	
	# Check whether a repo exists. Need the book #, not the .zip:
	# removed [11-Apr-2024 05:46AM] .rfrank	
	# if [ ${repocheck} = "YES" ] ; then
	#    BOOKNUM=`/bin/echo ${i} | /usr/bin/sed 's/.zip//'`
	#    ${REPOCHECK} ${BOOKNUM}
	# fi

	# Note that if sent to www-data, it will go to someone who
	# will investigate why the above didn't work.

	## Add BOM checker here:
	## gbn April 6 2024: We're not adding BOMs any more:
#	U=$(/usr/bin/stat -c '%U' $i) # original owner
#	${ADDBOM} ${STARTDIR}/${i}
#	# If a file was changed by ADDBOM, reset the owner:
#	if [ $? = 2 ] ; then
#	    /usr/bin/sudo /bin/chown $U $i
#	fi
	
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
		    # we'll run fixperm.sh (recursive chmod) rather
		    # than separate commands:
		    bn=`echo $i | /usr/bin/sed 's/\.zip//'`
		    ${SSH} ${j} "chmod 700 ${TMPLOC}/${i}; mkdir -p ~/ftp/${remotedirs}; cd ~/ftp/${remotedirs}; ${ibibliounzip} -o ${TMPLOC}/${i}; rm -f ${TMPLOC}/${i}; /usr/bin/chgrp -R pg ~/ftp/${destdirs}; ~/.bin/fixperms.sh ~/ftp/${remotedirs}${bn}" >> $OUTFILE 2>&1
		    # ${SSH} ${j} "chmod 700 ${TMPLOC}/${i}; mkdir -p ~/ftp/${remotedirs}; cd ~/ftp/${remotedirs}; ${ibibliounzip} -o ${TMPLOC}/${i}; rm -f ${TMPLOC}/${i}; chgrp -R pg ~/ftp/${destdirs}; chmod -R g+w ~/ftp/${destdirs}; chmod -R o+rx ~/ftp/${destdirs}" >> $OUTFILE 2>&1
#		    ${SSH} ${j} "chmod 700 ${TMPLOC}/${i}; mkdir -p ~/ftp/${remotedirs}; cd ~/ftp/${remotedirs}; ${ibibliounzip} -o ${TMPLOC}/${i}; rm -f ${TMPLOC}/${i}; chgrp -R pg ~/ftp/${destdirs}; chmod -R g+w ~/ftp/${destdirs}" >> $OUTFILE 2>&1
		    ### ${SSH} ${j} "chmod 700 ${TMPLOC}/${i}; mkdir -p ~/ftp/${remotedirs}; cd ~/ftp/${remotedirs}; ${ibibliounzip} -o ${TMPLOC}/${i}; rm -f ${TMPLOC}/${i}; chmod -R g+w ~/ftp/${destdirs}" >> $OUTFILE 2>&1
# 		fi
#		    if [ $? -ne 0 ] ; then
#			echo "Got $? exit status at ${j}, this file did not go!" >> $OUTFILE; BOMBED='ERROR'
#		    else
		    # 		    if [ $j = "$IBIBLIOHOST" ] ; then
		    if [ $j = gbnewby@"$IBIBLIOHOST" ] ; then
			${SSH} $j "touch $IBIBLIO_TRIGGER_DIR/$i.trig"
			# Move to JSON metadata staging directory:
			# If there was no .json, then create xxxxx.txt
			# with the username of the WWer:
			#			    ${SSH} $j "if [ -f ~/ftp/${jsonroot}.json ]; then /bin/cp ~/ftp/${jsonroot}.json ${IBIBLIO_JSON_DIR}/; /bin/rm -f ~/ftp/${jsonroot}.json; fi"
    			${SSH} $j "if [ -f ~/ftp/${jsonroot}.json ]; then /bin/cp ~/ftp/${jsonroot}.json ${IBIBLIO_JSON_DIR}/; /bin/rm -f ~/ftp/${jsonroot}.json; else /usr/bin/echo ${ME} > ${IBIBLIO_JSON_DIR}/`/usr/bin/basename ${jsonroot}`.txt; fi"
		    else
			# Remove the JSON metadata from the other hosts:
			${SSH} $j "if [ -f ~/ftp/${jsonroot}.json ]; then /bin/rm ~/ftp/${jsonroot}.json; fi"
		    fi
		    echo "Success!" >> $OUTFILE; echo "" >> $OUTFILE
		fi      # $? != 0
	    done        # for i in *.zip; do    
	    if [ $BOMBED = 'no' ] ; then
		PD=`/bin/date --iso-8601`
		# Rename any older existing files:. gbn 20200217; 20240320
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

	
    done
fi  # End of .zip files

# Part 3, just for GUTINDEX* files:
cd $STARTDIR
if [ `/bin/ls -l | grep -c GUTINDEX` != 0 ] ; then
    for i in GUTINDEX* ; do

	echo working on $i	
	# Presume output just goes to one person
	ME=`/bin/ls -l $i | head -2 | tail -1 | awk '{print $3}'`
	for j in $TOHOSTS; do
	    echo "Copying to ${j}..." >> $OUTFILE
	    ${SCP} -q GUTINDEX* ${j}:ftp/ 2>&1 >> $OUTFILE
	    if [ $? -ne 0 ] ; then
		echo "Got $? exit status,this file did not go!" >> $OUTFILE
		BOMBED='ERROR'
	    else
		rm -f GUTINDEX*
	    fi
	done
    done
# Any files sent?  Send output:
    if [ -f $OUTFILE ] ; then
	if [ $BOMBED != 'no' ] ; then
	    /usr/bin/mail -s "$i pushed failure $BOMBED" $BOSS,$ME < $OUTFILE
	else
	    /usr/bin/mail -s "$i pushed success" $ME < $OUTFILE
	fi
	
    # Append to logfile:
	cat $OUTFILE >> $LOGFILE
	rm -f $OUTFILE
    fi
fi  # End of GUTINDEX.*


# Bye...
rm -f ${PUSHRUNNING}
exit


#########################################################################
# Not executed. We have exited just above. The section below is
# legacy code, which we no longer use because nothing ever goes to
# etext??/ destinations any more.
# gbn 2020-08-03
#########################################################################

## #####
## # Section 1: For pre-10K eBooks, which go to the etext?? directories
## 
## # Subdirectories of parent directory to check
## SUBDIRS="etext90 etext91 etext92 etext93 etext94 etext95 etext96 etext97 etext98 etext99 etext00 etext01 etext02 etext03 etext04 etext05 etext06"
## 
## today=`date +%m%d%Y`
## 
## # Where to scp to -- note, we presume all permissions and
## # the right directories etc. are in place there.
## # TOHOSTS="login2.ibiblio.org"
## TOHOSTS="gutenberg.login.ibiblio.org readingroo.ms aleph.gutenberg.org"
## #TOHOSTS="login2.ibiblio.org snowy.arsc.alaska.edu readingroo.ms"
## #TOHOSTS="login2.ibiblio.org ftp.archive.org"
## #TOHOSTS="login2.ibiblio.org snowy.arsc.alaska.edu readingroo.ms ftp.archive.org"
## 
## # unzip is missing on ftp.archive.org and I don't have root
## # there.  So...
## archiveunzip="/local/home/gbnewby/.bin/unzip"
## # same on snowy, readingroo:
## ibibliounzip="/usr/bin/unzip"
## 
## IBIBLIO_TRIGGER_DIR="/public/vhost/g/gutenberg/private/logs/dopush"
## 
## # Where to move files after uploading them:
## DONE=/home/DONE
## 
## # Who to send notice to:
## ## Temp: add Greg
## ME="`/usr/bin/whoami` gbnewby"
## 
## # Output:
## OUTFILE=/tmp/$$
## LOGFILE=/home/gbnewby/logs/dopush-log.txt
## LASTRUNFILE=/home/gbnewby/logs/dopush-lastrun
## 
## # Current date in seconds since the epoch, for logging:
## # DATE=`/bin/date +%s`
## # Let's make those more readable. gbn 20200625
## DATE=`/bin/date --iso-8601`
## echo $DATE > $LASTRUNFILE
## 
## if [ ! -d $STARTDIR ] ; then
##     echo "$0: $STARTDIR does not exist!"
##     exit 1
## fi
## 
## 
## # Change to our main working directory:
## cd $STARTDIR
## 
## # Track whether an error happened:
## BOMBED='no'
## 
## # For each subdirectory:
## for i in $SUBDIRS; do
## #    echo "checking $i"
##     if [ ! -d $i ] ; then
## 	echo "$0: subdir $i does not exist!"
## 	exit 1
##     fi
## 
##     cd $i
## #    CONTENTS=`/bin/ls -1`
##     CONTENTS=`/bin/ls`
## 
##     if [ "$CONTENTS" != "" ] ; then
## #	echo $i contains $CONTENTS
## 
## 	##	ME=`/bin/ls -l | head -2 | tail -1 | awk '{print $3}'`
## 	K=`echo "$i" | cut -d'.' -f1`
## 	FILE="/htdocs/workflow/d/$K/wwemail.txt"
## 	if test -f "$FILE"; then
## 	    ME=`cat $FILE`
## 	else
## 	    ME=`/bin/ls -l | head -2 | tail -1 | awk '{print $3}’`
## 	fi
## 
## ## Add BOM if needed:
## 	for m in $CONTENTS; do
## 	    U=$(/usr/bin/stat -c '%U' $m) # original owner
## 	    ${ADDBOM} ${STARTDIR}/${i}/${m}
## 	    # If a file was changed by ADDBOM, reset the owner:
## 	    if [ $? = 2 ] ; then
## 		/usr/bin/sudo /bin/chown $U $m
## 	    fi
## 	done		
## 	
## 	# push to servers via scp:
## 	for j in $TOHOSTS; do
## 	    echo "Pushed to $j:" >> $OUTFILE
## 	    # Use 'sh -c' to handle different login shells on hosts:
## 	    /usr/bin/ssh ${j} "/bin/sh -c cd $i; for m in \"${CONTENTS}\"; do rm -f \$m; done"
## #	    /usr/bin/ssh ${j} "/bin/sh -c cd $i; for m in \"${CONTENTS}\"; do rm -f \$m; done"
## # This just isn't quite working, no matter how I quote or escape it...
## #	    /usr/bin/ssh ${j} "/bin/sh -c \'cd $i; for m in \`echo ${CONTENTS}\`; do echo m=$m ; if [ -f \$m ] ; then mv \$m \${HOME}/etext-backup/\$m-$today ; fi ; done\'"
## 	    /usr/bin/scp -q ${CONTENTS} ${j}:${i}/ >> $OUTFILE 2>&1
## #	    /usr/bin/scp -q ${CONTENTS} ${j}:${i}/ >> $OUTFILE 2>&1
## 	    if [ $? -ne 0 ] ; then
## 		echo "Got $? exit status, this file did not go!" >> $OUTFILE
## 		BOMBED='ERROR'
## 	    fi
## 	    echo $CONTENTS >> $OUTFILE
## 	    echo "" >> $OUTFILE
## 	    if [ $j = "gutenberg.login.ibiblio.org" ] ; then
## 		for m in $CONTENTS; do
## 		    ssh $j "touch $IBIBLIO_TRIGGER_DIR/$i-$m.trig"
## 		done		
## 	    fi
## 	done
## 
## 	# move to "DONE" if we didn't bomb out:
## 	if [ $BOMBED = 'no' ] ; then 
## 	    # Move files, with filename based on date:
## 	    for k in ${CONTENTS} ; do
## #		# mv -f ${k} ${DONE}/${i}
## 		mv -f ${k} ${DONE}/${k}.${DATE}
## 		echo "Moved pushed files to ${DONE}/${k}.${DATE}" >> $OUTFILE
## 	    done
## 	else
## 	    echo "Files NOT moved, we'll try again on the next push" >> $OUTFILE
## 	fi
## 
## # Any files sent?  Send output:
## 	if [ -f $OUTFILE ] ; then
## 	    if [ $BOMBED != 'no' ] ; then
## 		/usr/bin/mail -s "${i}/${CONTENTS} pushed failure $BOMBED" $ME $BOSS < $OUTFILE
## 	    else
## 		/usr/bin/mail -s "${i}/${CONTENTS} pushed success" $ME < $OUTFILE
## 	    fi
##     # Append to logfile:
## 	    cat $OUTFILE >> $LOGFILE
## 	    rm -f $OUTFILE
## 	fi
##     fi
##     cd $STARTDIR
##     
## done # Back for the next subdir 
## 
