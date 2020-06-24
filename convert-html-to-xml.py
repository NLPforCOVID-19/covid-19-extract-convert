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

    def __init__(self, region):
        threading.Thread.__init__(self)
        self.name = "Producer for region {}".format(region)
        self.region = region
        self.stopped = False
        self.files_to_process = {}

    def run(self):
        global queue_html_files
        logger.info("Processing files from region: {}...".format(self.region))
        root_input_dir = "{0}/ja_translated".format(self.region)
        root_output_dir = "{0}/ja_translated".format(self.region)

        root_abs_input_dir = os.path.join(html_dir, root_input_dir)
        root_abs_output_dir = os.path.join(xml_dir, root_output_dir)
        if os.path.exists(root_abs_input_dir):
            for domain in os.listdir(root_abs_input_dir):
                logger.info("Processing domain: {}...".format(domain))
                self.files_to_process[domain] = []
                for top, dirs, files in os.walk(os.path.join(root_abs_input_dir, domain)):
                    # logger.debug("top={0} dirs={1} files={2}".format(top, dirs, files))
                    for file in files:

                        if self.stopped:
                            logger.info("Producer for region {0} has been stopped.".format(self.region))
                            return

                        if file.endswith('.html'):
                            www2sf_input_file = os.path.join(top, file)
                            www2sf_output_file = os.path.join(root_abs_output_dir, domain, top[top.index(domain) + len(domain) + 1:], file[:file.index('.html')] + '.xml')
                            logger.debug("Checking file: {}".format(www2sf_input_file))
                            if www2sf_input_file in unconvertable_files:
                                logger.debug("Skip {} because it's flagged as unconvertable.".format(www2sf_input_file))
                                continue

                            if www2sf_output_file in prev_processed_files:
                                logger.debug("Skip {} because already processed.".format(www2sf_output_file))
                                continue

                            timestamp = datetime.datetime.fromtimestamp(os.stat(www2sf_input_file).st_mtime).strftime('%Y-%m-%d-%H-%M')
                            logger.debug("Adding {} to files to process.".format(www2sf_input_file))
                            self.files_to_process[domain].append((www2sf_input_file, www2sf_output_file, timestamp) )

                # Process the 200 most recent files first for this domain. 
                logger.debug("len(files_to_process[{0}]) for region {1}: {2}".format(domain, self.region, len(self.files_to_process[domain])))
                self.most_recent_files_first = sorted(self.files_to_process[domain], reverse=True, key=lambda x: x[-1])[:200]
                for file in self.most_recent_files_first:
                    logger.info("Adding {} to queue.".format(www2sf_input_file))
                    queue_html_files.put((file[0], file[1]))
                    
        logger.info("Finished processing files from region: {}...".format(self.region))


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


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Launch the converter.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--config", help="Location of config file.", type=str, default="config.json")
    parser.add_argument("--log_config", help="Log configuration file.", type=str, default="converter_logging.conf")
    args = parser.parse_args(args=None)

    config_filename = args.config

    logging.config.fileConfig(args.log_config)
    logger = logging.getLogger('default')

    signal.signal(signal.SIGINT, signal_handler)
    print("Hit CTRL+C and wait a little bit to stop the converter.")

    stopped = False
    while not stopped:
        with open(config_filename, 'r') as config_file:
            config = json.load(config_file)

        html_dir = config['html_dir']
        xml_dir = config['xml_dir']
        run_dir = config['run_dir']
        new_xml_files_dir = "{0}/new-xml-files".format(run_dir)
        www2sf_dir = config['WWW2sf_dir']
        detectblocks_dir = config['detectblocks_dir']

        now = datetime.datetime.now()

        queue_html_files = queue.Queue()

        unconvertable_files = get_unconvertable_files(new_xml_files_dir)
        unreferred_files = get_unreferred_files(new_xml_files_dir)
        prev_processed_files = get_processed_files(new_xml_files_dir)
        processed_files = []

        mutex = threading.Lock()

        producers = []
        for region in os.listdir(html_dir):
            # Skip French region temporarily.
            # if region == 'fr':
            #     continue
            producer = Producer(region)
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

        converter_count = 40
        converters = []
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
