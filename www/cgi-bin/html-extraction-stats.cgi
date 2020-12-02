#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import os.path
import subprocess
import sys
import time

build_report = True
build_stats_report_script = './build-stats-report.cgi'
report_file = '/tmp/report_covid19-stats.html'
if os.path.exists(report_file):
    stat = os.stat(report_file)
    time_delta = timedelta(seconds=time.time() - stat.st_mtime)
    if stat.st_size == 0:
        build_report = False
    else:
        time_delta = timedelta(seconds=time.time() - stat.st_mtime)
        if time_delta.seconds < 5 * 60:
            with open(report_file, 'r', encoding='utf-8') as input:
                report = input.read()
                print(report)
                sys.exit()

if build_report:
    with open(report_file, 'w', encoding='utf-8') as output:
        subprocess.Popen([build_stats_report_script], stdout=output, stderr=subprocess.STDOUT);

print("Content-Type: text/html")
print()    
print("<!doctype html>")
print("<html lang=\"en\">")
print("<head>")
print("<meta charset=\"utf-8\">")
print("<link rel=\"stylesheet\" href=\"../default.css\">")
print("<meta http-equiv=\"refresh\" content=\"20\">")
print("</head>")
print("<body>")
print("<br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/>")
print("<center>")
print("<h3>Generating report...</h3><br/><br/>")
print("<p>This can take a few minutes.<br/><br/>Please be patient.</p>")
print("<img src=\"../waiting.gif\"/>")
print("</center>")
print("</body>")
print("</html>")
