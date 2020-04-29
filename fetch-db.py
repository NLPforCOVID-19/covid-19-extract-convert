import datetime
import json
import os
import re
import requests
import sys


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
    database_url = os.path.join(config['crawled_data_repository'], domain_dir, database)
    os.makedirs(os.path.join(db_dir, domain_dir), exist_ok=True)
    database_filename = os.path.join(db_dir, domain_dir, database)
    req = requests.get(database_url, stream=True)
    with open(database_filename, 'wb') as database_file:
        for chunk in req.iter_content(chunk_size=1024):
            database_file.write(chunk)
        print("File {} written.".format(database_filename))


config_filename = sys.argv[1] if len(sys.argv) == 2 else 'config.json'
with open(config_filename, 'r') as config_file:
    config = json.load(config_file)

db_dir = config['db_dir']
run_dir = config['run_dir']

now = datetime.datetime.now()

for domain in config['domains']:
    print("Processing domain: {}...".format(domain))
    processed_dbs = get_processed_databases(domain)
    available_dbs = get_available_databases(domain)
    for db in available_dbs:
        if not db in processed_dbs:
            retrieve_database(domain, db)
