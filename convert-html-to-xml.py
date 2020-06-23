import datetime
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


def get_processed_files(new_xml_files_dir):
    processed_files = set()

    # Consider unconvertable files as already processed. 
    unconvertable_filename = "{0}/unconvertable_files.txt".format(new_xml_files_dir)
    if os.path.exists(unconvertable_filename): 
        with open(unconvertable_filename, 'r') as f:
            xml_entries = f.read().splitlines()
            for entry in xml_entries:
                if entry.endswith('.html'):
                    modified_entry = entry[:-5] + ".xml"
                    processed_files.add(modified_entry)

    for new_xml_file in glob.glob("{0}/new-xml-files*.txt".format(new_xml_files_dir)):
        with open(new_xml_file, 'r') as f:
            xml_entries = f.read().splitlines()
        for entry in xml_entries:
            print("entry={0}".format(entry))
            processed_files.add(entry)

    return processed_files


class Producer(threading.Thread):

    def __init__(self, region):
        threading.Thread.__init__(self)
        self.name = "Producer for region {}".format(region)
        self.region = region
        self.stopped = False

    def run(self):
        logger.info("Processing files from region: {}...".format(self.region))
        root_input_dir = "{0}/ja_translated".format(self.region)
        root_output_dir = "{0}/ja_translated".format(self.region)

        root_abs_input_dir = os.path.join(html_dir, root_input_dir)
        root_abs_output_dir = os.path.join(xml_dir, root_output_dir)
        if os.path.exists(root_abs_input_dir):
            for domain in os.listdir(root_abs_input_dir):
                logger.info("Processing domain: {}...".format(domain))
                for top, dirs, files in os.walk(os.path.join(root_abs_input_dir, domain)):
                    # logger.debug("top={0} dirs={1} files={2}".format(top, dirs, files))
                    for file in files:

                        if self.stopped:
                            logger.info("Producer for region {0} has been stopped.".format(self.region))
                            return

                        if file.endswith('.html'):
                            www2sf_input_file = os.path.join(top, file)
                            www2sf_output_file = os.path.join(root_abs_output_dir, domain, top[top.index(domain) + len(domain) + 1:], file[:file.index('.html')] + '.xml')
                            if www2sf_output_file in prev_processed_files:
                                # logger.debug("Skip {} because already processed.".format(www2sf_output_file))
                                continue
                            
                            if not queue_html_files.full():
                                # logger.info("Adding {} to queue.".format(www2sf_input_file))
                                queue_html_files.put((www2sf_input_file, www2sf_output_file))


class Converter(threading.Thread):

    def __init__(self, identifier, new_xml_files_dir):
        threading.Thread.__init__(self)
        self.name = "Converter: {}".format(identifier)
        self.identifier = identifier
        self.stopped = False
        self.new_xml_files_dir = new_xml_files_dir

    def run(self):
        while True:
            try:
                if self.stopped:
                    logger.info("Converter {0} has been stopped.".format(self.identifier))
                    break

                if not queue_html_files.empty():
                    (www2sf_input_file, www2sf_output_file) = queue_html_files.get()
                    # logger.info("Process file: {}".format(www2sf_input_file))
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
                            mutex.acquire()
                            try:
                                processed_files.append(www2sf_output_file)
                            finally:
                                mutex.release()
                        else:
                            unconvertable_filename = "{0}/unconvertable_files.txt".format(self.new_xml_files_dir)
                            with open(unconvertable_filename, 'a') as f:
                                f.write("{0}\n".format(www2sf_input_file))

                else:
                    # Wait a while.  If the queue is still empty after that, stop working.
                    time.sleep(60)
                    if queue_html_files.empty():
                        break
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
        converter_count = 20

        now = datetime.datetime.now()

        queue_html_files = queue.Queue()

        prev_processed_files = get_processed_files(new_xml_files_dir)
        processed_files = []

        mutex = threading.Lock()

        converters = []
        for c in range(0, converter_count):
            converter = Converter(c, new_xml_files_dir)
            converters.append(converter)
            converter.start()

        producers = []
        for region in os.listdir(html_dir):
            producer = Producer(region)
            producers.append(producer)
            producer.start()

        for producer in producers:
            producer.join()

        for convert in converters:
            converter.join()

        if len(processed_files) > 0:
            new_xml_filename = os.path.join(run_dir, 'new-xml-files', 'new-xml-files-{0}.txt'.format(now.strftime('%Y-%m-%d-%H-%M')))
            logger.info("Writing report file: {0} new_xml_file_count: {1}".format(new_xml_filename, len(processed_files)))
            with open(new_xml_filename, 'a') as new_xml_file:
                for file in processed_files:
                    new_xml_file.write(file)
                    new_xml_file.write("\n")
            logger.info("Report written.")
