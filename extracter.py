import argparse
import json
import logging
import logging.config
import threading
import traceback


class DatabaseMonitor(threading.Thread):

    def __init__(self, config_filename):
        threading.Thread.__init__(self)

    def run(self):
        while True:
            try:
            except:
                (typ, val, tb) = sys.exc_info()
                error_msg = "An exception occurred in the ChatroomCleaner:\n"
                for line in traceback.format_exception(typ, val, tb):
                    error_msg += line + "\n"
                self.logger.debug(error_msg)
    with open(args.config, 'r') as config_file:
        config = json.load(config_file)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--config", default="config.json", help="Path to configuration file.")
    argparser.add_argument("--log_config", help="Log configuration file.", type=str, default="extracter_logging.conf")
    args = argparser.parse_args()

    # database_monitor = DatabaseMonitor(args.config)
    # database_monitor.start()
