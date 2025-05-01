# coding: utf-8
"""
"""
import os

port = int(os.environ.get('PORT0', 8988))
bind = ['0.0.0.0:{}'.format(port)]
workers = 6
max_requests = 20000
timeout = 30
