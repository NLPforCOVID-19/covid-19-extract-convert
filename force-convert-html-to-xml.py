import datetime
from filelock import FileLock
import glob
import json
import logging
import logging.config
import os
import pathlib
import queue
import signal
import subprocess
import sys
import threading
import time
import traceback


def get_timestamp_from_filename(new_translated_file_fn):
    base_fn = os.path.basename(new_translated_file_fn)
    timestamp_str = base_fn[21:37]
    [yyyy, mm, dd, hh, mn] = timestamp_str.split('-')
    timestamp = datetime.datetime(int(yyyy), int(mm), int(dd), int(hh), int(mn))
    return timestamp


def signal_handler(sig, frame):
    print("Ctrl+C has been pressed. Let's stop the workers.")
    global stopped
    stopped = True
    for producer in producers:
        producer.stopped = True
    for convert in converters:
        convert.stopped = True
    print("The converter script should stop in a few moments.  Please be patient.")


class Producer(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.name = "Producer"
        self.stopped = False
        self.files_to_process = {}
        self.file_count = 0


    def process_translated_files_file(self, new_translated_files_file):
        logger.info(f"Processing {new_translated_files_file}...")
        with open(new_translated_files_file) as f:
            for line in f:

                if self.stopped:
                    return

                translated_file = line.strip()
                if translated_file == '':
                    continue

                # Consider only valid lines.
                if translated_file.startswith(html_dir) and translated_file.endswith(".html"):
                    region, _, domain, *url_parts = pathlib.Path(translated_file[len(html_dir) + 1:]).parts

                    url_filename = pathlib.Path(*url_parts)

                    www2sf_input_file = pathlib.Path(html_dir) / region / "ja_translated" / domain / url_filename
                    www2sf_output_file = pathlib.Path(xml_dir) / region / "ja_translated" / domain / url_filename.with_suffix('.xml')
                    logger.debug(f"www2sf_input_file={www2sf_input_file}")
                    logger.debug(f"www2sf_output_file={www2sf_output_file}")

                    logger.debug(f"Checking file: {www2sf_input_file}")

                    if not os.path.exists(www2sf_input_file):
                        logger.debug(f"Skip {www2sf_input_file} because it doesn't exist.")
                        continue

                    timestamp = datetime.datetime.fromtimestamp(os.stat(www2sf_input_file).st_mtime).strftime('%Y-%m-%d-%H-%M')
                    item = (www2sf_input_file, www2sf_output_file, timestamp)
                    if domain in self.files_to_process and item in self.files_to_process[domain]:
                        logger.debug(f"Skip {www2sf_input_file} because {www2sf_output_file} already registered.")
                        continue

                    logger.debug("Adding {} to files to process.".format(www2sf_input_file))
                    if domain not in self.files_to_process:
                        self.files_to_process[domain] = []
                    if item not in self.files_to_process[domain]:
                        self.files_to_process[domain].append(item)
                        self.file_count += 1

                    # break


    def run(self):
        global queue_html_files
        logger.info("Processing new-translated-files.txt files...")

        translated_files_files = glob.glob(os.path.join(run_dir, 'new-translated-files') + '/**/new-translated-files-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[0-9][0-9].txt', recursive=True)
        translated_files_files_in_period = [translated_file for translated_file in translated_files_files if (get_timestamp_from_filename(translated_file) >= start_date and get_timestamp_from_filename(translated_file) <= end_date)]

        sorted_translated_files_files = sorted(translated_files_files_in_period, key=get_timestamp_from_filename, reverse=True)
        # print("sorted_translated_files_files")
        # for i in translated_files_files_in_period:
        #     print(i)
        # print("-----------------------------")

        # for translated_files_file in sorted_translated_files_files[:1]:
        for translated_files_file in sorted_translated_files_files:

            self.process_translated_files_file(translated_files_file)

        logger.info("Finished processing translated-files.txt files.")

        for domain in self.files_to_process.keys():
            logger.info(f"domain={domain} len={len(self.files_to_process[domain])}")

        for domain in self.files_to_process.keys():
            for file in self.files_to_process[domain]:
                logger.info(f"Adding {file[0]} to queue.")
                queue_html_files.put((str(file[0]), str(file[1])))


class Converter(threading.Thread):

    def __init__(self, identifier, new_xml_files_dir):
        threading.Thread.__init__(self)
        self.name = "Converter: {}".format(identifier)
        self.identifier = identifier
        self.stopped = False
        self.new_xml_files_dir = new_xml_files_dir


    def run(self):
        global queue_html_files
        while True:
            try:
                if self.stopped:
                    logger.info("Converter {0} has been stopped.".format(self.identifier))
                    break

                if queue_html_files.empty():
                    break

                (www2sf_input_file, www2sf_output_file) = queue_html_files.get()
                logger.info("Process file: {}".format(www2sf_input_file))
                logger.info("Convert input={} output={}".format(www2sf_input_file, www2sf_output_file))
                logger.info("cd {0} && tool/html2sf.sh -T -D {1} -J {2}".format(www2sf_dir, detectblocks_dir, www2sf_input_file))
                process = subprocess.run(["tool/html2sf.sh", "-T", "-D {}".format(detectblocks_dir), "-J", www2sf_input_file], cwd=www2sf_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logger.info(f"return_code={process.returncode} for {www2sf_input_file}")
                if process.returncode == 0:
                    os.makedirs(www2sf_output_file[:www2sf_output_file.rindex('/')], exist_ok=True)
                    temp_path = www2sf_output_file[:www2sf_output_file.rindex('/')]
                    while temp_path != xml_dir:
                        # An error might happen when the folder owner is different from the user running the script.
                        # The permissions of such folders should already be ok so it's not needed to update them.
                        try:
                            os.chmod(temp_path, 0o775)
                        except OSError as e:
                            break
                        temp_path = os.path.dirname(temp_path)

                    with open(www2sf_output_file, "wb") as xml_file:
                        xml_file.write(process.stdout)
                    logger.info("Output file {}: OK".format(www2sf_output_file))

                    new_xml_filename = os.path.join(run_dir, 'new-xml-files', 'new-xml-files-{0}.txt'.format(now.strftime('%Y-%m-%d-%H-%M')))
                    new_xml_file_lock = "{0}.lock".format(new_xml_filename)
                    with FileLock(new_xml_file_lock):
                        with open(new_xml_filename, 'a') as f:
                            f.write("{0}\n".format(www2sf_output_file))
                    mutex.acquire()
                    try:
                        processed_files.append(www2sf_output_file)
                    finally:
                        mutex.release()
                queue_html_files.task_done()

            except:
                # e = sys.exc_info()[0]
                # logger.info("An error has occurred: %s" % e)
                logger.info("An error has occurred: %s" % traceback.format_exc())


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Launch the converter.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--config", help="Location of config file.", type=str, default="config.json")
    parser.add_argument("--log_config", help="Log configuration file.", type=str, default="force_converter_logging.conf")
    parser.add_argument("start_date", nargs='?', default=None)
    parser.add_argument("end_date", nargs='?', default=None)
    args = parser.parse_args(args=None)

    config_filename = args.config
    logging.config.fileConfig(args.log_config)
    logger = logging.getLogger('default')

    signal.signal(signal.SIGINT, signal_handler)
    print("Hit CTRL+C and wait a little bit to stop the converter.")

    logger.info("Start running.")
    stopped = False
    while not stopped:
        logger.info("Start iteration.")
        with open(config_filename, 'r') as config_file:
            config = json.load(config_file)

        html_dir = config['html_dir']
        xml_dir = config['xml_dir']
        run_dir = config['run_dir']
        new_xml_files_dir = "{0}/new-xml-files".format(run_dir)
        www2sf_dir = config['WWW2sf_dir']
        detectblocks_dir = config['detectblocks_dir']

        now = datetime.datetime.now()
        ts_now = datetime.datetime.fromtimestamp(time.time())

        start_date = args.start_date
        end_date = args.end_date
        print(f"start_date={start_date}")
        print(f"end_date={end_date}")

        [yyyy, mm, dd] = start_date.split('-')
        start_date = datetime.datetime(int(yyyy), int(mm), int(dd))
        [yyyy, mm, dd] = end_date.split('-')
        end_date = datetime.datetime(int(yyyy), int(mm), int(dd))
        print(f"start_date={start_date}")
        print(f"end_date={end_date}")

        queue_html_files = queue.Queue()

        processed_files = []

        mutex = threading.Lock()

        producers = []
        converters = []

        producer = Producer()
        producers.append(producer)
        producer.start()

        for producer in producers:
            producer.join()

        # converter_count = 1
        converter_count = 40
        for c in range(0, converter_count):
            converter = Converter(c, new_xml_files_dir)
            converters.append(converter)
            converter.start()

        for converter in converters:
            converter.join()

        logger.info("Number of new xml files: {0}".format(len(processed_files)))

        logger.info("Iteration over.")

        stopped = True

        # # Wait 1 hour before next iteration.
        # time.sleep(60 * 60)

    logger.info("Stop running.")
