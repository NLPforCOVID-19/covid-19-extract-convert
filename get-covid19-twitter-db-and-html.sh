#!/bin/bash

export http_proxy=http://proxy.kuins.net:8080
export https_proxy=http://proxy.kuins.net:8080
export HTTP_PROXY=http://proxy.kuins.net:8080
export HTTPS_PROXY=http://proxy.kuins.net:8080
export ftp_proxy=http://proxy.kuins.net:8080
export FTP_PROXY=http://proxy.kuins.net:8080

SCRIPTS=/home/frederic/covid19/translation-dev
PIPENV=/home/frederic/.local/bin/pipenv


NOW=$(date +"%Y-%m-%d %H:%M:%S")
echo "Start time: $NOW"

cd "$SCRIPTS"

echo "Fetching twitter db file..."
$PIPENV run python fetch-twitter-db.py
echo "The db file have been fetched."

# echo "Extracting tweets from db file..."
# $PIPENV run python extract-tweets.py
# echo "The tweets have been extracted."

echo "Done"

NOW=$(date +"%Y-%m-%d %H:%M:%S")
echo "Stop time: $NOW"

