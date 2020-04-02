import json
import os
import subprocess
import sys

config_filename = sys.argv[1] if len(sys.argv) == 2 else 'config.json'
with open(config_filename, 'r') as config_file:
    config = json.load(config_file)

db_dir = config['db_dir']
html_dir = config['html_dir']
xml_dir = config['xml_dir']
www2sf_dir = config['WWW2sf_dir']

for region in os.listdir(html_dir):
    print("Processing files from region: {}...".format(region))
    root_input_dir = "{0}/ja_translated".format(region)
    root_output_dir = "{0}/ja_translated".format(region)

    root_abs_input_dir = os.path.join(html_dir, root_input_dir)
    root_abs_output_dir = os.path.join(xml_dir, root_output_dir)
    if os.path.exists(root_abs_input_dir):
        for domain in os.listdir(root_abs_input_dir):
            print("Processing domain: {}...".format(domain))
            for top, dirs, files in os.walk(os.path.join(root_abs_input_dir, domain)):
                print("top={0} dirs={1} files={2}".format(top, dirs, files))
                for file in files:
                    if file.endswith('.html'):
                        www2sf_input_file = os.path.join(top, file)
                        www2sf_output_file = os.path.join(root_abs_output_dir, domain, top[top.index(domain) + len(domain) + 1:], file[:file.index('.html')] + '.xml')
                        print("www2sf_output_file={0} exist={1}".format(www2sf_output_file, os.path.exists(www2sf_output_file)))
                        if not os.path.exists(www2sf_output_file):
                            # print("file={} input={} output={}".format(file, www2sf_input_file, www2sf_output_file))
                            process = subprocess.run(["tool/html2sf.sh", "-J", www2sf_input_file], cwd=www2sf_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            print("return_code={0}".format(process.returncode))
                            os.makedirs(www2sf_output_file[:www2sf_output_file.rindex('/')], exist_ok=True)
                            with open(www2sf_output_file, "wb") as xml_file:
                                xml_file.write(process.stdout)

