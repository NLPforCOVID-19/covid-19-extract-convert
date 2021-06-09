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
    return dbs


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

retrieved_dbs_count = 0
processed_dbs = get_processed_databases()
available_dbs = get_available_databases()
# Process the latest dbs first.
for index, db in enumerate(reversed(available_dbs)):
    # Even if the last db has already been processed, it must be
    # processed again because it's been updated with new data.
    if not db in processed_dbs or index == 0:
        retrieve_database(db)
        retrieved_dbs_count += 1
        # Get out after enough dbs have been processed.
        # This allows to refresh latest data while processing older dbs.
        if retrieved_dbs_count >= 3:
            break
