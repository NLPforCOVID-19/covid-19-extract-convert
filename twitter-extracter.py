import argparse
import datetime
import json
import logging
import logging.config
import os
import signal
import subprocess
import sys
import threading
from threading import Event
import time
import traceback


# Number of seconds to wait before checking again for new twitter data.
INTER_CHECKS_DELAY = 60 * 60 * 2

exit = Event()


def signal_handler(sig, frame):
    print("Ctrl+C has been pressed. The script should stop in a few minutes. Please be patient.")
    exit.set()


class Extracter(threading.Thread):

    def __init__(self, logger, run_dir):
        threading.Thread.__init__(self)
        self.logger = logger
        self.run_dir = run_dir

    def run(self):
        start = datetime.datetime.now()
        start_timestamp = start.strftime('%Y-%m-%d-%H-%M')

        self.logger.info(f"Starting twitter extraction at {start_timestamp}...")
        cmd = ['nice ./get-covid19-twitter-db-and-html.sh']
        output = None
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError as err:
            self.logger.info(f"The extraction of twitter data resulted in a non-zero return code: {err.returncode}")
            if err.output:
                output = err.output

        if output:
            report_path = f'{self.run_dir}/twitter-extracter'
            os.makedirs(report_path, exist_ok=True, mode=775)
            report_filename = f'{report_path}/extracter_{start_timestamp}.txt'
            with open(report_filename, 'wb') as report_file:
                report_file.write(output)

        stop = datetime.datetime.now()
        stop_timestamp = stop.strftime('%Y-%m-%d-%H-%M')
        self.logger.info(f"Twitter extraction terminated at {stop_timestamp}.")
        extracter = None


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--config", default="config.json", help="Path to configuration file.")
    argparser.add_argument("--log_config", help="Log configuration file.", type=str, default="twitter_extracter_logging.conf")
    args = argparser.parse_args()

    logging.config.fileConfig(args.log_config)
    logger = logging.getLogger('default')

    signal.signal(signal.SIGINT, signal_handler)
    print("Hit CTRL+C and wait a until the script stops.")

    extracter = None

    while not exit.is_set():

       try:

            with open(args.config, 'r') as config_file:
                config = json.load(config_file)

            run_dir = config['run_dir']

            extracter = Extracter(logger, run_dir)
            extracter.start()
            extracter.join()

            if not exit.is_set():
                exit.wait(INTER_CHECKS_DELAY)

       except:
           (typ, val, tb) = sys.exc_info()
           error_msg = "An exception occurred in the main thread of the extracter:\n"
           for line in traceback.format_exception(typ, val, tb):
               error_msg += line + "\n"
           self.logger.debug(error_msg)

