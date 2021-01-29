import bs4
import datetime
import json
import os
import re
import requests
from requests.auth import HTTPBasicAuth


def get_processed_databases():
    dbs = []
    run_filename = os.path.join(run_dir, "twitter.json")
    if os.path.exists(run_filename):
        with open(run_filename, 'r') as run_file:
            dbs = json.load(run_file)
    return dbs


def get_available_databases():
    dbs = []
    index_url = config['twitter']['crawled_data_repository']
    req = requests.get(index_url, auth=HTTPBasicAuth(config['twitter']['user'], config['twitter']['password']))
    if req.status_code == 200:
        soup = bs4.BeautifulSoup(req.text, 'html.parser')
        all_rows = soup.find_all('li')
        for row in all_rows:
            link = row.find('a').get('href')
            match = re.search('(\d\d\d\d-\d\d-\d\d-\d\d-\d\d)/', link)
            if match:
                dbs.append(match.group(1))
    # Remove the last entry because it's assumed that it's not been completely computed yet.
    return dbs[:-1]


def retrieve_database(database):
    print(f"Retrieving db: {database}")
    database_url = os.path.join(config['twitter']['crawled_data_repository'], database, 'rtjobs')
    print(f"db url: {database_url}")
    os.makedirs(os.path.join(db_dir, "twitter"), exist_ok=True)
    database_filename = os.path.join(db_dir, "twitter", f"tweets_{database}.txt")

    with requests.get(database_url, stream=True, auth=HTTPBasicAuth(config['twitter']['user'], config['twitter']['password'])) as req:
        req.raise_for_status()
        with open(database_filename, 'wb') as database_file:
            for chunk in req.iter_content(chunk_size=8192):
                database_file.write(chunk)
            print("File {} written.".format(database_filename))


config_filename = 'config.json'
with open(config_filename, 'r') as config_file:
    config = json.load(config_file)

db_dir = config['db_dir']
run_dir = config['run_dir']

now = datetime.datetime.now()

processed_dbs = get_processed_databases()
available_dbs = get_available_databases()
for db in available_dbs:
    if not db in processed_dbs:
        retrieve_database(db)
