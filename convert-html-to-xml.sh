#!/bin/bash

SCRIPTS=/home/frederic/covid19/translation
PIPENV=/home/frederic/.local/bin/pipenv

export PATH=/orange/ubrew/data/bin:$PATH
export PERL5LIB=/home/frederic/usr/lib/perl:/home/frederic/usr/lib/perl/lib/perl5:/home/frederic/usr/lib/perl/lib/perl5/x86_64-linux-thread-multi:/home/frederic/perl5:/home/frederic/perl5/lib/perl5:/home/frederic/perl5/lib/perl5/site_perl/5.26.2:. 

NOW=$(date +"%Y-%m-%d %H:%M:%S")
echo "Start time: $NOW"

cd "$SCRIPTS"

echo "Converting HTML files to XML..."
if [ $# -ne 0 ]
then
    REGION=$1
    $PIPENV run python convert-html-to-xml.py --log_config converter_logging_${REGION//,/_} $REGION
else
    $PIPENV run python convert-html-to-xml.py
fi
echo "The HTML files have been converted."

echo "Done"

NOW=$(date +"%Y-%m-%d %H:%M:%S")
echo "Stop time: $NOW"
