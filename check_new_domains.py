import argparse
import email
import json
import re
import requests
import utils


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--config", default="config.json", help="Path to configuration file.")
    args = argparser.parse_args()

    with open(args.config, 'r') as config_file:
        config = json.load(config_file)

    domain_prefixes = [config['domains'][domain]['prefix'] for domain in config['domains'] if 'prefix' in config['domains'][domain]]
    domain_prefixes += [config['domains_ignored'][domain]['prefix'] for domain in config['domains_ignored'] if 'prefix' in config['domains_ignored'][domain]]
    domain_prefixes += [config['domains_disabled'][domain]['prefix'] for domain in config['domains_disabled'] if 'prefix' in config['domains_disabled'][domain]]

    index_url = config['crawled_data_repository']
    req = requests.get(index_url)
    if req.status_code == 200:
        new_domains = set()
        for line in req.text.splitlines():
            match = re.search('a href="(.+)">.+</a>', line)
            if match:
                domain = match.group(1)
                domain = domain.replace("_", ".")
                if domain in config['domains']:
                    continue
                if 'domains_ignored' in config and domain in config['domains_ignored']:
                    continue
                if 'domains_disabled' in config and domain in config['domains_disabled']:
                    continue
                if domain in domain_prefixes:
                    continue
                new_domains.add(domain)

        if len(new_domains) > 0:
            utils.send_mail(config['mail']['from'],
                None if 'to' not in config['mail'] else config['mail']['to'],
                None if 'cc' not in config['mail'] else config['mail']['cc'],
                None if 'bcc' not in config['mail'] else config['mail']['bcc'],
                "New domains discovered for COVID-19", str(new_domains))
