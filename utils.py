from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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

