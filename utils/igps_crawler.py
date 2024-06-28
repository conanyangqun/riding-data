#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
igps crawler.
"""

import argparse
import logging
import math
import sys
import time

import requests

class IGPSCrawler(object):
    """
    IGPS Crawler.
    """
    URLS = {
        'login': 'https://my.igpsport.com/Auth/Login',
        'logout': 'https://my.igpsport.com/account/logout',
        'activity_list': 'https://my.igpsport.com/Activity/ActivityList',
        'my_activity_list': 'https://my.igpsport.com/Activity/MyActivityList',
    }

    def __init__(self, username=None, password=None) -> None:
        self.username = username
        self.password = password

        self.session = requests.Session()
    
    def login(self):
        """
        login website.
        """
        if not self.username:
            raise ValueError("usename is empty.")
        if not self.password:
            raise ValueError("password is empty.")
        
        data = {
            'username': self.username,
            'password': self.password,
        }
        res = self.session.post(
            url=self.URLS['login'],
            data=data,
        )

        if res.status_code == 200:
            logging.info('login successfully.')
        else:
            logging.error('login failed.')
            logging.debug('status code: {}'.format(res.status_code))
            sys.exit(1)
    
    def logout(self):
        res = self.session.get(
            self.URLS['logout']
        )
        if res.status_code in [302, 200]:
            logging.info('logout successfully.')
        else:
            logging.error('logout failed.')
            logging.debug('status code: {}'.format(res.status_code))
            sys.exit(1)
    
    def test_login_and_logout(self):
        self.login()
        time.sleep(10)
        self.logout()
    
    def get_my_activity_list(self, page=1):
        """
        request my activity list page and return json data.
        """
        logging.debug('request my activity list page {}'.format(page))

        url = self.URLS['my_activity_list'] + '?pageindex={}'.format(page)
        res = self.session.get(url)
        if res.status_code == 200:
            data = res.json()
        else:
            logging.warning('my activity list page {} request failed.'.format(page))
            data = {}
        
        return data
    
    def get_total_activity_nums(self):
        """
        get total activity nums.
        """
        total_num = 0
        data = self.get_my_activity_list()
        total_num = data.get('total', 0)
        return total_num
    
    def get_all_activities_between_pages(self, page_start=1, page_end=None):
        """
        get all activities.
        """
        if page_end:
            logging.info('request activities between page {} and page {}.'.format(page_start, page_end))
        else:
            logging.info('request activities from page {} to end.'.format(page_start))
        
        activities = []
        
        # cal page end.
        if not page_end:
            total_num = self.get_total_activity_nums()
            if total_num == 0:
                page_end = 1
            else:
                page_end = math.ceil(total_num / 15.0)
        
        # get all data.
        for p in range(page_start, page_end + 1):
            p_data = self.get_my_activity_list(page=p)
            activities.extend(p_data.get('item', []))
        
        logging.debug('got {} activies.'.format(len(activities)))

        return activities

    def download(self, saved_json=None, page_start=1, page_end=None):
        """
        download all activity files.
        """
        # login.
        self.login()

        activities = self.get_all_activities_between_pages(page_start=page_start, page_end=page_end)

        # logout.
        self.logout()


def main(args):
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(filename)s %(levelname)s %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(filename)s %(levelname)s %(message)s')
    
    igps_crawler = IGPSCrawler(username=args.u, password=args.p)
    
    # download data.
    if args.download:
        igps_crawler.download(page_end=1)

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description="igps crawler.")
    arg_parser.add_argument('-u', help='username.')
    arg_parser.add_argument('-p', help='password.')
    arg_parser.add_argument('--download', help='download all data file.', action='store_true', default=False)
    arg_parser.add_argument('--year', help='download x year data', default='2024')
    arg_parser.add_argument('--debug', help='debug log mode.', action='store_true', default=False)

    args = arg_parser.parse_args(sys.argv[1:])

    main(args)
