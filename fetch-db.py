import datetime
import json
import os
import re
import requests
import sqlite3
import sys

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
        for line in req.text.splitlines():
            match = re.search('a href="\./(.*?\.db)', line)
            if match:
                db_filename = match.group(1)
                dbs.append(db_filename)
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

for domain in config['domains']:
    if input_domain != 'all' and domain != input_domain:
        continue

    print("Processing domain: {}...".format(domain))
    processed_dbs = get_processed_databases(domain)
    available_dbs = get_available_databases(domain)
    for db in available_dbs:
        if not db in processed_dbs:
            retrieve_database(domain, db)
