#!/usr/bin/env python3
from app import app
from flask import request, jsonify
from app.models import CampaignSchema
from helper.functions import write_to_disk, require_api_key, check_procs
import subprocess
import os
import signal
import psutil
import shutil
import shlex


@app.route('/campaigns/start', methods=['POST'])
@require_api_key
def start():
    # get the json campaign object
    json = request.get_json()[0]
    schema = CampaignSchema(strict=True)
    campaign = schema.load(json)

    write_to_disk(campaign)

    port = int(campaign[0]['port'])
    existing_proc = check_procs(port)

    if existing_proc is not None:
        return '%s running in process %d' % (existing_proc.name(), existing_proc.pid), 400
    
    cert = campaign[0]['domain']['cert_path']
    key = campaign[0]['domain']['key_path']

    # start the subprocess running the campaigns flask server
    chdir = 'campaigns/%d' % campaign[0]['id']
    if campaign[0]['ssl']:
        subprocess.Popen(shlex.split('pipenv run gunicorn --chdir %s app:app -b 0.0.0.0:%s --daemon --keyfile %s --certfile %s' % (chdir, port, key, cert)))
    else:
        subprocess.Popen(shlex.split('pipenv run gunicorn --chdir %s app:app -b 0.0.0.0:%s --daemon' % (chdir, port)))
    return 'campaign started'


@app.route('/campaigns/kill', methods=['POST'])
@require_api_key
def kill():
    # get the port the campaign is running on adn campaign id
    port = int(request.form.get('port'))
    id = request.form.get('id')

    check_procs(port, True)

    # remove files from disk
    shutil.rmtree('campaigns/%s' % id)

    return 'campaign killed'


@app.route('/status')
@require_api_key
def status():
    return 'responsive', 200


@app.route('/certificates/generate', methods=['POST'])
@require_api_key
def generate_cert():
    domain = request.form.get('domain')
    proc = subprocess.Popen(shlex.split('certbot certonly --standalone -d %s --non-interactive' % domain))
    proc.wait()
    return 'certs generated'