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


max_file_count = 1000
max_file_count_per_domain = 200


def get_timestamp_from_filename(new_html_file_fn):
    base_fn = os.path.basename(new_html_file_fn)
    timestamp_str = base_fn[15:31]
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


def get_unconvertable_files(new_xml_files_dir):
    files = set()
    unconvertable_filename = "{0}/unconvertable_files.txt".format(new_xml_files_dir)
    if os.path.exists(unconvertable_filename):
        with open(unconvertable_filename, 'r') as f:
            entries = f.read().splitlines()
            for entry in entries:
                files.add(entry)
    return files


# For some reasons (like the script was killed abruptly), some xml files have
# not been reported even though they have been converted.
# Eventually, we should report these files?
# For the moment, we skip these as they already
def get_unreferred_files(new_xml_files_dir):
    files = set()
    unreferred_filename = "{0}/already_converted_but_unreferred_files.txt".format(new_xml_files_dir)
    if os.path.exists(unreferred_filename):
        with open(unreferred_filename, 'r') as f:
            entries = f.read().splitlines()
            for entry in entries:
                files.add(entry)
    return files


def get_processed_files(new_xml_files_dir):
    files = set()

    for new_xml_file in glob.glob("{0}/new-xml-files*.txt".format(new_xml_files_dir)):
        with open(new_xml_file, 'r') as f:
            xml_entries = f.read().splitlines()
        for entry in xml_entries:
            files.add(entry)

    for entry in unreferred_files:
        files.add(entry)

    return files

class Producer(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.name = "Producer"
        self.stopped = False
        self.files_to_process = {}
        self.file_count = 0


    def process_new_html_files_file(self, new_html_files_file):
        with open(new_html_files_file) as f:
            for line in f:

                if self.stopped:
                    return

                html_file = line.strip()
                if html_file == '':
                    continue

                # Consider only valid lines.
                if html_file.startswith(html_dir) and html_file.endswith(".html"):
                    region, _, domain, *url_parts = pathlib.Path(html_file[len(html_dir) + 1:]).parts

                    if self.file_count < max_file_count and (domain not in self.files_to_process or len(self.files_to_process[domain]) < max_file_count_per_domain):
                        url_filename = pathlib.Path(*url_parts)

                        www2sf_input_file = pathlib.Path(html_dir) / region / "ja_translated" / domain / url_filename
                        www2sf_output_file = pathlib.Path(xml_dir) / region / "ja_translated" / domain / url_filename.with_suffix('.xml')
                        logger.debug(f"www2sf_input_file={www2sf_input_file}")
                        logger.debug(f"www2sf_output_file={www2sf_output_file}")

                        logger.debug(f"Checking file: {www2sf_input_file}")

                        if not os.path.exists(www2sf_input_file):
                            logger.debug(f"Skip {www2sf_input_file} because it doesn't exist.")
                            continue

                        if www2sf_input_file in unconvertable_files:
                            logger.debug(f"Skip {www2sf_input_file} because it's flagged as unconvertable.")
                            continue

                        if www2sf_output_file in prev_processed_files:
                            logger.debug(f"Skip {www2sf_output_file} because already processed.")
                            continue

                        if os.path.exists(www2sf_output_file):
                            logger.debug(f"Skip {www2sf_input_file} because {www2sf_output_file} already exists.")
                            continue

                        timestamp = datetime.datetime.fromtimestamp(os.stat(www2sf_input_file).st_mtime).strftime('%Y-%m-%d-%H-%M')
                        item = (www2sf_input_file, www2sf_output_file, timestamp)
                        if domain in self.files_to_process and item in self.files_to_process[domain]:
                            logger.debug(f"Skip {www2sf_input_file} because {www2sf_output_file} already registered.")
                            continue

                        logger.debug("Adding {} to files to process.".format(www2sf_input_file))
                        if domain not in self.files_to_process:
                            self.files_to_process[domain] = []
                        self.files_to_process[domain].append(item)
                        self.file_count += 1

                        if self.file_count >= max_file_count or len(self.files_to_process[domain]) >= max_file_count_per_domain:
                            return



    def run(self):
        global queue_html_files
        logger.info("Processing new-html-files.txt files...")

        new_html_files_files = glob.glob(os.path.join(run_dir, 'new-html-files') + '/**/new-html-files-*.txt', recursive=True)
        recent_new_html_files_files = [new_html_file for new_html_file in new_html_files_files if (now - get_timestamp_from_filename(new_html_file)).days < 2]
        sorted_new_html_files_files = sorted(recent_new_html_files_files, key=get_timestamp_from_filename, reverse=True)

        for new_html_files_file in sorted_new_html_files_files:

            self.process_new_html_files_file(new_html_files_file)
            if self.file_count >= max_file_count:
                break

        logger.info("Finished processing new-html-files.txt files.")

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
                if not os.path.exists(www2sf_output_file):
                    logger.info("Convert input={} output={}".format(www2sf_input_file, www2sf_output_file))
                    logger.info("cd {0} && tool/html2sf.sh -T -D {1} -J {2}".format(www2sf_dir, detectblocks_dir, www2sf_input_file))
                    process = subprocess.run(["tool/html2sf.sh", "-T", "-D {}".format(detectblocks_dir), "-J", www2sf_input_file], cwd=www2sf_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    logger.info("return_code={0}".format(process.returncode))
                    if process.returncode == 0:
                        os.makedirs(www2sf_output_file[:www2sf_output_file.rindex('/')], exist_ok=True)
                        with open(www2sf_output_file, "wb") as xml_file:
                            xml_file.write(process.stdout)
                        logger.info("Output file {}: OK".format(www2sf_output_file))

                        # It's unlikely to happen but consider that 2 converter processes could start at the exact same time and conflict with each other.
                        # I should test if the file exists and change the name a bit when it happens.
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
                    else:
                        # If the script is stopped manually, the file is considered as not processed.
                        if not stopped:
                            unconvertable_filename = "{0}/unconvertable_files.txt".format(self.new_xml_files_dir)
                            unconvertable_file_lock = "{0}.lock".format(unconvertable_filename)
                            with FileLock(unconvertable_file_lock):
                                with open(unconvertable_filename, 'a') as f:
                                    f.write("{0}\n".format(www2sf_input_file))
                else:
                    # Special case for files that had an old timestamps format or have been lost
                    # probably because the converter has been killed abruptly.
                    # If the script is stopped manually, the file is considered as not processed.
                    if not stopped:
                        lost_filename = "{0}/already_converted_but_unreferred_files.txt".format(self.new_xml_files_dir)
                        lost_file_lock = "{0}.lock".format(lost_filename)
                        with FileLock(lost_file_lock):
                            with open(lost_filename, 'a') as f:
                                f.write("{0}\n".format(www2sf_output_file))

            except:
                e = sys.exc_info()[0]
                logger.info("An error has occurred: %s" % e)
                # logger.info("An error has occurred: %s" % traceback.format_exc())


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Launch the converter.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--config", help="Location of config file.", type=str, default="config.json")
    parser.add_argument("--log_config", help="Log configuration file.", type=str, default="converter_logging.conf")
    parser.add_argument("region", nargs='?', default=None)
    args = parser.parse_args(args=None)

    config_filename = args.config
    logging.config.fileConfig(args.log_config)
    logger = logging.getLogger('default')

    regions = None if args.region is None else args.region.split(',')

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

        queue_html_files = queue.Queue()

        unconvertable_files = get_unconvertable_files(new_xml_files_dir)
        unreferred_files = get_unreferred_files(new_xml_files_dir)
        prev_processed_files = get_processed_files(new_xml_files_dir)
        processed_files = []

        mutex = threading.Lock()

        producers = []
        converters = []

        producer = Producer()
        producers.append(producer)
        producer.start()

        for producer in producers:
            producer.join()

        # i = 0
        # while not queue_html_files.empty():
        #     (www2sf_input_file, www2sf_output_file) = queue_html_files.get()
        #     print("i={0} www2sf_input_file={1}".format(i, www2sf_input_file))
        #     i += 1
        #     queue_html_files.task_done()

        converter_count = 40 if args.region is None else min(40, 10 * len(regions))
        for c in range(0, converter_count):
            converter = Converter(c, new_xml_files_dir)
            converters.append(converter)
            converter.start()

        for converter in converters:
            converter.join()

        logger.info("Number of new xml files: {0}".format(len(processed_files)))

        # if len(processed_files) > 0:
        #     new_xml_filename = os.path.join(run_dir, 'new-xml-files', 'new-xml-files-{0}.txt'.format(now.strftime('%Y-%m-%d-%H-%M')))
        #     logger.info("Writing report file: {0} new_xml_file_count: {1}".format(new_xml_filename, len(processed_files)))
        #     with open(new_xml_filename, 'a') as new_xml_file:
        #         for file in processed_files:
        #             new_xml_file.write(file)
        #             new_xml_file.write("\n")
        #     logger.info("Report written.")

        logger.info("Iteration over.")

        # stopped = True

    logger.info("Stop running.")
