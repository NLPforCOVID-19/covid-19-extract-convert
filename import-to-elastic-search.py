from datetime import date, datetime, timedelta
from elastic_search_utils import ElasticSearchImporter
import json
import logging
import logging.config
import os
import queue
import random
import signal
import sys
import threading


def signal_handler(sig, frame):
    print("Ctrl+C has been pressed. Let's stop the workers.")
    global stopped
    stopped = True
    for producer in producers:
        producer.stopped = True
    for convert in importers:
        convert.stopped = True
    print("The importation script should stop in a few moments.  Please be patient.")


def datetime_from_path(input_file):
    global logger
    logger.info(f"datetime_from_path input_file={input_file}")
    dirs = input_file[len(html_dir) + 1:].split("/")
    logger.info(f"dirs={dirs}")
    region = dirs[0]
    domain = dirs[2]

    path = "/".join(dirs[3:-4])
    logger.info(f"region={region} domain={domain} path={path}")

    timestamp_year = dirs[-4]
    timestamp_month = dirs[-3]
    timestamp_day_time = dirs[-2]
    logger.info(f"timestamp_day_time={timestamp_day_time}")

    timestamp_parts = timestamp_day_time.split("-")
    # Ignore files using the old path formats.
    if len(timestamp_parts) > 3:
        logger.info(f"Old path format found: {input_file}")
        return None

    timestamp_day, timestamp_hh, timestamp_mm = timestamp_parts
    
    timestamp_local = datetime(int(timestamp_year), int(timestamp_month), int(timestamp_day), int(timestamp_hh), int(timestamp_mm))
    
    return timestamp_local

class ShuffableQueue(queue.Queue):
    def shuffle(self):
        random.shuffle(self.queue)


class Producer(threading.Thread):

    def __init__(self, lang, region, period_start):
        threading.Thread.__init__(self)
        self.name = f"Producer for region {region}"
        self.lang = lang
        self.region = region
        self.period_start = period_start
        self.stopped = False
        self.files_to_process = {}

    def run(self):
        global queue_files_to_import
        logger.info(f"Processing files from region: {self.region}...")
        root_input_dir = f"{self.region}/{self.lang}_translated"

        root_abs_input_dir = os.path.join(html_dir, root_input_dir)
        if os.path.exists(root_abs_input_dir):
            for domain in os.listdir(root_abs_input_dir):
                logger.info(f"Processing domain: {domain}...")
                self.files_to_process[domain] = []
                for top, dirs, files in os.walk(os.path.join(root_abs_input_dir, domain)):
                    # logger.debug(f"top={top} dirs={dirs} files={files}")
                    for file in files:

                        if self.stopped:
                            logger.info(f"Producer for region {self.region} has been stopped.")
                            return

                        if file.endswith('.txt'):
                            abs_path = os.path.join(top, file)
                            # logger.info(f"abs_path={abs_path}") 
                            
                            file_timestamp = datetime_from_path(abs_path)
                            if file_timestamp is not None:
                                file_timestamp_str = file_timestamp.strftime('%Y-%m-%d-%H-%M')
                                is_accepted = file_timestamp >= period_start and file_timestamp < now
                                if (is_accepted):
                                    # logger.info(f"Adding {file} to queue.")
                                    logger.info(f"Timestamp: {file_timestamp_str} so adding {abs_path} to queue.")
                                    queue_files_to_import.put(abs_path)

        logger.info(f"Finished processing files from region: {self.region}...")


class Importer(threading.Thread):

    def __init__(self, identifier, elastic_search_handler):
        threading.Thread.__init__(self)
        self.name = f"Importer: {identifier}"
        self.identifier = identifier
        self.stopped = False
        self.elastic_search_handler = elastic_search_handler

    def run(self):
        global queue_files_to_import
        while True:
            try:
                if self.stopped:
                    logger.info(f"Importer {self.identifier} has been stopped.")
                    break

                if queue_files_to_import.empty():
                    break

                file_to_import = queue_files_to_import.get()
                logger.info(f"Process file: {file_to_import}")
                record_id = self.elastic_search_handler.update_record(file_to_import)
                if record_id is not None:
                    mutex.acquire()
                    try:
                        added_records.add(record_id)
                    finally:
                        mutex.release()

                mutex.acquire()
                try:
                    processed_files.append(file_to_import)
                finally:
                    mutex.release()
                queue_files_to_import.task_done()

            except:
                e = sys.exc_info()[0]
                logger.info("An error has occurred: %s" % e)


def check_positive(value):
    int_value = int(value)
    if int_value < 0:
        raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
    return int_value


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Launch the importer.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--config", help="Location of config file.", type=str, default="config.json")
    parser.add_argument("--log_config", help="Log configuration file.", type=str, default="es_importer_logging.conf")
    parser.add_argument("--days", help="Age of files (in days) that need to be imported.", default=0, type=check_positive)
    parser.add_argument("lang", help="Language of the files to process.")
    args = parser.parse_args(args=None)

    config_filename = args.config

    logging.config.fileConfig(args.log_config)
    logger = logging.getLogger('default')

    with open(config_filename, 'r') as config_file:
        config = json.load(config_file)

    if 'elastic_search' not in config:
        sys.exit(1)

    elastic_search_handler = ElasticSearchImporter(
        config['elastic_search']['host'], 
        config['elastic_search']['port'], 
        f"{config['elastic_search']['index_basename']}-{args.lang}",
        config['html_dir'],
        args.lang,
        logger
    )

    index_period = config['elastic_search']['index_period']

    html_dir = config['html_dir']
    run_dir = config['run_dir']

    signal.signal(signal.SIGINT, signal_handler)
    print("Hit CTRL+C and wait a little bit to stop the importer.")

    logger.info("Start running.")
    stopped = False
    while not stopped:
        logger.info("Start iteration.")
        
        now = datetime.now()

        if args.days == 0:
            # Try to fetch the date of the last import first.
            # If found, use it otherwise use the index_period.
            period_start = now - timedelta(index_period)
        elif args.days > 0:
            period_start = now - timedelta(days=args.days)
        period_start = datetime(period_start.year, period_start.month, period_start.day, 0, 0)
        logger.info(f"period_start={period_start}")

        queue_files_to_import = ShuffableQueue()

        processed_files = []
        added_records = set()

        mutex = threading.Lock()

        producers = []
        importers = []

        for region in os.listdir(html_dir):
            # if region != 'cn':
            #     continue
            producer = Producer(args.lang, region, period_start)
            producers.append(producer)
            producer.start()

        for producer in producers:
            producer.join()

        # To reduce concurrency hazards, I shuffle the files from the queue.
        # Not doing so makes it very likely that some older record will be stored in the index.
        # Shuffling the files is not 100% perfect but it should be good enough.
        queue_files_to_import.shuffle() 

        importer_count = 40
        for c in range(0, importer_count):
            importer = Importer(c, elastic_search_handler)
            importers.append(importer)
            importer.start()

        for importer in importers:
            importer.join()

        logger.info(f"Number of new processed files: {len(processed_files)}")
        
        logger.info("Iteration over.")

        stopped = True

    logger.info("Stop running.")

    logger.info(f"processed_files={len(processed_files)}")
    for f in processed_files:
        logger.info(f)

    logger.info(f"added_records={len(added_records)}")
    for f in added_records:
        logger.info(f)


