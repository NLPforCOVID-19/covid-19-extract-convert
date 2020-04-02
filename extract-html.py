import datetime
import glob
import json
import os
import re
import sqlite3
import sys

config_filename = sys.argv[1] if len(sys.argv) == 2 else 'config.json'
with open(config_filename, 'r') as config_file:
    config = json.load(config_file)

db_dir = config['db_dir']
html_dir = config['html_dir']
run_dir = config['run_dir']

now = datetime.datetime.now()

nb_html_files_per_domain = {}
processed_db_per_domain = {}

gmt_date_format = '%a, %d %b %Y %H:%M:%S GMT'
utf_offset_date_format = '%a, %d %b %Y %H:%M:%S %z'
utf_offset_date_format_2 = '%a, %d %b %y %H:%M:%S %z'


def write_html_file(path, filename, url):
    try:
        os.makedirs(path, exist_ok=True)
        filename = os.path.join(path, filename)
        with open(filename, 'wb') as html_file:
            html_file.write(content)
        filename_url = filename[:-5] + '.url'
        with open(filename_url, 'w') as url_file:
            url_file.write(url)
        new_html_filename = os.path.join(run_dir, 'new-html-files-{}.txt'.format(now.strftime('%Y-%m-%d-%H-%M')))
        with open(new_html_filename, 'a') as new_html_file:
            new_html_file.write(filename)
            new_html_file.write("\n")
        global nb_html_files
        nb_html_files += 1
    except OSError as os_err:
        print("An error has occurred: {0}".format(os_err))


def write_stats_file(filename):
    with open(filename, 'w') as stats_file:
        data = {}
        json.dump(nb_html_files_per_domain, stats_file)


def is_too_old(headers):
    json_data = json.loads(headers)
    for key in json_data:
        if key == 'last-modified' or key == 'Last-Modified' or key == 'Last-modified':
            str_last_modif = json_data[key]
            try:
                last_modif = datetime.datetime.strptime(str_last_modif, gmt_date_format) 
            except ValueError:
                try:
                    last_modif = datetime.datetime.strptime(str_last_modif, utf_offset_date_format) 
                except ValueError:
                    try:
                        last_modif = datetime.datetime.strptime(str_last_modif, utf_offset_date_format_2) 
                    except ValueError:
                        # Give up, 
                        return False
            if last_modif.year < 2019 or last_modif == 2019 and month < 11:
                return True
    return False


for domain in os.listdir(db_dir):
    if domain.endswith('.html') or domain.endswith('.py') or domain.endswith('.py~') or domain.endswith(".jp"):
        continue
    domain_dir = db_dir + '/' + domain
    real_domain = domain.replace('_', '.')
    # print("domain_dir={0} real_domain={1}".format(domain_dir, real_domain))
    if real_domain not in config['domains']:
        continue

    run_filename = os.path.join(run_dir, '{}.json'.format(real_domain))
    if os.path.exists(run_filename):
        with open(run_filename, 'r') as run_file:
            run_data = json.load(run_file)
            print("run_data for {0}={1}".format(real_domain, run_data))
            processed_db_per_domain[real_domain] = run_data

    nb_html_files = 0
    
    lang = config['domains'][real_domain]['language']
    region = config['domains'][real_domain]['region']
    for db_file in sorted(glob.glob('{0}/*.db'.format(domain_dir))):
        db_file_basename = os.path.basename(db_file)
        if real_domain in processed_db_per_domain and db_file_basename in processed_db_per_domain[real_domain]:
            continue
        print("Processing {0}".format(db_file))
        conn = sqlite3.connect(db_file)
        try:
            cursor = conn.cursor()
            sql = (
                "select url, same_as, content, headers from page "
                "where content_type like '%text/html%'"
            )
            for row in cursor.execute(sql):
                url = row[0]
                same_as = row[1]
                content = row[2]
                headers = row[3]

                # Skip older files.
                if is_too_old(headers):
                    continue

                # print("url={0} same_as={1} isNone={2} isEmptu={3}".format(url, same_as, (same_as is None), same_as == ''))
                domain_part = "^http.*?{0}/(.*)".format(real_domain)
                match = re.search(domain_part, url)
                # print("url={}".format(url))
                if match:
                    # print("g0={}".format(match.group(0)))
                    # print("g1={}".format(match.group(1)))
                    path = match.group(1)
                    if path == '':
                        filename = '_'
                    else:
                        parts = path.split('/')
                        dirs = '/'.join(parts[:-1])
                        filename = parts[-1]
                        if filename == '':
                            filename = '_'
                        # print("mkdirs {}".format(dirs))
                    # print("filename {}".format(filename))
                    if filename.endswith('.htm'):
                        filename = filename[:-4] + '.html'
                    if not filename.endswith('.html'):
                        filename = filename + '.html'
                    full_path = os.path.join(html_dir, region, 'orig', real_domain, path)
                    # print("full_path {}".format(full_path))
                    if not os.path.exists(os.path.join(full_path, filename)) or same_as is None:
                        write_html_file(full_path, filename, url)

        except sqlite3.DatabaseError as db_err:
            print("An error has occurred: {0}".format(db_err))
        finally:
            conn.close()
        nb_html_files_per_domain[real_domain] = nb_html_files
        if real_domain in processed_db_per_domain:
            processed_db_per_domain[real_domain].append(os.path.basename(db_file))
        else:
            processed_db_per_domain[real_domain] = [os.path.basename(db_file)]

    with open(run_filename, 'w') as run_file:
        json.dump(processed_db_per_domain[real_domain], run_file)

stats_file = os.path.join(run_dir, 'stats-{}.json'.format(now.strftime('%Y-%m-%d-%H-%M')))
write_stats_file(stats_file)
