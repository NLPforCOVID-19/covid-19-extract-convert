#!/bin/bash

#
# I'm assuming that this script will be run on day 15 of each month.
#

COVID_RUN_DIR=/mnt/hinoki/share/covid19/run
ARCHIVE_DIR=$COVID_RUN_DIR/archives

NEW_HTML_FILES_DIR=$COVID_RUN_DIR/new-html-files
NEW_TRANSLATED_FILES_DIR=$COVID_RUN_DIR/new-translated-files
NEW_XML_FILES_DIR=$COVID_RUN_DIR/new-xml-files
EXTRACTER_DIR=$COVID_RUN_DIR/extracter


now=$(date +'%Y/%m/%d %H:%M')
month=$(date +'%m')
year=$(date +'%Y')

echo "Archiving old files. Started on $now."

echo $now
echo $year
echo $month


#
# Initialize tmp_year and tmp_month.
# I will move data that belong to the 3 previous
# month from the current month.
#

if [[ ${month#0} -gt 3 ]];
then
    echo "m is < 4"
    tmp_year=$year
    tmp_month=$(( ${month#0} - 3 ))
else
    echo "m is >= 4"
    tmp_year=$(( $year - 1 ))
    tmp_month=$(( 9 + ${month#0} ))
fi
tmp_month=$(printf %02d $tmp_month)


for iter in 1 2 3
do
    echo "Archiving files from $tmp_year/$tmp_month..."

    # Archive new-html-files.
    mkdir -p $ARCHIVE_DIR/new-html-files/$tmp_year/$tmp_month
    mv $NEW_HTML_FILES_DIR/new-html-files-$tmp_year-$tmp_month*.txt $ARCHIVE_DIR/new-html-files/$tmp_year/$tmp_month/.

    # Archive new-translated-files.
    mkdir -p $ARCHIVE_DIR/new-translated-files/$tmp_year/$tmp_month
    mv $NEW_TRANSLATED_FILES_DIR/new-translated-files-$tmp_year-$tmp_month*.txt* $ARCHIVE_DIR/new-translated-files/$tmp_year/$tmp_month/.
    mv $NEW_TRANSLATED_FILES_DIR/new-translated-files-en-$tmp_year-$tmp_month*.txt* $ARCHIVE_DIR/new-translated-files/$tmp_year/$tmp_month/.
    
    # Archive new-xml-files.
    mkdir -p $ARCHIVE_DIR/new-xml-files/$tmp_year/$tmp_month
    mv $NEW_XML_FILES_DIR/new-xml-files-$tmp_year-$tmp_month*.txt $ARCHIVE_DIR/new-xml-files/$tmp_year/$tmp_month/.
    rm -f $NEW_XML_FILES_DIR/new-xml-files-$tmp_year-$tmp_month*.txt.lock

    # Archive extract
    for domain_dir in $EXTRACTER_DIR/*
    do
        domain=$(basename $domain_dir)
        mkdir -p $ARCHIVE_DIR/extracter/$domain/$tmp_year/$tmp_month
        mv $domain_dir/extracter_$tmp_year-$tmp_month*.txt $ARCHIVE_DIR/extracter/$domain/$tmp_year/$tmp_month/.
    done


    if [[ ${tmp_month#0} -eq 12 ]];
    then
        tmp_month=01
        tmp_year=$(( $tmp_year + 1 ))
    else
        tmp_month=$(( ${tmp_month#0} + 1 ))
        tmp_month=$(printf %02d $tmp_month)
    fi

done

echo "Files have been archived."
