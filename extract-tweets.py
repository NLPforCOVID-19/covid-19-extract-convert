# import bs4
import datetime
# from difflib import SequenceMatcher
import glob
# import hashlib
import json
import os
import re
# import sys
import twitter
import utils


config_filename = 'config.json'
 
with open(config_filename, 'r') as config_file:
    config = json.load(config_file)

db_dir = config['db_dir']
twitter_db_dir = f"{db_dir}/twitter"
html_dir = config['html_dir']
run_dir = config['run_dir']

now = datetime.datetime.now()

processed_databases = []

# gmt_date_format = '%a, %d %b %Y %H:%M:%S GMT'
# utf_offset_date_format = '%a, %d %b %Y %H:%M:%S %z'
# utf_offset_date_format_2 = '%a, %d %b %y %H:%M:%S %z'
# 
# 
# def write_html_file(path, filename, url, content, source, domain_path):
#     print("write_html_file path={0} filename={1} url={2} source={3} domain_path={4}".format(path, filename, url, source, domain_path))
#     try:
#         timestamp = now.strftime('%Y-%m-%d-%H-%M')
#         timestamp_path = now.strftime('%Y/%m/%d-%H-%M')
#         path = "{0}/{1}".format(path, timestamp_path).replace("//", "/")
#         os.makedirs(path, exist_ok=True)
#         temp_path = path
#         while temp_path != domain_path:
#             os.chmod(temp_path, 0o775)
#             temp_path = os.path.dirname(temp_path)
#         filename = os.path.join(path, filename)
#         with open(filename, 'wb') as html_file:
#             html_file.write(content)
#         filename_url = filename[:-5] + '.url'
#         with open(filename_url, 'w') as url_file:
#             url_file.write(url)
#         filename_source = filename[:-5] + '.src'
#         with open(filename_source, 'w') as source_file:
#             source_file.write(source)
#         new_html_filename = os.path.join(run_dir, 'new-html-files', 'new-html-files-{}.txt'.format(timestamp))
#         with open(new_html_filename, 'a') as new_html_file:
#             new_html_file.write(filename)
#             new_html_file.write("\n")
#         global nb_html_files
#         nb_html_files += 1
#     except OSError as os_err:
#         print("An error has occurred in write_html(path={0} filename={1} url={2}): {3}".format(path, filename, url, os_err))
# 
# 
# def write_stats_file(filename):
#     if nb_html_files_per_domain:
#         with open(filename, 'w') as stats_file:
#             json.dump(nb_html_files_per_domain, stats_file)
# 
# 
# def is_too_old(headers, limit_in_days=7):
#     json_data = json.loads(headers)
#     for key in json_data:
#         if key == 'last-modified' or key == 'Last-Modified' or key == 'Last-modified':
#             str_last_modif = json_data[key]
#             try:
#                 last_modif = datetime.datetime.strptime(str_last_modif, gmt_date_format)
#             except ValueError:
#                 try:
#                     last_modif = datetime.datetime.strptime(str_last_modif, utf_offset_date_format)
#                     last_modif = last_modif.replace(tzinfo=None)
#                 except ValueError:
#                     try:
#                         last_modif = datetime.datetime.strptime(str_last_modif, utf_offset_date_format_2)
#                         last_modif = last_modif.replace(tzinfo=None)
#                     except ValueError:
#                         # Give up,
#                         return False
#             delta = datetime.datetime.now() - last_modif
#             # Ignore pages that are older than a week.
#             if delta.days > limit_in_days:
#                 return True
#     return False
# 
# 
# def get_source(file, filename):
#     source_filename = os.path.join(file, filename[:-5] + '.src')
#     print("source_filename={}".format(source_filename))
#     if os.path.exists(source_filename):
#         with open(source_filename, 'r') as source_file:
#             source = source_file.read()
#         return source
#     return None
# 
# 
# def get_content(file, filename):
#     content_filename = os.path.join(file, filename[:-5] + '.html')
#     # print("content_filename={0}".format(content_filename))
#     if os.path.exists(content_filename):
#         with open(content_filename, 'rb') as content_file:
#             content_on_disk = content_file.read()
#         return content_on_disk
#     return None
# 
# 
# def get_all_versions(parent_dir, file_dir_prefix):
#     if not os.path.exists(parent_dir):
#         return []
# 
#     res = []
#     if file_dir_prefix == '':
#         res.append(parent_dir + "/")
# 
#     other_versions = glob.glob('{0}/{1}/[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9]-[0-9][0-9]-[0-9][0-9]'.format(parent_dir, file_dir_prefix).replace('//', '/'))
#     res += other_versions
# 
#     return res
# 
# 
# def is_content_similar_to_other_urls(content, urls_data, similarity_threshold):
#     for url_data in urls_data:
#         url, filename, parent_dir, file_dir_prefix, full_path = url_data
#         all_versions = sorted(get_all_versions(parent_dir, file_dir_prefix))
#         if len(all_versions) > 0:
#             # Only considerf the most recent version.
#             file = all_versions[-1]
#             if os.path.isdir(file):
#                 content_on_disk = get_content(file, filename)
#                 if content_on_disk is not None:
#                     seq = SequenceMatcher(a=content.decode('utf-8'), b=content_on_disk.decode('utf-8'))
#                     ratio = seq.quick_ratio()
#                     print(f"is_content_similar_to_other_urls url={url} if sim_ratio={ratio} > {similarity_threshold}? Discarded!")
#                     if ratio > similarity_threshold:
#                         return True
#     return False
# 
# 
# def is_similar_to_other_urls(url_to_check, urls):
#     for url in urls:
#         # Skip first characters that should be the same.
#         i = 0
#         while i < min(len(url), len(url_to_check)) and url[i] == url_to_check[i]:
#             i += 1
# 
#         seq = SequenceMatcher(a=url_to_check[i:], b=url[i:])
#         ratio = seq.ratio()
#         if ratio > 0.7:
#             print(f"is_similar_to_other_urls urls={url_to_check} vs {url} ratio={ratio}")
#             return True
#     print(f"is_similar_to_other_urls urls={url_to_check} -> False")
#     return False
# 
# 
# def process_file(filename, parent_dir, file_dir_prefix, same_as, url, content, db_file_basename, urls_with_title, full_path, domain_path, similarity_threshold):
#     print("process_file parent_dir={0} file_dir_prefix={1}".format(parent_dir, file_dir_prefix))
#     all_versions = sorted(get_all_versions(parent_dir, file_dir_prefix))
#     # print("all_versions={0}".format(all_versions))
# 
#     if len(all_versions) > 0:
#         # Now that we are using the similarity column from the database, I'm not convinced that
#         # the following code is useful. It looks redundant actually.
# 
#         # Only consider the most recent version.
#         file = all_versions[-1]
#         if os.path.isdir(file):
#             if same_as:
#                 source = get_source(file, filename)
#                 print("source={0} same_as={1} egal?={2}".format(source, same_as, (source == same_as)))
#                 if source is not None and source == same_as:
#                     return
# 
#             content_on_disk = get_content(file, filename)
#             if content_on_disk is not None:
#                 md5_content = hashlib.md5(content)
#                 md5_content_on_disk = hashlib.md5(content_on_disk)
#                 # print("content == content_on_disk? {}".format(content == content_on_disk))
#                 print("md5_content={0} md5_content_on_disk={1} equal? {2}".format(md5_content.hexdigest(), md5_content_on_disk.hexdigest(), md5_content.hexdigest() == md5_content_on_disk.hexdigest()))
#                 test = md5_content.hexdigest() == md5_content_on_disk.hexdigest()
#                 if test:
#                     return
# 
#     # Add the root_url to the urls_with_title so that we can detect doublons and skip them.
#     if content is not None:
#         soup = bs4.BeautifulSoup(content, 'html.parser')
#         title = soup.find('title')
#         if title is not None and title.string is not None:
#             stripped_title = title.string.strip()
#             question_mark_pos = url.find("?")
#             root_url = url[:question_mark_pos] if question_mark_pos != -1 else url
#             root_url = root_url.lower()
#             if stripped_title not in urls_with_title:
#                 urls_with_title[stripped_title] = {(root_url, filename, parent_dir, file_dir_prefix, full_path)}
#             else:
#                 urls_data = urls_with_title[stripped_title]
#                 urls = {data[0] for data in urls_data}
# 
#                 # Test if there is already a previous article with the same title and the same root_url.
#                 # If so, the current article is considered a doublon and is skipped.
#                 if root_url in urls or is_similar_to_other_urls(root_url, urls) or is_content_similar_to_other_urls(content, urls_data, similarity_threshold):
#                     doublon_urls.add((stripped_title, url))
#                     return
# 
#                 # The title is exactly like a previously processed file but the url
#                 # is different so it's assumed that they are different document.
#                 urls_data.add((root_url, filename, parent_dir, file_dir_prefix, full_path))
# 
#     source = same_as or db_file_basename
#     write_html_file(full_path, filename, url, content, source, domain_path)
# 
# 
# def perform_fact_checking(db_file, real_domain, region, db_file_basename, urls_with_title):
#     print("Check special urls for fact_checking.")
#     fact_checking_urls = ['https://fij.info/coronavirus-feature/national', 'https://fij.info/coronavirus-feature/overseas']
#     for url in fact_checking_urls:
#         print(f"Checking url={url}")
#         content = None
#         conn = sqlite3.connect(db_file)
#         try:
#             cursor = conn.cursor()
#             sql = f"select content from page where url='{url}';"
#             cursor.execute(sql)
#             record = cursor.fetchone()
#             content = record[0]
#         except sqlite3.DatabaseError as db_err:
#             print("An error has occurred: {0}".format(db_err))
#         finally:
#             conn.close()
# 
#         if content is not None:
#             soup = bs4.BeautifulSoup(content, 'html.parser')
# 
#             # Remove undesirable links.
#             for h4_tag in soup.find_all('h4', string="追記情報（ＦＩＪ）"):
#                 for p_tag in h4_tag.find_next_siblings('p'):
#                     p_tag.decompose()
# 
#             links = set(soup.find_all('a'))
#             external_hrefs = {link.get('href') for link in links if link.get('href').startswith('http') and not re.search("^http.*?fij.info/?.*", link.get('href'))}
# 
#             conn = sqlite3.connect(db_file)
#             try:
#                 cursor = conn.cursor()
#                 sql = (
#                     "select url, same_as, content, headers, similarity, maintext_similarity, compared_against from page "
#                     "where content_type like '%text/html%' and url in ({0})"
#                 ).format(','.join(["'{}'".format(href) for href in external_hrefs]))
#                 for row in cursor.execute(sql):
#                     process_row(row, real_domain, region, db_file_basename, urls_with_title, test_domain_and_subdomain=False)
#             except sqlite3.DatabaseError as db_err:
#                 print("An error has occurred: {0}".format(db_err))
#             finally:
#                 conn.close()
# 
# def process_row(row, real_domain, region, db_file_basename, urls_with_title, test_domain_and_subdomain=True, test_similarity=True, limit_in_days=7):
#     url = row[0]
#     same_as = row[1]
#     content = row[2]
#     headers = row[3]
#     similarity = row[4]
#     main_text_similarity = row[5]
#     compared_against = row[6]
# 
#     print("url: {0}".format(url))
# 
#     # Skip older files.
#     if is_too_old(headers, limit_in_days=limit_in_days):
#         print("url too old detected!!!: {}".format(url))
#         return
# 
#     # Skip blacklisted urls.
#     if is_blacklisted(url):
#         print("url blacklisted detected!!!: {}".format(url))
#         return
# 
#     # Consider only urls that match the domain_part or declared subdomains.
#     # print("url={0} same_as={1} isNone={2} isEmpty={3}".format(url, same_as, (same_as is None), same_as == ''))
#     if test_domain_and_subdomain:
#         domain_part = "^https?://{0}/(.*)".format(real_domain)
#         if 'prefix' in config['domains'][real_domain]:
#             domain_part = "^https?://{0}/(.*)".format(config['domains'][real_domain]['prefix'])
#         match = re.search(domain_part, url)
#         if match:
#             print(f"domain_part={domain_part} url={url} matched!!!")
#         else:
#             print("domain_part not matched so check subdomains")
#             if 'subdomains' not in config['domains'][real_domain]:
#                 print("url discarded because it's not matching the domain.")
#                 return
# 
#             subdomain_match = False
#             for subdomain in config['domains'][real_domain]['subdomains']:
#                 subdomain_part = "^https?://({0}/?.*)".format(subdomain)
#                 match = re.search(subdomain_part, url)
#                 if match:
#                     print(f"subdomain_part={subdomain_part} url={url} matched!!!")
#                     subdomain_match = True
#                     break
#             if not subdomain_match:
#                 print("url discarded because it's not matching the domain or subdomains.")
#                 return
#     else:
#         match = re.search("^https?://(.*)", url)
# 
#     # print("url={0} g0={1} g1={2}".format(url, match.group(0), match.group(1)))
#     path = match.group(1)
#     if path == '':
#         filename = '_'
#     else:
#         # Remove leading slashes.
#         while path.startswith('/'):
#             path = path[1:]
#         parts = path.split('/')
#         dirs = '/'.join(parts[:-1])
#         filename = parts[-1]
#         if filename == '':
#             filename = '_'
#         # print("mkdirs {}".format(dirs))
#     # print("filename {}".format(filename))
#     if filename.endswith('.htm'):
#         filename = filename[:-4] + '.html'
#     if not filename.endswith('.html'):
#         filename = filename + '.html'
#     domain_path = os.path.join(html_dir, region, 'orig', real_domain)
#     full_path = os.path.join(html_dir, region, 'orig', real_domain, path)
#     parent_dir = os.path.dirname(full_path)
#     file_dir_prefix = os.path.basename(full_path)
#     print("full_path {0} filename={1} parent_dir={2} file_dir_prefix={3}".format(full_path, filename, parent_dir, file_dir_prefix))
#     print("glob expr={0}/{1}*".format(parent_dir, file_dir_prefix))
# 
#     similarity_threshold = config['domains'][real_domain]['similarity_threshold'] if 'similarity_threshold' in config['domains'][real_domain] else config['default_similarity_threshold']
#     # Consider similarity when the file exists.
#     if os.path.exists(full_path) and test_similarity:
#         print("sim: {0} main_text_sim: {1} compared against: {2} sim_threshold={3}".format(similarity, main_text_similarity, compared_against, similarity_threshold))
#         if compared_against is not None and main_text_similarity >= similarity_threshold:
#             print("url too similar to previous version sim: {0} main_text_sim={1} sim_treshold={2}".format(similarity, main_text_similarity, similarity_threshold))
#             return
# 
#     process_file(filename, parent_dir, file_dir_prefix, same_as, url, content, db_file_basename, urls_with_title, full_path, domain_path, similarity_threshold)
# 
# 


def process_tweet(tweet_id, tweet_count, tweet_lang, tweet_country, tweet_json_str):
    tweet_json = json.loads(tweet_json_str)
    tweet_status = twitter.models.Status.NewFromJsonDict(tweet_json)
    try:
        tweet_country_code = utils.convert_country_to_iso_3166_alpha_2(tweet_country)
    except LookupError ex:
        print(ex)

    tweets[tweet_id] = {
        "count": tweet_count,
        "lang": tweet_lang,
        "country": tweet_country,
        "status": tweet_status
    }

    # Catch LookupError and notify erroneous country by email.

    print(f"id={tweet_id} count={tweet_count} lang={tweet_lang} country={tweet_country}")
    print(f"text={tweet_status.text}")
    print(f"full_text={tweet_status.full_text}")
    print(f"location={tweet_status.location}")
    print(f"place={tweet_status.place}")
    print(f"country={tweet_country}")
    print(f"2-alpha code={utils.convert_country_to_iso_3166_alpha_2(tweet_country)}")
    print(f"retweet_count={tweet_status.retweet_count}")
    print(f"lang={tweet_status.lang}")
    print(f"created_at={tweet_status.created_at}")
    print(f"hashtags={tweet_status.hashtags}")
    print(f"user={tweet_status.user}")
    print(f"urls={tweet_status.urls}")
    print(f"timestamp_in_secs={tweet_status.created_at_in_seconds}")
    print(f"timestamp_in_mils={tweet_json['timestamp_ms']}") # The milliseconds are lost when I convert from json to status.
    print(f"json={tweet_json}\n")


run_filename = os.path.join(run_dir, 'twitter.json')
for database_filename in os.listdir(twitter_db_dir):
    print(f"database_filename={database_filename}")
    if os.path.exists(run_filename):
        with open(run_filename, 'r') as run_file:
            run_data = json.load(run_file)
            print(f"run_data={run_data}")
            processed_databases = run_data

for db_filename in sorted(glob.glob(f'{twitter_db_dir}/tweets_*.txt')):
    print(f"Processing {db_filename}")

    tweets = {}
    tweet_count_per_country = {}

    with open(db_filename, 'r', encoding='latin-1') as twitter_data_file:
        for line in twitter_data_file:
            match = re.search("(\d+) (\d+) (\w+) ([-)'(\w]+) (\{.*\})", line)
            if match:
                tweet_id = match.group(1)
                tweet_count = match.group(2)
                tweet_lang = match.group(3)
                tweet_country = match.group(4)
                tweet_json_str = match.group(5)
                process_tweet(tweet_id, tweet_count, tweet_lang, tweet_country, tweet_json_str)
            else:
                print(f"Invalid line: {line}")

    processed_databases.append(os.path.basename(db_filename))
    # if os.path.exists(db_filename):
    #     os.remove(db_filename)

# with open(run_filename, 'w') as run_file:
#     json.dump(processed_databases, run_file)










# for domain in os.listdir(db_dir):
#     if domain.endswith('.html') or domain.endswith('.py') or domain.endswith('.py~') or domain.endswith(".jp"):
#         continue
# 
#     domain_dir = db_dir + '/' + domain
#     real_domain = domain.replace('_', '.')
#     # print("domain_dir={0} real_domain={1} input_domain={2}".format(domain_dir, real_domain, input_domain))
#     if input_domain != 'all' and real_domain != input_domain:
#         continue
# 
#     if real_domain not in config['domains']:
#         continue
# 
#     run_filename = os.path.join(run_dir, '{}.json'.format(real_domain))
#     if os.path.exists(run_filename):
#         with open(run_filename, 'r') as run_file:
#             run_data = json.load(run_file)
#             print("run_data for {0}={1}".format(real_domain, run_data))
#             processed_databases[real_domain] = run_data
# 
#     nb_html_files = 0
#     urls_with_title = {}
#     doublon_urls = set()
# 
#     lang = config['domains'][real_domain]['language']
#     region = config['domains'][real_domain]['region']
#     for db_file in sorted(glob.glob('{0}/*.db'.format(domain_dir))):
#         db_file_basename = os.path.basename(db_file)
#         if real_domain in processed_databases and db_file_basename in processed_databases[real_domain]:
#             continue
#         print("Processing {0}".format(db_file))
# 
#         conn = sqlite3.connect(db_file)
#         try:
#             cursor = conn.cursor()
#             sql = (
#                 "select url, same_as, content, headers, similarity, maintext_similarity, compared_against from page "
#                 "where content_type like '%text/html%'"
#             )
#             for row in cursor.execute(sql):
#                 process_row(row, real_domain, region, db_file_basename, urls_with_title)
#         except sqlite3.DatabaseError as db_err:
#             print("An error has occurred: {0}".format(db_err))
#         finally:
#             conn.close()
# 
#         if real_domain == 'fij.info':
#             perform_fact_checking(db_file, real_domain, region, db_file_basename, urls_with_title)
# 
#         nb_html_files_per_domain[real_domain] = nb_html_files
#         if real_domain in processed_databases:
#             processed_databases[real_domain].append(os.path.basename(db_file))
#         else:
#             processed_databases[real_domain] = [os.path.basename(db_file)]
# 
#         # if os.path.exists(db_file):
#         #    os.remove(db_file)
# 
#     with open(run_filename, 'w') as run_file:
#         json.dump(processed_databases[real_domain], run_file)
# 
#     print(f"urls_with_title ({len(urls_with_title)} items)")
#     for title in urls_with_title:
#         print(f"{title}: {urls_with_title[title]}")
#     print("===============")
# 
#     print(f"doublon_urls ({len(doublon_urls)} items)")
#     for url in doublon_urls:
#         print(f"{url}")
#     print("===============")
# 
#     print(f"nb_html_files={nb_html_files}")
# 
# stats_file = os.path.join(run_dir, 'stats', 'stats-{}.json'.format(now.strftime('%Y-%m-%d-%H-%M')))
# write_stats_file(stats_file)
