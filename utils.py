from apiclient import errors
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import base64
from email.mime.text import MIMEText
import re


SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def create_message(sender, to, cc, bcc, subject, message_text):
    message = MIMEText(message_text)
    message['to'] = to
    message['cc'] = cc
    message['bcc'] = bcc
    message['from'] = sender
    message['subject'] = subject
    encode_message = base64.urlsafe_b64encode(message.as_bytes())
    return {'raw': encode_message.decode()}


def send_message(service, user_id, message):
    try:
        message = (service.users().messages().send(userId=user_id, body=message).execute())
        # print('Message Id: %s' % message['id'])
        return message
    except errors.HttpError as error:
        print('An error occurred: %s' % error)


def send_mail(fromm, to, cc, bcc, subject, text):
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server()
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    message = create_message(fromm, to, cc, bcc, subject, text)
    send_message(service, 'me', message)


def convert_country_to_iso_3166_alpha_2(country):
    if "-" == country:
        return None
    if hasattr(convert_country_to_iso_3166_alpha_2, "country_codes") and country in convert_country_to_iso_3166_alpha_2.country_codes:
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
