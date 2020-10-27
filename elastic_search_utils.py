from datetime import date, datetime, timedelta
from dateutil import tz
from elasticsearch import Elasticsearch, TransportError
import os


def datetime_from_iso_format(str_timestamp):
    date_str = str_timestamp[:10]
    time_str = str_timestamp[11:]
    year, month, day = date_str.split('-')
    hh, mm, ss = time_str.split(':')
    return datetime(int(year), int(month), int(day), int(hh), int(mm), int(ss))


class ElasticSearchImporter:

    def __init__(self, host, port, index, html_dir, lang, logger=None):
        self.index = index
        self.html_dir = html_dir
        self.lang = lang
        self.logger = logger

        self.es = Elasticsearch([f'http://{host}:{port}'], use_ssl=False)

    def update_record(self, input_file):
        "Import a page into Elastic Search database."
        "Returns the record_id if the page has been successfully imported."
        "None otherwise."
        if self.logger is not None:
            self.logger.info(f"ES update_record: {input_file}")

        dirs = input_file[len(self.html_dir) + 1:].split("/")
        region = dirs[0]
        domain = dirs[2]

        path = "/".join(dirs[3:-4])
        if self.logger is not None:
            self.logger.debug(f"region={region} domain={domain} path={path}")

        timestamp_year = dirs[-4]
        timestamp_month = dirs[-3]
        timestamp_day_time = dirs[-2]

        if self.logger is not None:
            self.logger.debug(f"timestamp_year={timestamp_year} timestamp_month={timestamp_month} timestamp_day_time={timestamp_day_time}")

        timestamp_day, timestamp_hh, timestamp_mm = timestamp_day_time.split("-")
        timestamp_local = datetime(int(timestamp_year), int(timestamp_month), int(timestamp_day), int(timestamp_hh), int(timestamp_mm))
        timestamp_utc = timestamp_local.astimezone(tz.gettz('UTC')).replace(tzinfo=None)
        filename = dirs[-1][:-4]

        record_id = "/".join([region, domain, path, filename])

        must_index_record = False
        if (self.es.exists(index=self.index, id=record_id)):
            index_record = self.es.get(index=self.index, id=record_id)
            index_record_timestamp_str = index_record['_source']['timestamp']['local']
            if self.logger is not None:
                self.logger.debug(f"index_record={index_record}")
            index_record_timestamp = datetime_from_iso_format(index_record_timestamp_str)
            if timestamp_local > index_record_timestamp:
                if self.logger is not None:
                    self.logger.info(f"timestamp is newer!!! rec_id={record_id} file_ts={timestamp_local} ndx_rec_ts={index_record_timestamp}")
                must_index_record = True
        else:
            must_index_record = True

        if must_index_record:
            url_filename = f"{self.html_dir}/{region}/orig/{domain}/{path}/{timestamp_year}/{timestamp_month}/{timestamp_day_time}/{filename}.url"
            txt_filename = f"{self.html_dir}/{region}/{self.lang}_translated/{domain}/{path}/{timestamp_year}/{timestamp_month}/{timestamp_day_time}/{filename}.txt"
          
            if self.logger is not None:
                self.logger.debug(f"record_id={record_id} url_filename={url_filename} txt_filename={txt_filename}")

            if not os.path.isfile(url_filename):
                if self.logger is not None:
                    self.logger.info(f"url_file {url_filename} not found so skip it.")
                return None

            if not os.path.isfile(txt_filename):
                if self.logger is not None:
                    self.logger.info(f"txt_file {txt_filename}is not found so skip it.")
                return None

            with open(url_filename, encoding='utf-8') as url_file:
                url = url_file.read()

            with open(txt_filename, encoding='utf-8') as text_file:
                text = text_file.read()

            record = {
                'text': text,
                'region': region,
                'domain': domain,
                'path': path,
                'timestamp': {
                    'year': int(timestamp_year),
                    'month': int(timestamp_month),
                    'day': int(timestamp_day),
                    'hh': int(timestamp_hh),
                    'mm': int(timestamp_mm),
                    'local': timestamp_local,
                    'utc': timestamp_utc
                },
                'filename': filename,
                'url': url
            }

            if self.logger is not None:
                self.logger.debug(f"ES Record: id={record_id} content={record}")
            try:
                res = self.es.index(index=self.index, id=record_id, body=record)
                if self.logger is not None:
                    self.logger.debug(f"Response for es.index(id={record_id}) -> {res}")
            except TransportError as te:
                if self.logger is not None:
                    self.logger.info(f"An error has occurred when indexing record with id={record_id}: {te}")
                return None

            return record_id
