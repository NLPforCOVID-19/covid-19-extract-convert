#!/bin/bash

SCRIPTS=/home/frederic/covid19/translation
PIPENV=/home/frederic/.local/bin/pipenv

cd "$SCRIPTS"

echo "Converting HTML files to XML..."
$PIPENV run python convert-html-to-xml.py
echo "The HTML files have converted."

echo "Done"
