#!/bin/bash

export http_proxy=http://proxy.kuins.net:8080
export https_proxy=http://proxy.kuins.net:8080
export HTTP_PROXY=http://proxy.kuins.net:8080
export HTTPS_PROXY=http://proxy.kuins.net:8080
export ftp_proxy=http://proxy.kuins.net:8080
export FTP_PROXY=http://proxy.kuins.net:8080

SCRIPTS=/home/frederic/covid19/translation
PIPENV=/home/frederic/.local/bin/pipenv


NOW=$(date +"%Y-%m-%d %H:%M:%S")
echo "Start time: $NOW"

cd "$SCRIPTS"

echo "Fetching twitter db files..."
$PIPENV run python fetch-twitter-db.py
echo "The db files have been fetched."

echo "Extracting tweets from db files..."
$PIPENV run python extract-tweets.py
echo "The tweets have been extracted."

echo "Done"

NOW=$(date +"%Y-%m-%d %H:%M:%S")
echo "Stop time: $NOW"

