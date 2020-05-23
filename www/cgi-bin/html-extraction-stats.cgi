#!/usr/bin/env python3
# -*- coding: utf-8 -*-

print("Content-Type: text/html")
print()    

from datetime import datetime, timedelta
import glob
import json
import os
import re
import sys

config_filename = sys.argv[1] if len(sys.argv) == 2 else 'config.json'
with open(config_filename, 'r') as config_file:
    config = json.load(config_file)

run_dir = config['run_dir']


def get_total_files_per_day(filename_pattern, glob_pattern):
    files_per_day_per_domain = {}
    temp = datetime.today()
    start = temp - timedelta(days=period)
    while temp > start:
        str_year = "0" + str(temp.year) if temp.year < 10 else str(temp.year)
        str_month = "0" + str(temp.month) if temp.month < 10 else str(temp.month)
        str_day = "0" + str(temp.day) if temp.day < 10 else str(temp.day)
        str_date = "{0}-{1}-{2}".format(str_year, str_month, str_day)
        stat_filename_glob = glob_pattern.format(str_date)
        daily_totals_per_domain = {}
        files_per_day_per_domain[str_date] = daily_totals_per_domain
        for stat_filename in glob.glob(stat_filename_glob):
            with open(stat_filename, "r") as stat_file:
                for line in stat_file:
                    m = re.match(filename_pattern, line)
                    if m:
                        domain = m.group(1)
                        if domain in daily_totals_per_domain:
                            daily_totals_per_domain[domain] += 1
                        else:
                            daily_totals_per_domain[domain] = 1
                        
        temp = temp - timedelta(days=1)
    return files_per_day_per_domain


def show_total_files_per_day(files_per_day_per_domain, title):
    print("<h2>{0}</h2>".format(title))
    print("<table class=\"file-count-table table table-header-rotated table-striped table-hover table-striped-column\">")
    print("<thead>")
    print("<tr><th class=\"row-header\" >Date</th>")
    for domain in sorted(config['domains']):
        print("<th class=\"rotate-45\"><div><span>{0}</span></div></th>".format(domain))
    print("<th class=\"rotate-45\"><div><span>Total</span></div></th>".format(domain))
    print("</tr>")
    print("</thead>")

    temp = datetime.today()
    start = temp - timedelta(days=period)
    while temp > start:
        str_year = "0" + str(temp.year) if temp.year < 10 else str(temp.year)
        str_month = "0" + str(temp.month) if temp.month < 10 else str(temp.month)
        str_day = "0" + str(temp.day) if temp.day < 10 else str(temp.day)
        str_date = "{0}-{1}-{2}".format(str_year, str_month, str_day)
        daily_total = 0
        print("<tr><td>{0}</td>".format(str_date))
        for domain in sorted(config['domains']):
            total = files_per_day_per_domain[str_date][domain] if domain in files_per_day_per_domain[str_date] else 0
            daily_total += total
            print("<td class=\"num-col\">{0}</td>".format("<b>0</b>" if total == 0 else total))
        print("<td class=\"num-col\">{0}</td>".format("<b>0</b>" if daily_total == 0 else daily_total))

        print("</tr>")

        temp = temp - timedelta(days=1)

    print("</table>")


# In days.
period = 14

date_min = None
date_max = None

totals_per_domain = {}
totals_per_region = {}

os.chdir(run_dir)
for stat_filename in sorted(glob.glob('stats-*')):
    date_str = stat_filename[6:22]
    date = datetime.strptime(date_str, '%Y-%m-%d-%H-%M')
    if date_min is None or date < date_min:
        date_min = date
    if date_max is None or date > date_max:
        date_max = date

    with open(stat_filename, 'r') as stat_file:
        data_json = json.load(stat_file)
        for domain in data_json:
            count = data_json[domain]
            if domain not in config['domains']:
                continue
            region = config['domains'][domain]['region']
            if domain in totals_per_domain:
                totals_per_domain[domain] += count
            else:
                totals_per_domain[domain] = count
            if region in totals_per_region:
                totals_per_region[region] += count
            else:
                totals_per_region[region] = count

html_file_pattern = ".*/html/.+?/orig/(.+?)/.*"
html_file_glob = "new-html-files-{0}*.txt"
totals_html_per_day = get_total_files_per_day(html_file_pattern, html_file_glob) 

xml_file_pattern = ".*/xml/.+?/ja_translated/(.+?)/.*"
xml_file_glob = "new-xml-files-{0}*.txt"
totals_xml_per_day = get_total_files_per_day(xml_file_pattern, xml_file_glob)

delta = date_max - date_min

print("<!doctype html>")
print("<html lang=\"en\">")
print("<head>")
print("<meta charset=\"utf-8\">")
print("<link rel=\"stylesheet\" href=\"../default.css\">")
print("</head>")
print("<body>")

print("<h1>HTML file extraction from db files</h1>")

print("<p>Date of first extraction: {0}</p>".format(date_min))
print("<p>Date of last extraction: {0}</p>".format(date_max))
print("<p>Length of period (days): {0}</p>".format(delta.days))

print("<hr/>")

html_table_title = "Number of HTML files extracted per day per domain (last {0} days)".format(period)
show_total_files_per_day(totals_html_per_day, html_table_title)

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

print("<hr/>")

xml_table_title = "Number of XML files converted per day per domain (last {0} days)".format(period)
show_total_files_per_day(totals_xml_per_day, xml_table_title)

print("</body>")
print("</html>")

