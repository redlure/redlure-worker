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
import json
import socket
from socket import AF_INET, SOCK_STREAM, SOCK_DGRAM


@app.route('/campaigns/start', methods=['POST'])
@require_api_key
def start():
    # get the json campaign object
    print(request.get_json())
    data = request.get_json()
    schema = CampaignSchema(strict=True)
    campaign = schema.load(data)

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
        subprocess.Popen(shlex.split('gunicorn3 --chdir %s app:app -b 0.0.0.0:%s --daemon --keyfile %s --certfile %s' % (chdir, port, key, cert)))
    else:
        subprocess.Popen(shlex.split('gunicorn3 --chdir %s app:app -b 0.0.0.0:%s --daemon' % (chdir, port)))
    return json.dumps({'success': True}), 200, {'ContentType':'application/json'}


@app.route('/campaigns/kill', methods=['POST'])
@require_api_key
def kill():
    try:
        # get the port the campaign is running on adn campaign id
        port = int(request.form.get('port'))
        id = request.form.get('id')

        check_procs(port, True)

        # remove files from disk
        shutil.rmtree('campaigns/%s' % id)

        return json.dumps({'success': True}), 200, {'ContentType':'application/json'}
    except:
        return 'Error Killing Campaign', 400


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


@app.route('/processes/kill', methods=['POST'])
@require_api_key
def kill_process():
    port = int(request.form.get('port'))
    check_procs(port, kill=True)
    proc = check_procs(port)
    if proc:
        return 'error kiling process', 400
    else:
        return 'process killed', 200


@app.route('/processes/check')
@require_api_key
def check_listening():
    AD = "-"
    AF_INET6 = getattr(socket, 'AF_INET6', object())
    proto_map = {
        (AF_INET, SOCK_STREAM): 'tcp',
        (AF_INET6, SOCK_STREAM): 'tcp6',
        (AF_INET, SOCK_DGRAM): 'udp',
        (AF_INET6, SOCK_DGRAM): 'udp6',
    }

    # code modded from https://github.com/giampaolo/psutil/blob/master/scripts/netstat.py
    procs = []
    # templ % ("Proto", "Local address", "Status", "PID", "Program name")
    try:
        proc_names = {}
        for p in psutil.process_iter(attrs=['pid', 'name']):
            proc_names[p.info['pid']] = p.info['name']
        for c in psutil.net_connections(kind='inet'):
            if c.status =='LISTEN':
                laddr = "%s:%s" % (c.laddr)
                raddr = ""
                if c.raddr:
                    raddr = "%s:%s" % (c.raddr)
                procs.append(
                    {
                        'protocol': proto_map[(c.family, c.type)],
                        'localaddr': laddr,
                        'status': c.status,
                        'pid': c.pid,
                        'name': proc_names.get(c.pid, '?')[:15]
                    }
                )
        return json.dumps({'success': True, 'data': procs}), 200, {'ContentType':'application/json'}
    except:
        return json.dumps({'success': False}), 200, {'ContentType':'application/json'}
