import datetime
import glob
import hashlib
import json
import os
import re
import sqlite3
import sys

input_domain = sys.argv[1]

config_filename = sys.argv[2] if len(sys.argv) == 3 else 'config.json'

with open(config_filename, 'r') as config_file:
    config = json.load(config_file)

db_dir = config['db_dir']
html_dir = config['html_dir']
run_dir = config['run_dir']

rejected_urls = []
with open(config['url_black_list'], 'r') as rejected_urls_file:
    for line in rejected_urls_file:
        rejected_urls.append(line.strip())


now = datetime.datetime.now()

nb_html_files_per_domain = {}
processed_db_per_domain = {}

gmt_date_format = '%a, %d %b %Y %H:%M:%S GMT'
utf_offset_date_format = '%a, %d %b %Y %H:%M:%S %z'
utf_offset_date_format_2 = '%a, %d %b %y %H:%M:%S %z'


def is_blacklisted(url):
    for item in rejected_urls:
        if url.find(item) != -1:
            return True
    return False


def write_html_file(path, filename, url, content, source, domain_path):
    print("write_html_file path={0} filename={1} url={2} source={3} domain_path={4}".format(path, filename, url, source, domain_path))
    try:
        timestamp = now.strftime('%Y-%m-%d-%H-%M')
        path = "{0}_{1}".format(path, timestamp)
        os.makedirs(path, exist_ok=True)
        temp_path = path
        while temp_path != domain_path:
            os.chmod(temp_path, 0o775)
            temp_path = os.path.dirname(temp_path)
        filename = os.path.join(path, filename)
        with open(filename, 'wb') as html_file:
            html_file.write(content)
        filename_url = filename[:-5] + '.url'
        with open(filename_url, 'w') as url_file:
            url_file.write(url)
        filename_source = filename[:-5] + '.src'
        with open(filename_source, 'w') as source_file:
            source_file.write(source)
        new_html_filename = os.path.join(run_dir, 'new-html-files-{}.txt'.format(timestamp))
        with open(new_html_filename, 'a') as new_html_file:
            new_html_file.write(filename)
            new_html_file.write("\n")
        global nb_html_files
        nb_html_files += 1
    except OSError as os_err:
        print("An error has occurred in write_html(path={0} filename={1} url={2}): {3}".format(path, filename, url, os_err))


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


def get_source(file, filename):
    source_filename = os.path.join(file, filename[:-5] + '.src')
    print("source_filename={}".format(source_filename))
    if os.path.exists(source_filename):
        with open(source_filename, 'r') as source_file:
            source = source_file.read()
        return source
    return None


def get_content(file, filename):
    content_filename = os.path.join(file, filename[:-5] + '.html')
    # print("content_filename={0}".format(content_filename))
    if os.path.exists(content_filename):
        with open(content_filename, 'rb') as content_file:
            content_on_disk = content_file.read()
        return content_on_disk
    return None


def process_file(filename, parent_dir, file_dir_prefix, same_as, url, content, db_file_basename, full_path, domain_path):
    all_versions = sorted(glob.glob("{0}/{1}".format(parent_dir, file_dir_prefix)) + glob.glob("{0}/{1}_[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[0-9][0-9]".format(parent_dir, file_dir_prefix)))
    if len(all_versions) > 0:
        # Now that we are using the similarity column from the database, I'm not convinced that
        # the following code is useful. It looks redundant actually.

        # Only consider the most recent version.
        file = all_versions[-1]
        if os.path.isdir(file):
            if same_as:
                source = get_source(file, filename)
                print("source={0} same_as={1} egal?={2}".format(source, same_as, (source == same_as)))
                if source is not None and source == same_as:
                    return

            content_on_disk = get_content(file, filename)
            if content_on_disk is not None:
                md5_content = hashlib.md5(content)
                md5_content_on_disk = hashlib.md5(content_on_disk)
                # print("content == content_on_disk? {}".format(content == content_on_disk))
                print("md5_content={0} md5_content_on_disk={1} equal? {2}".format(md5_content.hexdigest(), md5_content_on_disk.hexdigest(), md5_content.hexdigest() == md5_content_on_disk.hexdigest()))
                test = md5_content.hexdigest() == md5_content_on_disk.hexdigest()
                if test:
                    return

    source = same_as or db_file_basename
    write_html_file(full_path, filename, url, content, source, domain_path)


def process_row(row, real_domain, region, db_file_basename):
    url = row[0]
    same_as = row[1]
    content = row[2]
    headers = row[3]
    similarity = row[4]
    main_text_similarity = row[5]
    compared_against = row[6]

    # Skip older files.
    if is_too_old(headers):
        print("url too old detected!!!: {}".format(url))
        return

    # Skip blacklisted urls.
    if is_blacklisted(url):
        print("url blacklisted detected!!!: {}".format(url))
        return

    # Consider only urls that match the domain_part or declared subdomains.
    # print("url={0} same_as={1} isNone={2} isEmpty={3}".format(url, same_as, (same_as is None), same_as == ''))
    domain_part = "^http.*?{0}/(.*)".format(real_domain)
    if 'prefix' in config['domains'][real_domain]:
        domain_part = "^http.*?{0}/(.*)".format(config['domains'][real_domain]['prefix'])
    match = re.search(domain_part, url)
    if not match:
        if 'subdomains' not in config['domains'][real_domain]:
            print("url discarded because it's not matching the domain.")
            return

        subdomain_match = False
        for subdomain in config['domains'][real_domain]['subdomains']:
            match = re.search("^https?://({0}/.*)".format(subdomain), url)
            if match:
                subdomain_match = True
                break
        if not subdomain_match:
            print("url discarded because it's not matching the domain or subdomains.")
            return

    print("url: {0} sim: {1} main_text_sim: {2} compared against: {3}".format(url, similarity, main_text_similarity, compared_against))
    if compared_against is not None and main_text_similarity >= 0.8 :
        print("url too similar to previous version: {0} sim: {1} main_text_sim={2}".format(url, similarity, main_text_similarity))
        return

    # print("url={0} g0={1} g1={2}".format(url, match.group(0), match.group(1)))
    path = match.group(1)
    if path == '':
        filename = '_'
    else:
        # Remove leading slashes.
        while path.startswith('/'):
            path = path[1:]
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
    domain_path = os.path.join(html_dir, region, 'orig', real_domain)
    full_path = os.path.join(html_dir, region, 'orig', real_domain, path)
    parent_dir = os.path.dirname(full_path)
    file_dir_prefix = os.path.basename(full_path)
    print("full_path {0} filename={1} parent_dir={2} file_dir_prefix={3}".format(full_path, filename, parent_dir, file_dir_prefix))
    print("glob expr={0}/{1}*".format(parent_dir, file_dir_prefix))
    process_file(filename, parent_dir, file_dir_prefix, same_as, url, content, db_file_basename, full_path, domain_path)


for domain in os.listdir(db_dir):
    if domain.endswith('.html') or domain.endswith('.py') or domain.endswith('.py~') or domain.endswith(".jp"):
        continue
    domain_dir = db_dir + '/' + domain
    real_domain = domain.replace('_', '.')
    print("domain_dir={0} real_domain={1} input_domain={2}".format(domain_dir, real_domain, input_domain))
    if input_domain != 'all' and real_domain != input_domain:
        continue

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
                "select url, same_as, content, headers, similarity, maintext_similarity, compared_against from page "
                "where content_type like '%text/html%'"
            )
            for row in cursor.execute(sql):
                process_row(row, real_domain, region, db_file_basename)
        except sqlite3.DatabaseError as db_err:
            print("An error has occurred: {0}".format(db_err))
        finally:
            conn.close()
        nb_html_files_per_domain[real_domain] = nb_html_files
        if real_domain in processed_db_per_domain:
            processed_db_per_domain[real_domain].append(os.path.basename(db_file))
        else:
            processed_db_per_domain[real_domain] = [os.path.basename(db_file)]

        if os.path.exists(db_file):
            os.remove(db_file)

    with open(run_filename, 'w') as run_file:
        json.dump(processed_db_per_domain[real_domain], run_file)

stats_file = os.path.join(run_dir, 'stats-{}.json'.format(now.strftime('%Y-%m-%d-%H-%M')))
write_stats_file(stats_file)




