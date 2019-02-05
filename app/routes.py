#!/usr/bin/env python3
from app import app
from flask import request, jsonify
from app.models import CampaignSchema
from app.functions import write_to_disk, require_api_key
import subprocess
import os
import signal
import psutil

subprocesses = {}

@app.route('/start', methods=['POST'])
@require_api_key
def start():
    # get the json campaign object
    json = request.get_json()[0]
    schema = CampaignSchema(strict=True)
    campaign = schema.load(json)

    write_to_disk(campaign)

    # start the subprocess running the campaigns flask server
    chdir = 'campaigns/%d' % campaign[0]['id']
    proc = subprocess.Popen(['gunicorn', '--chdir', chdir, 'app:app', '-b 0.0.0.0:8080', '--daemon'])

    # add the subprocess object to the dict, using campaign id as the key
    global subprocesses
    subprocesses[str(int(campaign[0]['id']))] = proc
    return 'campaign started'


@app.route('/kill', methods=['POST'])
@require_api_key
def kill():
    # get the campaign id
    id = str(request.form.get('id'))

    # get the subprocess objec to kill
    proc = subprocesses.get(id)

    # add 2 to the PID - tested on Ubuntu and Kali - for some reason the 
    # actual process is a child or grandchild fof the dict process
    p = psutil.Process(proc.pid + 2)

    p.terminate()
    return 'campaign killed'

