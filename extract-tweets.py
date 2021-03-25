import datetime
import glob
import json
from json import JSONDecodeError
import os
import re
import twitter
import utils

# # Uncomment to test import into Elastic Search database.
# from elastic_search_utils import ElasticSearchTwitterImporter

now = datetime.datetime.now()

config_filename = 'config.json'

with open(config_filename, 'r') as config_file:
    config = json.load(config_file)

db_dir = config['db_dir']
twitter_db_dir = f"{db_dir}/twitter"
twitter_html_dir = config['twitter']['html_dir']
run_dir = config['run_dir']

rejected_expressions = []
if "black_list" in config["twitter"]:
    with open(config['twitter']['black_list'], 'r') as rejected_expressions_file:
        for line in rejected_expressions_file:
            rejected_expressions.append(line.strip())

processed_databases = set()

# # Uncomment to test import into Elastic Search database.
# es_importer = {
#     'ja': ElasticSearchTwitterImporter(config['elastic_search']['host'], config['elastic_search']['port'], twitter_html_dir, 'ja'),
#     'en': ElasticSearchTwitterImporter(config['elastic_search']['host'], config['elastic_search']['port'], twitter_html_dir, 'en')
# }

def extract_date_from(db_filename):
    bn = os.path.basename(db_filename)
    return bn[bn.index("_") + 1:bn.index(".txt")]


def get_tweet_text(status):
    tweet_text = status.full_text if status.tweet_mode == 'extended' else status.text
    tweet_text = re.sub("https://t.co/\w+", "", tweet_text) # Remove urls from text.
    tweet_text = re.sub("#\w+\s*", "", tweet_text) # Remove hashtags from text.
    return tweet_text


def search_black_list(tweet_text):
    for expr in rejected_expressions:
        if expr in tweet_text:
            return expr
    return None


def write_tweet_data(tweet_id):
    print(f"write_tweet_data tweet_id={tweet_id}")
    try:
        tweet = tweets[tweet_id]
        timestamp = now.strftime('%Y-%m-%d-%H-%M')
        tweet_timestamp = datetime.datetime.fromtimestamp(tweet['status'].created_at_in_seconds)
        country_code_dir = utils.get_country_code_dir(tweet['country_code'])
        timestamp_path = tweet_timestamp.strftime('%Y/%m/%d/%H-%M')
        html_orig_tweet_dir = os.path.join(twitter_html_dir, country_code_dir, "orig", timestamp_path)
        os.makedirs(html_orig_tweet_dir, exist_ok=True)
        temp_path = html_orig_tweet_dir
        while temp_path != twitter_html_dir:
            os.chmod(temp_path, 0o775)
            temp_path = os.path.dirname(temp_path)

        print(f"tweet_path={html_orig_tweet_dir}")

        # EVen if the json file already exists, it's updated.
        json_filename = os.path.join(html_orig_tweet_dir, f"{tweet_id}.json")
        with open(json_filename, 'w') as json_file:
            json.dump(tweet['json'], json_file)

        # EVen if the metadata file already exists, it's updated.
        metadata_filename = os.path.join(html_orig_tweet_dir, f"{tweet_id}.metadata")
        with open(metadata_filename, 'w') as metadata_file:
            metadata = {
                "id": tweet_id,
                "country": tweet["country"],
                "country_code": tweet["country_code"],
                "count": tweet["count"]
            }
            json.dump(metadata, metadata_file)

        # Write html file only if it doesn't exist yet.
        tweet_text_for_html = get_tweet_text(tweet['status'])
        html_filename = os.path.join(html_orig_tweet_dir, f"{tweet_id}.html")
        if not os.path.exists(html_filename):
            with open(html_filename, 'w') as html_file:
                html_str = (
                    "<!DOCTYPE html>\n"
                    f"<html lang=\"{tweet['status'].lang}\">\n"
                    "<head><meta charset=\"utf-8\"/></head>\n"
                    "<body>\n"
                    f"<p>{tweet_text_for_html}</p>\n"
                    "</body>\n"
                    "</html>\n"
                )
                html_file.write(html_str)

            new_html_filename = os.path.join(run_dir, 'new-html-files', f'new-twitter-html-files-{timestamp}.txt')
            with open(new_html_filename, 'a') as new_html_file:
                new_html_file.write(html_filename)
                new_html_file.write("\n")

            # # Uncomment to test import into Elastic Search database.
            # es_index = config['elastic_search']['twitter_index_basename'] + '-' + tweet['status'].lang
            # es_importer[tweet['status'].lang].update_record(html_filename[:-4]+"txt", index=es_index, is_data_stream=True)

            if country_code_dir in tweet_count_per_country:
                tweet_count_per_country[country_code_dir] += 1
            else:
                tweet_count_per_country[country_code_dir] = 1
    except OSError as os_err:
        print(f"An error has occurred in write_tweet_data(tweet_id={tweet_id}) os_err={os_err}")


def write_stats_file(filename, tweet_count_per_country):
    if len(tweet_count_per_country) > 0:
        with open(filename, 'w') as stats_file:
            json.dump(tweet_count_per_country, stats_file)


def process_tweet(tweet_id, tweet_count, tweet_lang, tweet_country, tweet_json_str):
    tweet_json = json.loads(tweet_json_str)
    tweet_status = twitter.models.Status.NewFromJsonDict(tweet_json)
    tweet_text = get_tweet_text(tweet_status)

    # Skip tweets that contain rejected words.
    rejected_expr = search_black_list(tweet_text)
    if rejected_expr is not None:
        print(f"Tweet {tweet_id} has been skipped because it contains rejected expression: {rejected_expr}.")
        return

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

    write_tweet_data(tweet_id)

run_filename = os.path.join(run_dir, 'twitter.json')
if os.path.exists(run_filename):
    with open(run_filename, 'r') as run_file:
        run_data = json.load(run_file)
        print(f"run_data={run_data}")
        processed_databases = set(run_data)

for db_filename in sorted(glob.glob(f'{twitter_db_dir}/tweets_*.txt')):
    print(f"Processing {db_filename}")

    tweets = {}
    tweet_count_per_country = {}
    undefined_countries = set()

    with open(db_filename, 'r', encoding='latin-1') as twitter_data_file:
        for line in twitter_data_file:
            match = re.search("(\d+) (\d+) (\w+) ([-)'(\w]+) (\{.*\})", line)
            if match:
                tweet_id = int(match.group(1))
                tweet_count = int(match.group(2))
                tweet_lang = match.group(3)
                tweet_country = match.group(4)
                tweet_json_str = match.group(5)
                try:
                    process_tweet(tweet_id, tweet_count, tweet_lang, tweet_country, tweet_json_str)
                except JSONDecodeError as json_err:
                    print(f"Tweet {tweet_id} had invalid json and has been ignored. json_err={json_err}")
            else:
                print(f"Invalid line: {line}")

    processed_databases.add(extract_date_from(db_filename))

    if len(undefined_countries) > 0:
        utils.send_mail(config['mail']['from'], config['mail']['to'], config['mail']['cc'], None, "Undefined countries found",
            (f"Some tweets are referring to these countries: {sorted(undefined_countries)} but no corresponding ISO-3166-2 Alpha-2 code are defined.\n\n"
            "Adjust the country_codes.txt file accordingly to prevent this error from occurring again."))

    print(f"tweet_count_per_country={tweet_count_per_country}")

    stats_file = os.path.join(run_dir, 'twitter-stats', f"twitter-stats-{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')}.json")
    write_stats_file(stats_file, tweet_count_per_country)

    # Remove database to save disk space.
    if os.path.exists(db_filename):
        os.remove(db_filename)

# Remember that the file has been processed.
with open(run_filename, 'w') as run_file:
    json.dump(sorted(list(processed_databases)), run_file)
