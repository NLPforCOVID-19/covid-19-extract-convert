# Some extraction and conversion scripts for the NLPforCOVID-19 project

## Requirements

* Python 3.6.5
* WWW2sf
* detectblocks

## Configuration

To prepare the environment:

    pipenv sync

Copy the ```config.json.sample``` file to ```config.json``` and edit it according to your settings.

| Parameter | Description |
| --- | --- |
| crawled_data_repository |  Url of the harvested page databases. |
| twitter |  Settings for Twitter data extraction.  See below for more information. |
| default_similarity_threshold | Articles that are too similar will be ignored. |
| domains | Domains to consider.  Each domain contains several parameters.  See below for more information. |
| domains_ignored | Domains to ignore.  For some reasons, a domain might be irrelevant.  It can be put into this section so that it is ignored. |
| domains_disabled | Disabled domains.  For some reasons, a domain might become irrelevant after a while.  For instance, a domain might suddenly blocks our crawler.  In such a case, it's no longer useful to process it so it can be moved from domains to domains_disabled.  Previous data will be kept and shown in the stats page but no new data will be extracted and processed. |
| url_black_list | Text file containing URLs that must be ignored. |
| db_dir | Directory where the databases are stored during processing. |
| html_dir | Directory where the extracted html files are stored. |
| xml_dir | Directory where the converted xml files are stored. |
| run_dir | Directory containing running time info. |
| WWW2sf_dir | Installation directory of the WWW2sf tool. |
| detectblocks_dir | Installation directory of the detectblocks tool. |
| mail | Parameters needed for email notifications.  See below for more information. |


The domains sections can contain several parameters:

| Parameter | Description |
| --- | --- |
| region | 2 or 3 letters code corresponding to the geographical area of the domain. It's usually an ISO-3166 Alpha-2 code.  But "int" means international. |
| language | 2 letters code corresponding to the language of the resource. It's usually an ISO-639-2 code. |
| subdomains | An array of regular expressions that the URL must comply to be considered. |
| sources | The official sources associated to the domain.  Most of the time, it's equal to the domain name however for some cases where domains are grouped into a bundle, it will list the sources contained in the bundle. |


The mail section might contain several parameters:

| Parameter | Description |
| --- | --- |
| from | The From: field value of the notification email. |
| to | The To: field value where the notification mail will be sent. |
| cc |The Cc: field value where the notification mail will be also sent. |
| bcc |The Bcc: field value where the notification mail will be also sent. |

In addition to the mail parameters, it's also important to configure the OAuth settings.  The mail notification uses Googlle account using OAuth.

From the https://console.developers.google.com page, it's required to create an OAuth 2.0 Client IDs from the Credentials page.  Then the credential data must downloaded and copied into the ```credentials.json``` file.  

The ```send_mail()``` function in ```utils.py``` must be called from a desktop computer having access to Internet.  Doing so will lead the user to authenticate himself to Google and authorize mail notifications.  A resulting ```token.pickle``` will be generated.  This file must be copied in the same directory that contains the ```config.json``` file.  It will enable mail notifications without user interaction.

This procedure is not very convenient but I know no alternative to it at the moment.

The twitter section contains settings related to data extraction from Twitter: 

| Parameter | Description |
| --- | --- |
| crawled_data_repository |  Url of the harvested page databases. |
| user | Login of the user authorized to access the data. |
| password | Password of the user authorized to access the data. |
| html_dir | Directory where the extracted Twitter html files are stored. |
| xml_dir | Directory where the converted Twitter xml files are stored. |
