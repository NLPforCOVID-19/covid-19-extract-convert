#!/bin/bash

#
# Important: 
#
# This script must be executed from from tulip.
# It uses my local wget-1.20.
# The version installed on the system had this issue:
# idn_encode failed (3): ‘Non-digit/letter/hyphen in input’
# https://stackoverflow.com/questions/37881346/idn-encode-failed-3-non-digit-letter-hyphen-in-input
# Using a more recent version seems to bypass this issue.
#

export http_proxy=http://proxy.kuins.net:8080
export https_proxy=http://proxy.kuins.net:8080
export HTTP_PROXY=http://proxy.kuins.net:8080
export HTTPS_PROXY=http://proxy.kuins.net:8080
export ftp_proxy=http://proxy.kuins.net:8080
export FTP_PROXY=http://proxy.kuins.net:8080

SRC=http://setagaya.tkl.iis.u-tokyo.ac.jp:8901/~suzuki/covid19
WRK=/data/frederic/covid19/db
DST=/mnt/hinoki/share/covid19/db
EXT=/home/frederic/covid19/translation

declare -a procs

# cd "$WRK"
# # Remove index.html files to force the download of the databases.
# find . -iname "index.html" -exec rm -f {} \;
# echo "Retrieving latest db files..."
# wget -O covid19_index_html $SRC
# grep "^<li>" covid19_index_html | cut -d "\"" -f 2 | while read -r line ; do
#     echo "Downloading database from $line..." 
#     # echo "wget --timeout=0 --mirror --random-wait --page-requisites $SRC/$line"
#     # wget --timeout=15 --mirror --random-wait --page-requisites $SRC/$line &
#     # wget --timeout=0 --mirror --random-wait --page-requisites $SRC/$line &
#     wget --timeout=15 -nc -q --recursive --level 1 $SRC/$line
# done
# echo "The db files have been retrieved."

# 
# I tried to fetch the db files using parallel wget instances
# but for some reasons, on some occasions, a problem occurs and
# the script crashes, preventing the ulterior steps to execute.
# 
cd "$WRK"
# Remove index.html files to force the download of the databases.
find . -iname "index.html" -exec rm -f {} \;
echo "Retrieving latest db files..."
wget -O covid19_index_html $SRC
grep "^<li>" covid19_index_html | cut -d "\"" -f 2 | while read -r line ; do
    echo "Downloading database from $line..." 
    # echo "wget --timeout=0 --mirror --random-wait --page-requisites $SRC/$line"
    # wget --timeout=15 --mirror --random-wait --page-requisites $SRC/$line &
    # wget --timeout=0 --mirror --random-wait --page-requisites $SRC/$line &
    wget --timeout=15 -nc --recursive --level 1 $SRC/$line &
    procs=("${procs[@]}" $!)
done
for procId in "${procs[@]}"
do
    wait $procId
done
echo "The db files have been retrieved."

find $WRK -type d -exec chmod 775 {} \;
echo "Synchronizing the db files with the share folder..."
rsync -av "$WRK/" "$DST/"
echo "The db files have been synchronized."

cd "$EXT"
echo "Extracting HTML files from db files..."
pipenv run python extract-html.py
echo "The HTML files have been extracted."

echo "Done"
