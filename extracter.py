import argparse
import datetime
import json
import logging
import logging.config
import os
import re
import requests
import signal
import subprocess
import sys
import threading
import time
import traceback


# Wait a while before extracting another domain (to let it finish).
INTER_DOMAIN_DELAY = 60

# Wait a while before checking all the domains again.
INTER_DOMAINS_DELAY = 150

def signal_handler(sig, frame):
    print("Ctrl+C has been pressed. Let's stop the workers.")
    global stopped
    stopped = True
    print("The script should stop in a few moments.  Please be patient.")


class Extracter(threading.Thread):

    def __init__(self, domain, logger, run_dir):
        threading.Thread.__init__(self)
        self.domain = domain
        self.logger = logger
        self.run_dir = run_dir

    def run(self):
        start = datetime.datetime.now()
        start_timestamp = start.strftime('%Y-%m-%d-%H-%M')

        self.logger.info("Starting extraction for domain {0} at {1}...".format(self.domain, start_timestamp))
        cmd = ['nice ./get-covid19-db-and-html.sh {0}'.format(self.domain)]
        output = None
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError as err:
            self.logger.info("The extraction of domain: {0} resulted in a non-zero return code: {1}".format(self.domain, err.returncode))
            if err.output:
                output = err.output

        if output:
            report_path = '{0}/extracter/{1}'.format(self.run_dir, self.domain)
            os.makedirs(report_path, exist_ok=True)
            report_filename = '{0}/extracter_{1}.txt'.format(report_path, start_timestamp)
            with open(report_filename, 'wb') as report_file:
                report_file.write(output)

        stop = datetime.datetime.now()
        stop_timestamp = stop.strftime('%Y-%m-%d-%H-%M')
        self.logger.info("Extraction terminated for domain {0} at {1}.".format(self.domain, stop_timestamp))
        terminate_extracter(self.domain)


def terminate_extracter(domain):
    mutex.acquire()
    try:
        if domain in extracters:
            del extracters[domain]
    finally:
        mutex.release()


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--config", default="config.json", help="Path to configuration file.")
    argparser.add_argument("--log_config", help="Log configuration file.", type=str, default="extracter_logging.conf")
    args = argparser.parse_args()

    logging.config.fileConfig(args.log_config)
    logger = logging.getLogger('default')

    signal.signal(signal.SIGINT, signal_handler)
    print("Hit CTRL+C and wait a little bit to stop the script.")

    mutex = threading.Lock()
    extracters = {}

    stopped = False
    while not stopped:

       try:

            with open(args.config, 'r') as config_file:
                config = json.load(config_file)

            run_dir = config['run_dir']

            for domain in config['domains']:

                pause = 0

                if stopped:
                    break

                mutex.acquire()
                try:
                    # If an extracter is already working for the domain, skip it for now.
                    if domain in extracters:
                        continue

                    extracter = Extracter(domain, logger, run_dir)
                    extracters[domain] = extracter
                    extracter.start()

                    pause = INTER_DOMAIN_DELAY

                finally:
                    mutex.release()

                if stopped:
                    break

                if pause > 0:
                    time.sleep(pause)

            if not stopped:
                time.sleep(INTER_DOMAINS_DELAY)

       except:
           (typ, val, tb) = sys.exc_info()
           error_msg = "An exception occurred in the main thread of the extracter:\n"
           for line in traceback.format_exception(typ, val, tb):
               error_msg += line + "\n"
           self.logger.debug(error_msg)
