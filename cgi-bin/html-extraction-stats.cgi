#!/usr/bin/env python3
# -*- coding: utf-8 -*-

print("Content-Type: text/html")
print()    

import datetime
import glob
import json
import os
import sys

config_filename = sys.argv[1] if len(sys.argv) == 2 else 'config.json'
with open(config_filename, 'r') as config_file:
    config = json.load(config_file)

run_dir = config['run_dir']

date_min = None
date_max = None

totals_per_domain = {}
totals_per_region = {}

os.chdir(run_dir)
for stat_filename in sorted(glob.glob('stats-*')):
    date_str = stat_filename[6:22]
    date = datetime.datetime.strptime(date_str, '%Y-%m-%d-%H-%M')
    if date_min is None or date < date_min:
        date_min = date
    if date_max is None or date > date_max:
        date_max = date

    with open(stat_filename, 'r') as stat_file:
        data_json = json.load(stat_file)
        for domain in data_json:
            count = data_json[domain]
            region = config['domains'][domain]['region']
            if domain in totals_per_domain:
                totals_per_domain[domain] += count
            else:
                totals_per_domain[domain] = count
            if region in totals_per_region:
                totals_per_region[region] += count
            else:
                totals_per_region[region] = count
            
delta = date_max - date_min

print("<!doctype html>")
print("<html lang=\"en\">")
print("<head>")
print("<meta charset=\"utf-8\">")
print("<style>")
print("table { border-collapse: collapse; }")
print("table, th, td { border: solid 1px; }")
print("th, td { padding: 6px; }")
print(".right-aligned { text-align: right; }")
print("</style>")
print("</head>")
print("<body>")

print("<h1>HTML file extraction from db files</h1>")

print("<p>Date of first extraction: {0}</p>".format(date_min))
print("<p>Date of last extraction: {0}</p>".format(date_max))
print("<p>Length of period (days): {0}</p>".format(delta.days))
print("<hr/>")
print("<h2>Number of files per domain</h2>")
print("<table>")
print("<tr><th>Domain</th><th class=\"right-aligned\">Total</th><th class=\"right-aligned\">Daily Average</th></tr>")
grand_total = 0
total_daily_avg = 0.0
for domain in totals_per_domain:
    total = totals_per_domain[domain]
    daily_avg = total / delta.days
    grand_total += total
    total_daily_avg += daily_avg
    print("<tr><td>{0}</td><td class=\"right-aligned\">{1}</td><td class=\"right-aligned\">{2:.2f}</td></tr>".format(domain, total, daily_avg))
print("<tr><td>Total</td><td class=\"right-aligned\">{0}</td><td class=\"right-aligned\">{1:.2f}</td></tr>".format(grand_total, total_daily_avg))
print("</table>")

print("<h2>Number of files per region</h2>")
print("<table>")
print("<tr><th>Region</th><th class=\"right-aligned\">Total</th><th class=\"right-aligned\">Daily Average</th></tr>")
grand_total = 0
total_daily_avg = 0.0
for region in totals_per_region:
    total = totals_per_region[region]
    daily_avg = total / delta.days
    grand_total += total
    total_daily_avg += daily_avg
    print("<tr><td>{0}</td><td class=\"right-aligned\">{1}</td><td class=\"right-aligned\">{2:.2f}</td></tr>".format(region, total, daily_avg))
print("<tr><td>Total</td><td class=\"right-aligned\">{0}</td><td class=\"right-aligned\">{1:.2f}</td></tr>".format(grand_total, total_daily_avg))
print("</table>")
    
print("</body>")
print("</html>")

