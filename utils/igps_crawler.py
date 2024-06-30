#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
igps crawler.
"""

import argparse
import logging
import math
import json
import os
import sys
import time

import requests

REQUEST_INTERVAL = 5 # web请求间隔5s

class IGPSCrawler(object):
    """
    IGPS Crawler.
    """
    URLS = {
        'login': 'https://my.igpsport.com/Auth/Login',
        'logout': 'https://my.igpsport.com/account/logout',
        'activity_list': 'https://my.igpsport.com/Activity/ActivityList',
        'my_activity_list': 'https://my.igpsport.com/Activity/MyActivityList',
        'activity_url': 'https://my.igpsport.com/fit/activity?type={}&rideid={}'
    }

    FILE_TYPES = {
        '0': '.fit',
        '1': '.gpx',
        '2': '.tcx',
    }

    def __init__(self, username=None, password=None) -> None:
        self.username = username
        self.password = password

        self.session = requests.Session()
        headers ={
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.28 Safari/537.36',
        }
        self.session.headers = headers
    
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
        time.sleep(REQUEST_INTERVAL)
        self.logout()
    
    def get_activity_list(self, page=1, my_activity_list=False):
        """
        request my activity list/activity list page and return json data.
        """
        if my_activity_list:
            logging.debug('request my activity list page {}'.format(page))
            url = self.URLS['my_activity_list']
        else:
            logging.debug('request activity list page {}'.format(page))
            url = self.URLS['activity_list']

        url = url + '?pageindex={}'.format(page)
        res = self.session.get(url)
        if res.status_code == 200:
            data = res.json()
        else:
            logging.warning('page {} request failed.'.format(page))
            data = {}
        
        return data
    
    def get_total_activity_nums(self):
        """
        get total activity nums.
        """
        total_num = 0
        data = self.get_activity_list()
        total_num = data.get('total', 0)
        return total_num
    
    def get_all_activities_between_pages(self, page_start=1, page_end=None, page_nums=10, my_activity_list=False):
        """
        get all activities from activity list or my activity list.
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
                logging.warning('total activity nums is 0.')
                return activities
            else:
                page_end = math.ceil(total_num / page_nums)
        
        # get all data.
        for p in range(page_start, page_end + 1):
            p_data = self.get_activity_list(page=p)
            activities.extend(p_data.get('item', []))
            time.sleep(REQUEST_INTERVAL)
            
        
        logging.debug('got {} activies.'.format(len(activities)))

        return activities
    
    def read_json_data(self, json_file):
        """
        read saved activity json file.
        """
        logging.debug('read saved activities json file.')
        activities = []
        with open(json_file) as f:
            activities = json.load(f)
        
        return activities
    
    def download_activity_by_ride_id(self, ride_id, out_filename, file_type='0'):
        """
        download activity file by ride id.
        file type:
            0 -> fit.
            1 -> gpx.
            2 -> tcx.
        return: True/False.
        """
        logging.debug('download rideid {} activity file, type {}'.format(ride_id, file_type))
        assert file_type in self.FILE_TYPES
        url = self.URLS['activity_url'].format(file_type, ride_id)
        res = self.session.get(url)
        if res.status_code == 200:
            if len(res.content):
                with open(out_filename, 'wb') as o:
                    o.write(res.content)
                logging.debug('download successfully.')
                return True
            else:
                logging.warning('request successfully, but content is empty. account may be blocked.')
                return False
        else:
            logging.warning('download rideid {} activity file, type {} failed, pass'.format(ride_id, file_type))
            return False

    def download(self, out_dir=None, saved_json=None, page_start=1, page_end=None, fit=True, gpx=False, tcx=False):
        """
        download all activity files.
        """
        logging.info('download activities files.')

        out_dir = out_dir if out_dir else os.getcwd()

        # login.
        self.login()

        # get website activities.
        target_activities = self.get_all_activities_between_pages(page_start=page_start, page_end=page_end)

        # get saved actitivies.
        saved_activities = []
        if saved_json and os.path.exists(saved_json):
            saved_activities = self.read_json_data(json_file=saved_json)
        saved_ride_ids = [a['RideId'] for a in saved_activities]
        
        # wanted activities.
        wanted_activities = [a for a in target_activities if a['RideId'] not in saved_ride_ids]
        
        # download.
        downloaded_activities = []
        for a in wanted_activities:
            logging.debug(a)
            ride_id = a['RideId']
            start_time = a['StartTime'].replace(' ', '.').replace(':', '-')
            downloaded_flags = []
            for tag in self.FILE_TYPES:
                ext = self.FILE_TYPES[tag]

                # download or not.
                if not fit and ext == '.fit':
                    continue

                if not gpx and ext == '.gpx':
                    continue

                if not tcx and ext == '.tcx':
                    continue

                out_name = '{}.igps.{}'.format(start_time, ride_id) + ext
                out_path = os.path.join(out_dir, out_name)
                flag = self.download_activity_by_ride_id(ride_id, out_path, file_type=tag)
                downloaded_flags.append(flag)
                time.sleep(REQUEST_INTERVAL)
            
            # 所有需要下载的文件都为true，则该ride id记录保存.
            if all(downloaded_flags):
                downloaded_activities.append(a)
            else:
                logging.warning('ride id {} not all files downloaded.'.format(ride_id))
        
        # update saved activities json file.
        if saved_json:
            logging.info('save activities to json file.')
            saved_activities.extend(downloaded_activities)
            with open(saved_json, 'wt') as o:
                json.dump(saved_activities, o, indent=4)

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
        if any([args.fit, args.gpx, args.tcx]):
            igps_crawler.download(
                out_dir=args.out_dir, 
                saved_json=args.json,
                page_start=args.page_start, 
                page_end=args.page_end,
                fit=args.fit,
                gpx=args.gpx,
                tcx=args.tcx,
                )
        else:
            logging.warning('download given, but no fit, gpx or tcx. nothing to be done.')
            sys.exit(0)


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description="igps crawler.")
    arg_parser.add_argument('-u', help='username.', required=True)
    arg_parser.add_argument('-p', help='password.', required=True)
    arg_parser.add_argument('--download', help='download all data file.', action='store_true', default=False)
    arg_parser.add_argument('--out-dir', help='output dir for saving activity file.')
    arg_parser.add_argument('--json', help='saved activities in json file.')
    arg_parser.add_argument('--fit', help='download fit file', action='store_true', default=False)
    arg_parser.add_argument('--gpx', help='download gpx file', action='store_true', default=False)
    arg_parser.add_argument('--tcx', help='download tcx file', action='store_true', default=False)
    arg_parser.add_argument('--page_start', help='page start num', default=1, type=int)
    arg_parser.add_argument('--page_end', help='page end num', default=None, type=int)
    arg_parser.add_argument('--debug', help='debug log mode.', action='store_true', default=False)

    args = arg_parser.parse_args(sys.argv[1:])

    main(args)
