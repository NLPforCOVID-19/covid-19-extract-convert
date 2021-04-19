import bs4
import datetime
import glob
import json
from json import JSONDecodeError
import os
import pathlib
import re
import requests
from requests.auth import HTTPBasicAuth
import twitter
import utils


def fix_txt_file(txt_file, links, hashtags):
    with open(txt_file, 'r') as f:
        content = f.read()
    
    # print("BEFORE")
    # print(content)

    # print("AFTER")
    if len(links) > 0:
        content += "\n\n"
        for link in links:
            content += f"{link}\n"

    if len(hashtags) > 0:
        content += "\n\n"
        content += " ".join(hashtags)
    # print(content)

    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(content)


def write_hashtags_and_links_file(tweet_id, dest_dir, links, hashtags):
    metadata_filename = os.path.join(dest_dir, f"{tweet_id}.metadata")
    with open(metadata_filename, 'r', encoding='utf-8') as metadata_file:
        metadata = json.load(metadata_file)

    metadata['links'] = links
    metadata['hashtags'] = hashtags

    with open(metadata_filename, 'w', encoding='utf-8') as data_file:
        json.dump(metadata, data_file, ensure_ascii=False)


def fix_html_file(html_file, links, hashtags):
    soup = bs4.BeautifulSoup(open(html_file), "html.parser")
    # print("HTML BEFORE")
    # print(str(soup))
    
    # print("HTML AFTER")
    if len(links) > 0:
        for link in links:
            link_p_tag = soup.new_tag('p')
            link_p_tag.string = link
            soup.body.append(link_p_tag)
            soup.body.append("\n")

    if len(hashtags) > 0:
        hashtags_p_tag = soup.new_tag('p')
        hashtags_p_tag.string = " ".join(hashtags)
        soup.body.append(hashtags_p_tag)
        soup.body.append("\n")

    # print(str(soup))
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(str(soup))


def overwrite_tweet_html(tweet_id):
    try:
        tweet = tweets[tweet_id]
        timestamp = now.strftime('%Y-%m-%d-%H-%M')
        tweet_timestamp = datetime.datetime.fromtimestamp(tweet['status'].created_at_in_seconds)
        country_code_dir = tweet['country_code']
        timestamp_path = tweet_timestamp.strftime('%Y/%m/%d/%H-%M')
        html_orig_tweet_dir = os.path.join(twitter_html_dir, country_code_dir, "orig", timestamp_path)
        html_ja_translated_tweet_dir = os.path.join(twitter_html_dir, country_code_dir, "ja_translated", timestamp_path)
        html_en_translated_tweet_dir = os.path.join(twitter_html_dir, country_code_dir, "en_translated", timestamp_path)

        # print(f"html_orig_tweet_dir={html_orig_tweet_dir}")
        # print(f"html_ja_translated_tweet_dir={html_ja_translated_tweet_dir}")
        # print(f"html_en_translated_tweet_dir={html_en_translated_tweet_dir}")

        # # EVen if the json file already exists, it's updated.
        # json_filename = os.path.join(html_orig_tweet_dir, f"{tweet_id}.json")
        # with open(json_filename, 'w') as json_file:
        #     json.dump(tweet['json'], json_file)

        # # EVen if the metadata file already exists, it's updated.
        # metadata_filename = os.path.join(html_orig_tweet_dir, f"{tweet_id}.metadata")
        # with open(metadata_filename, 'w') as metadata_file:
        #     metadata = {
        #         "id": tweet_id,
        #         "country": tweet["country"],
        #         "country_code": tweet["country_code"],
        #         "count": tweet["count"]
        #     }
        #     json.dump(metadata, metadata_file)

        # Write html file only if it already exists.
        tweet_text_for_html, hashtags, links = get_tweet_objects(tweet['status'])
        html_filename = os.path.join(html_orig_tweet_dir, f"{tweet_id}.html")
        if os.path.exists(html_filename):
            # print(f"overwrite_tweet_html tweet_id={tweet_id}")
            # with open(html_filename, 'w', encoding='utf-8') as html_file:
            #     html_str = (
            #         "<!DOCTYPE html>\n"
            #         f"<html lang=\"{tweet['status'].lang}\">\n"
            #         "<head><meta charset=\"utf-8\"/></head>\n"
            #         "<body>\n"
            #         f"<p>{tweet_text_for_html}</p>\n"
            #         "</body>\n"
            #         "</html>\n"
            #     )
            #     html_file.write(html_str)
            write_hashtags_and_links_file(tweet_id, html_orig_tweet_dir, links, hashtags)

            # ja_translated_html_filename = os.path.join(html_ja_translated_tweet_dir, f"{tweet_id}.html")
            # if os.path.exists(ja_translated_html_filename):
            #     fix_html_file(ja_translated_html_filename, links, hashtags)

            # ja_translated_txt_filename = os.path.join(html_ja_translated_tweet_dir, f"{tweet_id}.txt")
            # if os.path.exists(ja_translated_txt_filename):
            #     fix_txt_file(ja_translated_txt_filename, links, hashtags)

            # en_translated_html_filename = os.path.join(html_en_translated_tweet_dir, f"{tweet_id}.html")
            # if os.path.exists(en_translated_html_filename):
            #     fix_html_file(en_translated_html_filename, links, hashtags)

            # en_translated_txt_filename = os.path.join(html_en_translated_tweet_dir, f"{tweet_id}.txt")
            # if os.path.exists(en_translated_txt_filename):
            #     fix_txt_file(en_translated_txt_filename, links, hashtags)

            if country_code_dir in tweet_count_per_country:
                tweet_count_per_country[country_code_dir] += 1
            else:
                tweet_count_per_country[country_code_dir] = 1
    except OSError as os_err:
        print(f"An error has occurred in overwrite_tweet_html(tweet_id={tweet_id}) os_err={os_err}")


def get_tweet_objects(status):
    text = status.full_text if status.tweet_mode == 'extended' else status.text

    hashtags = re.findall(r"[#＃][a-z0-9_\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff\u0100-\u024f\u0253-\u0254\u0256-\u0257\u0300-\u036f\u1e00-\u1eff\u0400-\u04ff\u0500-\u0527\u2de0-\u2dff\ua640-\ua69f\u0591-\u05bf\u05c1-\u05c2\u05c4-\u05c5\u05d0-\u05ea\u05f0-\u05f4\ufb12-\ufb28\ufb2a-\ufb36\ufb38-\ufb3c\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufb4f\u0610-\u061a\u0620-\u065f\u066e-\u06d3\u06d5-\u06dc\u06de-\u06e8\u06ea-\u06ef\u06fa-\u06fc\u0750-\u077f\u08a2-\u08ac\u08e4-\u08fe\ufb50-\ufbb1\ufbd3-\ufd3d\ufd50-\ufd8f\ufd92-\ufdc7\ufdf0-\ufdfb\ufe70-\ufe74\ufe76-\ufefc\u200c-\u200c\u0e01-\u0e3a\u0e40-\u0e4e\u1100-\u11ff\u3130-\u3185\ua960-\ua97f\uac00-\ud7af\ud7b0-\ud7ff\uffa1-\uffdc\u30a1-\u30fa\u30fc-\u30fe\uff66-\uff9f\uff10-\uff19\uff21-\uff3a\uff41-\uff5a\u3005\u3041-\u3096\u3099-\u309e\u3400-\u4dbf\u4e00-\u9fff\u20000-\u2a6df\u2a700-\u2b73f\u2b740-\u2b81f\u2f800-\u2fa1f]*[a-z_\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff\u0100-\u024f\u0253-\u0254\u0256-\u0257\u0300-\u036f\u1e00-\u1eff\u0400-\u04ff\u0500-\u0527\u2de0-\u2dff\ua640-\ua69f\u0591-\u05bf\u05c1-\u05c2\u05c4-\u05c5\u05d0-\u05ea\u05f0-\u05f4\ufb12-\ufb28\ufb2a-\ufb36\ufb38-\ufb3c\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufb4f\u0610-\u061a\u0620-\u065f\u066e-\u06d3\u06d5-\u06dc\u06de-\u06e8\u06ea-\u06ef\u06fa-\u06fc\u0750-\u077f\u08a2-\u08ac\u08e4-\u08fe\ufb50-\ufbb1\ufbd3-\ufd3d\ufd50-\ufd8f\ufd92-\ufdc7\ufdf0-\ufdfb\ufe70-\ufe74\ufe76-\ufefc\u200c-\u200c\u0e01-\u0e3a\u0e40-\u0e4e\u1100-\u11ff\u3130-\u3185\ua960-\ua97f\uac00-\ud7af\ud7b0-\ud7ff\uffa1-\uffdc\u30a1-\u30fa\u30fc-\u30fe\uff66-\uff9f\uff10-\uff19\uff21-\uff3a\uff41-\uff5a\u3005\u3041-\u3096\u3099-\u309e\u3400-\u4dbf\u4e00-\u9fff\u20000-\u2a6df\u2a700-\u2b73f\u2b740-\u2b81f\u2f800-\u2fa1f][a-z0-9_\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff\u0100-\u024f\u0253-\u0254\u0256-\u0257\u0300-\u036f\u1e00-\u1eff\u0400-\u04ff\u0500-\u0527\u2de0-\u2dff\ua640-\ua69f\u0591-\u05bf\u05c1-\u05c2\u05c4-\u05c5\u05d0-\u05ea\u05f0-\u05f4\ufb12-\ufb28\ufb2a-\ufb36\ufb38-\ufb3c\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufb4f\u0610-\u061a\u0620-\u065f\u066e-\u06d3\u06d5-\u06dc\u06de-\u06e8\u06ea-\u06ef\u06fa-\u06fc\u0750-\u077f\u08a2-\u08ac\u08e4-\u08fe\ufb50-\ufbb1\ufbd3-\ufd3d\ufd50-\ufd8f\ufd92-\ufdc7\ufdf0-\ufdfb\ufe70-\ufe74\ufe76-\ufefc\u200c-\u200c\u0e01-\u0e3a\u0e40-\u0e4e\u1100-\u11ff\u3130-\u3185\ua960-\ua97f\uac00-\ud7af\ud7b0-\ud7ff\uffa1-\uffdc\u30a1-\u30fa\u30fc-\u30fe\uff66-\uff9f\uff10-\uff19\uff21-\uff3a\uff41-\uff5a\u3005\u3041-\u3096\u3099-\u309e\u3400-\u4dbf\u4e00-\u9fff\u20000-\u2a6df\u2a700-\u2b73f\u2b740-\u2b81f\u2f800-\u2fa1f]*", text)
    links = re.findall("https://t.co/\w+", text)

    return text, hashtags, links


def process_tweet_file(orig_json_tweet_file):
    print(f"processing tweet {orig_json_tweet_file}...")

    path_parts = pathlib.Path(orig_json_tweet_file).parts
    country_code = path_parts[-7]
    tweet_id = os.path.splitext(path_parts[-1])[0]
    with open(orig_json_tweet_file, 'r') as f:
        tweet_json = json.load(f)
    tweet_status = twitter.models.Status.NewFromJsonDict(tweet_json)
    tweet_text, hashtags, links = get_tweet_objects(tweet_status)
    
    tweets[tweet_id] = {
        'json': tweet_json,
        "status": tweet_status,
        "country_code": country_code
    }

    overwrite_tweet_html(tweet_id)


def process_tweet(tweet_id, tweet_count, tweet_lang, tweet_country, tweet_json_str):
    print(f"processing tweet {tweet_id}...")
    tweet_json = json.loads(tweet_json_str)
    tweet_status = twitter.models.Status.NewFromJsonDict(tweet_json)
    tweet_text, hashtags, links = get_tweet_objects(tweet_status)

    tweet_country_code = None
    try:
        tweet_country_code = utils.convert_country_to_iso_3166_alpha_2(tweet_country)
    except LookupError as ex:
        undefined_countries.add(tweet_country)
        print("Tweet {tweet_id} has been ignored because it refers to an undefined country: {tweet_country}.")
        return

    tweets[tweet_id] = {
        "count": tweet_count,
        "lang": tweet_lang,
        "country": tweet_country,
        "country_code": tweet_country_code,
        'json': tweet_json,
        "status": tweet_status
    }

    overwrite_tweet_html(tweet_id)


def retrieve_database(database):
    print(f"Retrieving db: {database}")
    database_url = os.path.join(config['twitter']['crawled_data_repository'], database, 'rtjobs')
    print(f"db url: {database_url}")
    os.makedirs(db_dir, exist_ok=True)
    database_filename = os.path.join(db_dir, f"tweets_{database}.txt")

    with requests.get(database_url, stream=True, auth=HTTPBasicAuth(config['twitter']['user'], config['twitter']['password'])) as req:
        req.raise_for_status()
        with open(database_filename, 'wb') as database_file:
            for chunk in req.iter_content(chunk_size=8192):
                database_file.write(chunk)
            print("File {} written.".format(database_filename))
            return database_filename


def get_available_databases():
    dbs = []
    index_url = config['twitter']['crawled_data_repository']
    req = requests.get(index_url, auth=HTTPBasicAuth(config['twitter']['user'], config['twitter']['password']))
    if req.status_code == 200:
        soup = bs4.BeautifulSoup(req.text, 'html.parser')
        all_rows = soup.find_all('li')
        for row in all_rows:
            link = row.find('a').get('href')
            match = re.search('(\d\d\d\d-\d\d-\d\d-\d\d-\d\d)/', link)
            if match:
                dbs.append(match.group(1))
    return dbs


now = datetime.datetime.now()

config_filename = 'config.json'
with open(config_filename, 'r') as config_file:
    config = json.load(config_file)

twitter_html_dir = config['twitter']['html_dir']

tweets = {}
tweet_count_per_country = {}
for orig_json_tweet_file in glob.glob(f"{twitter_html_dir}/**/orig/**/*[0-9].json", recursive=True):
    process_tweet_file(orig_json_tweet_file)
for country in sorted(tweet_count_per_country.keys()):
    print(f"{country}: {tweet_count_per_country[country]}")
total_tweets = sum(tweet_count_per_country.values())
print(f"total_tweets={total_tweets}")
