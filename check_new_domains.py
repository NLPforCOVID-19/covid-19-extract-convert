import argparse
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import re
import requests
import smtplib

def send_mail(to, subject, text):
    resp_msg = MIMEMultipart()
    resp_msg['From'] = config['smtp']['from']

    # Never send a message to a daemon user.
    if to is not None and "daemon" in to.lower():
        return

    resp_msg['To'] = to
    cc = None
    bcc = None
    if 'cc' in config['smtp']:
        resp_msg['Cc'] = config['smtp']['cc']
        cc = config['smtp']['cc'].split(",")
    if 'bcc' in config['smtp']:
        resp_msg['Bcc'] = config['smtp']['bcc']
        bcc = config['smtp']['bcc'].split(",")

    dests = []
    if to:
        dests.append(to)
    if cc:
        dests += cc
    if bcc:
        dests += bcc

    if len(dests) == 0:
        return

    resp_msg['Subject'] = subject
    resp_msg.attach(MIMEText(text, 'plain', 'utf-8'))

    smtp_server = smtplib.SMTP(config['smtp']['host'], config['smtp']['port'])
    smtp_server.starttls()
    smtp_server.login(config['smtp']['user'], config['smtp']['password'])
    text = resp_msg.as_string().encode('ascii')
    smtp_server.sendmail(config['smtp']['from'], dests, text)
    smtp_server.quit()


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--config", default="config.json", help="Path to configuration file.")
    argparser.add_argument("--to", help="Email address of the listener.")
    args = argparser.parse_args()

    with open(args.config, 'r') as config_file:
        config = json.load(config_file)

    domain_prefixes = [config['domains'][domain]['prefix'] for domain in config['domains'] if 'prefix' in config['domains'][domain]]

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
                if domain in domain_prefixes:
                    continue
                if 'domains_ignored' in config and domain in config['domains_ignored']:
                    continue
                if 'domains_disabled' in config and domain in config['domains_disabled']:
                    continue
                new_domains.add(domain)

        if len(new_domains) > 0:
            send_mail(args.to, "New domains discovered for COVID-19", str(new_domains))
