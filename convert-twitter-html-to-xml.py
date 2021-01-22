import datetime
from filelock import FileLock
import glob
import json
import logging
import logging.config
import os
import queue
import signal
import subprocess
import sys
import threading
import time
import traceback


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
    unconvertable_filename = f"{new_xml_files_dir}/twitter_unconvertable_files.txt"
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
    unreferred_filename = f"{new_xml_files_dir}/twitter_already_converted_but_unreferred_files.txt"
    if os.path.exists(unreferred_filename):
        with open(unreferred_filename, 'r') as f:
            entries = f.read().splitlines()
            for entry in entries:
                files.add(entry)
    return files


def get_processed_files(new_xml_files_dir):
    files = set()

    for new_xml_file in glob.glob(f"{new_xml_files_dir}/new-twitter-xml-files*.txt"):
        with open(new_xml_file, 'r') as f:
            xml_entries = f.read().splitlines()
        for entry in xml_entries:
            files.add(entry)

    for entry in unreferred_files:
        files.add(entry)

    return files


class Producer(threading.Thread):

    def __init__(self, country):
        threading.Thread.__init__(self)
        self.name = f"Producer for country {country}"
        self.country = country
        self.stopped = False
        self.files_to_process = {}

    def run(self):
        global queue_html_files
        logger.info(f"Processing files from country: {self.country}...")
        root_input_dir = f"{self.country}/ja_translated"
        root_output_dir = f"{self.country}/ja_translated"

        root_abs_input_dir = os.path.join(html_dir, root_input_dir)
        root_abs_output_dir = os.path.join(xml_dir, root_output_dir)
        if os.path.exists(root_abs_input_dir):
            self.files_to_process = []
            for top, dirs, files in os.walk(root_abs_input_dir):
                # logger.debug(f"top={top} dirs={dirs} files={files}")
                for file in files:

                    if self.stopped:
                        logger.info(f"Producer for country {country} has been stopped.")
                        return

                    if file.endswith('.html'):
                        www2sf_input_file = os.path.join(top, file)
                        www2sf_output_file = os.path.join(root_abs_output_dir, top[top.index("ja_translated") + len("ja_translated") + 1:], file[:file.index('.html')] + '.xml')
                        logger.debug(f"Checking file: {www2sf_input_file}")
                        if www2sf_input_file in unconvertable_files:
                            logger.debug(f"Skip {www2sf_input_file} because it's flagged as unconvertable.")
                            continue

                        if www2sf_output_file in prev_processed_files:
                            logger.debug(f"Skip {www2sf_output_file} because already processed.")
                            continue

                        timestamp = datetime.datetime.fromtimestamp(os.stat(www2sf_input_file).st_mtime).strftime('%Y-%m-%d-%H-%M')
                        logger.debug(f"Adding {www2sf_input_file} to files to process.")
                        self.files_to_process.append((www2sf_input_file, www2sf_output_file, timestamp))

            # Process the 200 most recent files first for this country.
            logger.debug(f"len(files_to_process) for country {self.country}: {len(self.files_to_process)}")
            self.most_recent_files_first = sorted(self.files_to_process, reverse=True, key=lambda x: x[-1])[:200]
            for file in self.most_recent_files_first:
                logger.info(f"Adding {www2sf_input_file} to queue.")
                queue_html_files.put((file[0], file[1]))

        logger.info(f"Finished processing files from country: {self.country}...")


class Converter(threading.Thread):

    def __init__(self, identifier, new_xml_files_dir):
        threading.Thread.__init__(self)
        self.name = f"Converter: {identifier}"
        self.identifier = identifier
        self.stopped = False
        self.new_xml_files_dir = new_xml_files_dir

    def run(self):
        global queue_html_files
        while True:
            try:
                if self.stopped:
                    logger.info(f"Converter {self.identifier} has been stopped.")
                    break

                if queue_html_files.empty():
                    break

                (www2sf_input_file, www2sf_output_file) = queue_html_files.get()
                logger.info(f"Process file: {www2sf_input_file}")
                if not os.path.exists(www2sf_output_file):
                    logger.info(f"Convert input={www2sf_input_file} output={www2sf_output_file}")
                    logger.info(f"cd {www2sf_dir} && tool/html2sf.sh -T -D {detectblocks_dir} -J {www2sf_input_file}")
                    process = subprocess.run(["tool/html2sf.sh", "-T", f"-D {detectblocks_dir}", "-J", www2sf_input_file], cwd=www2sf_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    logger.info(f"return_code={process.returncode}")
                    if process.returncode == 0:
                        os.makedirs(www2sf_output_file[:www2sf_output_file.rindex('/')], exist_ok=True)
                        with open(www2sf_output_file, "wb") as xml_file:
                            xml_file.write(process.stdout)
                        logger.info(f"Output file {www2sf_output_file}: OK")

                        new_xml_filename = os.path.join(run_dir, 'new-xml-files', f"new-twitter-xml-files-{now.strftime('%Y-%m-%d-%H-%M')}.txt")
                        new_xml_file_lock = f"{new_xml_filename}.lock"
                        with FileLock(new_xml_file_lock):
                            with open(new_xml_filename, 'a') as f:
                                f.write(f"{www2sf_output_file}\n")
                        mutex.acquire()
                        try:
                            processed_files.append(www2sf_output_file)
                        finally:
                            mutex.release()
                        queue_html_files.task_done()
                    else:
                        # If the script is stopped manually, the file is considered as not processed.
                        if not stopped:
                            unconvertable_filename = f"{self.new_xml_files_dir}/twitter_unconvertable_files.txt"
                            unconvertable_file_lock = f"{unconvertable_filename}.lock"
                            with FileLock(unconvertable_file_lock):
                                with open(unconvertable_filename, 'a') as f:
                                    f.write(f"{www2sf_input_file}\n")
                else:
                    # Special case for files that had an old timestamps format or have been lost
                    # probably because the converter has been killed abruptly.
                    # If the script is stopped manually, the file is considered as not processed.
                    if not stopped:
                        lost_filename = f"{self.new_xml_files_dir}/twitter_already_converted_but_unreferred_files.txt"
                        lost_file_lock = f"{lost_filename}.lock"
                        with FileLock(lost_file_lock):
                            with open(lost_filename, 'a') as f:
                                f.write(f"{www2sf_output_file}\n")

            except:
                e = sys.exc_info()[0]
                logger.info("An error has occurred: %s" % e)
                # logger.info("An error has occurred: %s" % traceback.format_exc())


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Launch the converter.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--config", help="Location of config file.", type=str, default="config.json")
    parser.add_argument("--log_config", help="Log configuration file.", type=str, default="twitter_converter_logging.conf")
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

        html_dir = config['twitter']['html_dir']
        xml_dir = config['twitter']['xml_dir']
        run_dir = config['run_dir']
        new_xml_files_dir = f"{run_dir}/new-xml-files"
        www2sf_dir = config['WWW2sf_dir']
        detectblocks_dir = config['detectblocks_dir']

        now = datetime.datetime.now()

        queue_html_files = queue.Queue()

        unconvertable_files = get_unconvertable_files(new_xml_files_dir)
        unreferred_files = get_unreferred_files(new_xml_files_dir)
        prev_processed_files = get_processed_files(new_xml_files_dir)
        processed_files = []

        print(f"unconvertable_files={unconvertable_files}")
        print(f"unreferred_files={unreferred_files}")
        print(f"prev_processed_files={prev_processed_files}")
        print(f"countries={os.listdir(html_dir)}")

        mutex = threading.Lock()

        producers = []
        converters = []

        for country in os.listdir(html_dir):
            producer = Producer(country)
            producers.append(producer)
            producer.start()

        for producer in producers:
            producer.join()

        # i = 0
        # while not queue_html_files.empty():
        #     (www2sf_input_file, www2sf_output_file) = queue_html_files.get()
        #     print(f"i={i} www2sf_input_file={www2sf_input_file}")
        #     i += 1
        #     queue_html_files.task_done()

        converter_count = 40
        for c in range(0, converter_count):
            converter = Converter(c, new_xml_files_dir)
            converters.append(converter)
            converter.start()

        for converter in converters:
            converter.join()

        logger.info(f"Number of new xml files: {len(processed_files)}")

        # if len(processed_files) > 0:
        #     new_xml_filename = os.path.join(run_dir, 'new-xml-files', f'new-xml-files-{now.strftime('%Y-%m-%d-%H-%M')}.txt')
        #     logger.info(f"Writing report file: {new_xml_filename} new_xml_file_count: {len(processed_files)}")
        #     with open(new_xml_filename, 'a') as new_xml_file:
        #         for file in processed_files:
        #             new_xml_file.write(file)
        #             new_xml_file.write("\n")
        #     logger.info("Report written.")

        logger.info("Iteration over.")

        stopped = True

    logger.info("Stop running.")

