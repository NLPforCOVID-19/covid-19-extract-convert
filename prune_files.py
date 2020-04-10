"""Prune no longer needed HTML and associate files (.html, .xml, .txt, .url)."""

import argparse
import datetime
import glob
import json
import os


# Delete the file, all its brother files and remove the parent directory if it's empty (i.e. no brother directories).
# Delete also other parent directories if they are empty but stops
def delete_file(prefix, fn):
    abs_path = os.path.join(prefix, fn)
    if os.path.isfile(abs_path):
        parent_dir = os.path.dirname(abs_path)
        for f in os.listdir(parent_dir):
            f_abs_path = os.path.join(parent_dir, f) 
            if os.path.isfile(f_abs_path):
                print("remove f={}".format(f_abs_path))
                # os.remove(f)
        while parent_dir != prefix:
            if len(os.listdir(parent_dir)) == 0:
                print("remove parent_dir={}".format(parent_dir))
                # os.rmdir(parent_dir)
                parent_dir = os.dirname(parent_dir)
            else:
                break


def extract_date(fn):
    bn = os.path.basename(fn) 
    if bn[0].isdigit():
        return bn[:16]
    else:
        first_dash = bn.index('-')
        return bn[first_dash + 1:first_dash + 17]


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--config", default="config.json", help="Path to configuration file.")
    args = argparser.parse_args()

    with open(args.config, 'r') as config_file:
        config = json.load(config_file)

    files_to_keep = set()
    files_to_delete = set()

    now = datetime.datetime.now()
    for metadata_filename in sorted(glob.glob('{}/*.metadata.jsonl'.format(config['metadata_dir'])), key=extract_date):
        str_date = extract_date(metadata_filename)
        date = datetime.datetime.strptime(str_date, '%Y-%m-%d-%H-%M')
        delta = now - date

        with open(metadata_filename, 'r') as metadata_file:
            while True:
                line = metadata_file.readline()
                if not line:
                    break

                line_data = json.loads(line)
                orig_filename = line_data['orig']['file']
                ja_trans_filename = line_data['ja_translated']['file']
                xml_filename = line_data['ja_translated']['xml_file']

                for fn in [orig_filename, ja_trans_filename, xml_filename]:
                    if delta.days <= config['grace_period_before_pruning']:
                        files_to_keep.add(fn)
                    else:
                        if fn not in files_to_keep:
                            files_to_delete.add(fn)

    # print(len(files_to_delete))
    for fn in files_to_delete:
        prefix = os.path.dirname(config['html_dir'])
        # delete_file(prefix, fn)
        delete_file("/mnt/hinoki/share/covid19/html_04_09", fn[fn.index("/")+1:])
        # break
