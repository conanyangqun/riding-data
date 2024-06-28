#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
igps crawler.
"""

import argparse

class IGPSCrawler(object):
    """
    IGPS Crawler.
    """
    URLS = {
        'login': 'https://my.igpsport.com/Auth/Login',
        'activity_list': 'https://my.igpsport.com/Activity/ActivityList',
        'logout': 'https://my.igpsport.com/account/logout',
    }
