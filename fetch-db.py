import bs4
import datetime
import json
import os
import re
import requests
import sqlite3
import sys
import utils

max_attempts = 10

def get_processed_databases(domain):
    dbs = []
    run_filename = os.path.join(run_dir, "{}.json".format(domain))
    if os.path.exists(run_filename):
        with open(run_filename, 'r') as run_file:
            dbs = json.load(run_file)
    return dbs


def get_available_databases(domain):
    dbs = []
    if 'prefix' in config['domains'][domain]:
        index_url = '{0}/{1}'.format(config['crawled_data_repository'], config['domains'][domain]['prefix'].replace('.', '_'))
    else:
        index_url = '{0}/{1}'.format(config['crawled_data_repository'], domain.replace('.', '_'))
    req = requests.get(index_url)
    if req.status_code == 200:
        soup = bs4.BeautifulSoup(req.text, 'html.parser')
        all_rows = soup.find_all('tr')
        for row in all_rows:
            cols = row.find_all('td')
            if len(cols) == 3:
                db_name = cols[0].find('a').get('href')
                size_txt = cols[1].get_text()

                match = re.match("^([0-9]+) [A-Za-z]+$", size_txt)
                if match:
                    try:
                        size = int(match.group(1))
                        dbs.append((db_name, size))
                    except ValueError:
                        # Skip this row if the size is not a number.
                        break
    return dbs


def retrieve_database(domain, database):
    print("Retrieving db: {}".format(database))
    domain_dir = domain.replace('.', '_')

    if 'prefix' in config['domains'][domain]:
        database_url = os.path.join(config['crawled_data_repository'], config['domains'][domain]['prefix'].replace('.', '_'), database)
    else:
        database_url = os.path.join(config['crawled_data_repository'], domain.replace('.', '_'), database)
    print("db url: {}".format(database_url))
    os.makedirs(os.path.join(db_dir, domain_dir), exist_ok=True)
    database_filename = os.path.join(db_dir, domain_dir, database)
    
    attempt = 1
    while attempt <= max_attempts:
        with requests.get(database_url, stream=True) as req:
            req.raise_for_status()
            with open(database_filename, 'wb') as database_file:
                for chunk in req.iter_content(chunk_size=8192):
                    database_file.write(chunk)
                print("File {} written.".format(database_filename))

        conn = sqlite3.connect(database_filename)
        try:
            cursor = conn.cursor()
            sql = (
                "select count(url) as count from page where content_type like '%text/html%'"
            )
            for row in cursor.execute(sql):
                print("Records in the database: {0}".format(row[0]))
        except sqlite3.DatabaseError as db_err:
            print("An error has occurred while testing the database on attempt {0}: {1}".format(attempt, db_err))
            attempt += 1
            continue
        finally:
            conn.close()
        return


input_domain = sys.argv[1]

config_filename = sys.argv[2] if len(sys.argv) == 3 else 'config.json'
with open(config_filename, 'r') as config_file:
    config = json.load(config_file)

db_dir = config['db_dir']
run_dir = config['run_dir']

now = datetime.datetime.now()

empty_databases = {}
empty_databases_filename = f'{run_dir}/empty_databases.json'
if os.path.exists(empty_databases_filename):
    with open(empty_databases_filename, 'r') as empty_databases_file:
        empty_databases = json.load(empty_databases_file)

new_empty_databases = {}

for domain in config['domains']:
    if input_domain != 'all' and domain != input_domain:
        continue

    print("Processing domain: {}...".format(domain))
    processed_dbs = get_processed_databases(domain)
    available_dbs = get_available_databases(domain)
    for db, size in available_dbs:
        if not db in processed_dbs:
            if size == 0:
                # If the notification has already been sent, no need to send it again.
                if domain in empty_databases and db in empty_databases[domain]:
                    continue

                if domain not in new_empty_databases:
                    new_empty_databases[domain] = [db]
                else:
                    new_empty_databases[domain].append(db)
            else:
                retrieve_database(domain, db)

if len(new_empty_databases) > 0:
    # Filter unwanted domains before sending notifications of empty databases.
    empty_databases_to_notify = {}
    for domain in new_empty_databases:
        if 'notif_empty_db_disabled' not in config['domains'][domain] or not config['domains'][domain]['notif_empty_db_disabled']:
            empty_databases_to_notify[domain] = new_empty_databases[domain]
    if (empty_databases_to_notify):
        utils.send_mail(config['mail']['from'],
            None if 'to' not in config['mail'] else config['mail']['to'],
            None if 'cc' not in config['mail'] else config['mail']['cc'],
            None if 'bcc' not in config['mail'] else config['mail']['bcc'],
            "Empty databases were found", str(empty_databases_to_notify))

    for domain in new_empty_databases:
        for db in new_empty_databases[domain]:
            if domain not in empty_databases:
                empty_databases[domain] = [db]
            else:
                empty_databases[domain].append(db)
    with open(empty_databases_filename, 'w', encoding='utf8') as updated_empty_databases_file:
        json.dump(empty_databases, updated_empty_databases_file)
