#!/bin/bash

SCRIPTS=/home/frederic/covid19/translation-dev
PIPENV=/home/frederic/.local/bin/pipenv

export PATH=/orange/ubrew/data/bin:$PATH
export PERL5LIB=/home/frederic/usr/lib/perl:/home/frederic/usr/lib/perl/lib/perl5:/home/frederic/usr/lib/perl/lib/perl5/x86_64-linux-thread-multi:/home/frederic/perl5:/home/frederic/perl5/lib/perl5:/home/frederic/perl5/lib/perl5/site_perl/5.26.2:. 

if [ $# -ne 2 ]
then
    echo "A start and end dates must be provided (eg: ./force-convert-html-to-xml.sh 2022-02-20 2022-02-25)."
    exit 1
fi

START_DATE=$1
END_DATE=$2

NOW=$(date +"%Y-%m-%d %H:%M:%S")
echo "Start time: $NOW"

cd "$SCRIPTS"

echo "Force converting HTML files to XML..."
$PIPENV run python force-convert-html-to-xml.py "$START_DATE" "$END_DATE"

echo "Done"

NOW=$(date +"%Y-%m-%d %H:%M:%S")
echo "Stop time: $NOW"
