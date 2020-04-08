#!/bin/bash

export http_proxy=http://proxy.kuins.net:8080
export https_proxy=http://proxy.kuins.net:8080
export HTTP_PROXY=http://proxy.kuins.net:8080
export HTTPS_PROXY=http://proxy.kuins.net:8080
export ftp_proxy=http://proxy.kuins.net:8080
export FTP_PROXY=http://proxy.kuins.net:8080

SCRIPTS=/home/frederic/covid19/translation
PIPENV=/home/frederic/.local/bin/pipenv
HTML_DIR=/mnt/hinoki/share/covid19/html

cd "$SCRIPTS"

echo "Fetching db files..."
$PIPENV run python fetch-db.py
echo "The db files have been fetched."

echo "Extracting HTML files from db files..."
$PIPENV run python extract-html.py
echo "The HTML files have been extracted."

find $HTML_DIR -type d -exec chmod 775 {} \;

echo "Done"
