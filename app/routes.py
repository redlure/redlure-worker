#!/usr/bin/env python3
from app import app
from flask import request, jsonify
from app.models import CampaignSchema
from app.functions import write_to_disk
import subprocess
import os
import signal
import psutil

subprocesses = {}


@app.route('/start', methods=['POST'])
def start():
    json = request.get_json()[0]
    schema = CampaignSchema(strict=True)
    campaign = schema.load(json)
    write_to_disk(campaign)
    chdir = 'campaigns/%d' % campaign[0]['id']
    proc = subprocess.Popen(['gunicorn', '--chdir', chdir, 'app:app', '-b 0.0.0.0:8080', '--daemon'])
    global subprocesses
    subprocesses[str(campaign[0]['id'])] = proc
    print(proc.pid)
    return 'campaign started'


@app.route('/kill', methods=['POST'])
def kill():
    #port = request.form.get('port')
    #print(port)
    for key, val in subprocesses.items():
        print(val.pid)
        p = psutil.Process(val.pid + 2)
        p.terminate()
        #os.kill(os.getpgid(val.pid), signal.SIGTERM)
    return 'x'

