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

SCRIPTS=/home/frederic/covid19/translation
PIPENV=/home/frederic/.local/bin/pipenv

cd "$SCRIPTS"

echo "Fetching db files..."
$PIPENV run python fetch-db.py
echo "The db files have been fetched."

echo "Extracting HTML files from db files..."
$PIPENV run python extract-html.py
echo "The HTML files have been extracted."

echo "Done"
