#!/usr/bin/env python3
import sys
import os
import requests
from string import Template
from functools import wraps
from flask import request, abort
from shutil import copyfile
sys.path.append('..')
from config import Config

app_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
configs = Config


def write_to_disk(campaign):
    '''
    Create a Flask app on disk with the data provided by the server
    '''
    # create campaigns folder if it doesnt exist
    if not os.path.isdir(os.path.join(app_dir, 'campaigns')):
        os.mkdir(os.path.join(app_dir, 'campaigns'))
    
    id = str(int(campaign[0]['id']))
    campaign_dir = os.path.join(app_dir, 'campaigns', id)
    
    # create campaign dir
    if not os.path.isdir(campaign_dir):
        os.mkdir(campaign_dir)

    # create basic app folder structure
    if not os.path.isdir(os.path.join(campaign_dir, 'app')):
        os.mkdir(os.path.join(campaign_dir, 'app'))
    if not os.path.isdir(os.path.join(campaign_dir, 'app', 'templates')):
        os.mkdir(os.path.join(campaign_dir, 'app', 'templates'))
    if not os.path.isdir(os.path.join(campaign_dir, 'app', 'static')):
        os.mkdir(os.path.join(campaign_dir, 'app', 'static'))
    copyfile(os.path.join(app_dir, 'templates', 'pixel.png'), os.path.join(campaign_dir, 'app', 'static', 'pixel.png'))

     # create campaigns/<id>/app.py
    with open(os.path.join(campaign_dir, 'app.py'), 'w') as f:
        f.write('#!/usr/bin/env python3\nfrom app import app')

    # create campaigns/<id>/app/__init__.py
    with open(os.path.join(campaign_dir, 'app', '__init__.py'), 'w') as f:
        tmp = open(os.path.join(app_dir, 'templates', '__init__.txt')).read()
        f.write(tmp)

    # create campaigns/<id>/app/routes.py
    routes_template = Template(open(os.path.join(app_dir, 'templates', 'routes.txt')).read())

    values = {'url1': '/', 'url2': '/', 'url3': '/','url4': '/', 'url5': '/', 'redirect_url': '/'}
    values['url1'] = '/google'

    with open(os.path.join(campaign_dir, 'app', 'routes.py'), 'w') as f:
        f.write(routes_template.substitute(values))

    # create templates in campaigns/<id>/templates
    for idx, page in enumerate(campaign[0]['pages']):
        template_name = '%d.html' % (idx + 1)
        with open(os.path.join(campaign_dir, 'app', 'templates', template_name), 'w') as f:
            f.write(page['html'])


def require_api_key(f):
    '''
    Require an API key be provided to a function
    '''
    @wraps(f)
    def wrap(*args, **kwargs):
        if request.args.get('key') and request.args.get('key') == configs.API_KEY:
            return f(*args, **kwargs)
        else:
            abort(401)
    return wrap


def report_action(tracker, action):
    '''
    Report a hit on /static/pixel.png for a target ID to the redlure server
    '''
    url = 'https://%s:%d/results/update' % (configs.SERVER_IP, configs.SERVER_PORT)
    params = {'key': configs.API_KEY}
    payload = {'tracker': tracker, 'action': action}
    r = requests.post(url, data=payload, params=params, verify=False)


    