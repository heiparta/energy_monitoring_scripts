#!/usr/bin/env python3
import argparse
import logging
import requests
import yaml

from datetime import datetime, timedelta

BASE_URL = "https://oma.hso.fi/"
LOGIN_PATH = "login.php"
DATA_PATH = "getdata_excel.php"

class ConfigError(Exception):
    pass

class HSO():
    def __init__(self, config):
        required_items = ["username", "password"]
        for i in required_items:
            if i not in config:
                raise ConfigError("Missing required config item {}".format(i))
        self.config = config

    def do_login(self):
        data = dict(username = self.config['username'],
                    password=self.config['password'],
                    loginbtn="login",)
        headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://oma.hso.fi",
                "DNT": "1",
                "Referer": "https://oma.hso.fi/sivu/fi/",
                "Connection": "keep-alive",
                "Accept-Language": "fi-FI,fi;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0",
                "Upgrade-Insecure-Requests": "1",
                }
        self.session = requests.Session()
        resp = self.session.post(BASE_URL + LOGIN_PATH, data=data, headers=headers)
        resp.raise_for_status()

    def get_data(self, start, end):
        headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                }
        urlparams = dict(
                type="interval",
                temp="1",
                start=start.strftime("%d.%m.%Y."),
                end=end.strftime("%d.%m.%Y."),
                changekp="3",
            )
        resp = self.session.get(BASE_URL + DATA_PATH, params=urlparams, headers=headers)
        resp.raise_for_status()
        return resp.content


def main(args):
    """ Main entry point of the app """
    config = dict()
    with open(args.config, "r") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    hso = HSO(config)
    hso.do_login()
    end = datetime.utcnow()
    start = end - timedelta(weeks=1)
    data = hso.get_data(start, end)
    output_filename = "data_current.xlsx"
    with open(output_filename, "wb") as f:
        f.write(data)


if __name__ == "__main__":
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbosity (-v, -vv, etc)")

    args = parser.parse_args()
    if not args.config:
        parser.print_usage()
        exit(1)
    main(args)
