import argparse
import json
import logging
import logging.config
import os
import re
import requests
import signal
import sys
import threading
import time
import traceback


def signal_handler(sig, frame):
    print("Ctrl+C has been pressed. Let's stop the workers.")
    global stopped
    stopped = True
    database_monitor.stopped = True
    print("The script should stop in a few moments.  Please be patient.")


class DatabaseMonitor(threading.Thread):


    def __init__(self, config_filename, logger):
        threading.Thread.__init__(self)
        self.config_filename = config_filename
        self.logger = logger
        self.stopped = True


    def run(self):
        self.stopped = False
        while not self.stopped:
            try:
                with open(self.config_filename, 'r') as config_file:
                    config = json.load(config_file)

                db_dir = config['db_dir']
                run_dir = config['run_dir']
                for domain in config['domains']:

                    if self.stopped:
                        break

                    self.logger.info("Checking availability of new database for domain {0}...".format(domain))

                    if not self.stopped:
                        processed_dbs = self.get_processed_databases(domain, run_dir)
                        self.logger.info("Processed databases: {0}".format(len(processed_dbs)))
                        self.logger.debug("processed_dbs={0}".format(processed_dbs))

                    if not self.stopped:
                        available_dbs = self.get_available_databases(domain, config)
                        self.logger.info("Available databases: {0}".format(len(available_dbs)))
                        self.logger.debug("available_dbs={0}".format(available_dbs))

                    for db in available_dbs:
                        if not db in processed_dbs and not self.stopped:
                            self.retrieve_database(domain, db, config, db_dir)

                    if not self.stopped:
                        time.sleep(60)

            except:
                (typ, val, tb) = sys.exc_info()
                error_msg = "An exception occurred in the DatabaseMonitor:\n"
                for line in traceback.format_exception(typ, val, tb):
                    error_msg += line + "\n"
                self.logger.debug(error_msg)


    def get_processed_databases(self, domain, run_dir):
        dbs = []
        run_filename = os.path.join(run_dir, "{}.json".format(domain))
        if os.path.exists(run_filename):
            with open(run_filename, 'r') as run_file:
                dbs = json.load(run_file)
        return dbs


    def get_available_databases(self, domain, config):
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


    def retrieve_database(self, domain, database, config, db_dir):
        print("Retrieving db: {}".format(database))
        domain_dir = domain.replace('.', '_')

        if 'prefix' in config['domains'][domain]:
            database_url = os.path.join(config['crawled_data_repository'], config['domains'][domain]['prefix'].replace('.', '_'), database)
        else:
            database_url = os.path.join(config['crawled_data_repository'], domain.replace('.', '_'), database)
        print("db url: {}".format(database_url))
        os.makedirs(os.path.join(db_dir, domain_dir), exist_ok=True)
        database_filename = os.path.join(db_dir, domain_dir, database)
        with requests.get(database_url, stream=True) as req:
            req.raise_for_status()
            with open(database_filename, 'wb') as database_file:
                for chunk in req.iter_content(chunk_size=8192):
                    database_file.write(chunk)
                print("File {} written.".format(database_filename))


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--config", default="config.json", help="Path to configuration file.")
    argparser.add_argument("--log_config", help="Log configuration file.", type=str, default="extracter_logging.conf")
    args = argparser.parse_args()

    logging.config.fileConfig(args.log_config)
    logger = logging.getLogger('default')

    signal.signal(signal.SIGINT, signal_handler)
    print("Hit CTRL+C and wait a little bit to stop the script.")

    stopped = False

    database_monitor = DatabaseMonitor(args.config, logger)
    database_monitor.start()

