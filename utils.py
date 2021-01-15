from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
import smtplib

def send_mail(smtp_host, smtp_port, smtp_user, smtp_password, fromm, to, cc, bcc, subject, text):
    resp_msg = MIMEMultipart()
    resp_msg['From'] = fromm

    # Never send a message to a daemon user.
    if to is not None and "daemon" in to.lower():
        return

    resp_msg['To'] = to
    cc_list = None
    bcc_list = None
    if cc is not None:
        resp_msg['Cc'] = cc
        cc_list = cc.split(",")
    if bcc is not None:
        resp_msg['Bcc'] = bcc
        bcc_list = bcc.split(",")

    dests = []
    if to:
        dests.append(to)
    if cc:
        dests += cc_list
    if bcc:
        dests += bcc_list

    if len(dests) == 0:
        return

    resp_msg['Subject'] = subject
    resp_msg.attach(MIMEText(text, 'plain', 'utf-8'))

    smtp_server = smtplib.SMTP(smtp_host, smtp_port)
    smtp_server.starttls()
    smtp_server.login(smtp_user, smtp_password)
    text = resp_msg.as_string().encode('ascii')
    smtp_server.sendmail(fromm, dests, text)
    smtp_server.quit()


def convert_country_to_iso_3166_alpha_2(country):
    if "-" == country:
        return None
    if hasattr(convert_country_to_iso_3166_alpha_2, "country_codes") and country not in convert_country_to_iso_3166_alpha_2.country_codes:
        return convert_country_to_iso_3166_alpha_2.country_codes[country]
    convert_country_to_iso_3166_alpha_2.country_codes = {}
    country_codes_filename = "country_codes.txt" # Should be defined in the config.
    with open(country_codes_filename, 'r') as country_codes_file:
        for line in country_codes_file:
            line = line.strip()
            if line == '' or line.startswith('#'):
                continue
            match = re.search("(.*) (\w\w)", line)
            if match:
                convert_country_to_iso_3166_alpha_2.country_codes[match.group(1)] = match.group(2)
    if country in convert_country_to_iso_3166_alpha_2.country_codes:
        return convert_country_to_iso_3166_alpha_2.country_codes[country]

    raise LookupError(f"Country {country} undefined. Cannot find corresponding ISO-3166 Alpha-2 code.")

