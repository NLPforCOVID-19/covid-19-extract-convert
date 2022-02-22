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

max_file_count = 8000
max_file_count_per_country = 1000

# Number of days to look back when searching for files to convert.
last_days = 3


def get_timestamp_from_filename(new_translated_file_fn):
    base_fn = os.path.basename(new_translated_file_fn)
    timestamp_str = base_fn[29:45]
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

    def __init__(self):
        threading.Thread.__init__(self)
        self.name = f"Producer"
        self.stopped = False
        self.files_to_process = {}
        self.file_count = 0


    def process_new_translated_files_file(self, new_translated_files_file):
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
                    country, _, *url_parts = pathlib.Path(translated_file[len(html_dir) + 1:]).parts

                    print(f"country={country} url_parts={url_parts}")
                    # Skip old files.
                    if url_parts[0] == "2020":
                        continue

                    if self.file_count < max_file_count and (country not in self.files_to_process or len(self.files_to_process[country]) < max_file_count_per_country):
                        url_filename = pathlib.Path(*url_parts)

                        www2sf_input_file = pathlib.Path(html_dir) / country / "ja_translated" / url_filename
                        www2sf_output_file = pathlib.Path(xml_dir) / country / "ja_translated" / url_filename.with_suffix('.xml')
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
                        if country in self.files_to_process and item in self.files_to_process[country]:
                            logger.debug(f"Skip {www2sf_input_file} because {www2sf_output_file} already registered.")
                            continue

                        logger.debug("Adding {} to files to process.".format(www2sf_input_file))
                        if country not in self.files_to_process:
                            self.files_to_process[country] = []
                        if item not in self.files_to_process[country]:
                            self.files_to_process[country].append(item)
                            self.file_count += 1

                        if self.file_count >= max_file_count or len(self.files_to_process[country]) >= max_file_count_per_country:
                            return


    def run(self):
        global queue_html_files
        logger.info(f"Processing new-translated-files.txt files...")

        new_translated_files_files = glob.glob(os.path.join(run_dir, 'new-translated-files') + '/**/new-twitter-translated-files-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[0-9][0-9].txt', recursive=True)
        recent_new_translated_files_files = [new_translated_file for new_translated_file in new_translated_files_files if (now - get_timestamp_from_filename(new_translated_file)).days < last_days]
        sorted_new_translated_files_files = sorted(recent_new_translated_files_files, key=get_timestamp_from_filename, reverse=True)

        for new_translated_files_file in sorted_new_translated_files_files:

            self.process_new_translated_files_file(new_translated_files_file)
            if self.file_count >= max_file_count:
                break

        logger.info("Finished processing new-translated-files.txt files.")

        for country in self.files_to_process.keys():
            logger.info(f"country={country} len={len(self.files_to_process[country])}")

        for country in self.files_to_process.keys():
            for file in self.files_to_process[country]:
                logger.info(f"Adding {file[0]} to queue.")
                queue_html_files.put((str(file[0]), str(file[1])))


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
                # logger.info("An error has occurred: %s" % e)
                logger.info("An error has occurred: %s" % traceback.format_exc())


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

        producer = Producer()
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

        # stopped = True

        # Wait 1 hour before next iteration.
        # time.sleep(60 * 60)

    logger.info("Stop running.")

