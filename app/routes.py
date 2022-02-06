#!/usr/bin/env python3
from app import app
from flask import request, jsonify
from app.models import CampaignSchema
from app.functions import write_to_disk, require_api_key, check_procs, contact_console
import subprocess
import os
import signal
import psutil
import shutil
import shlex
import json
import socket
from socket import AF_INET, SOCK_STREAM, SOCK_DGRAM
from werkzeug.utils import secure_filename
from config import Config

@app.route('/campaigns/start', methods=['POST'])
@require_api_key
def start():
    # get the json campaign object
    data = request.get_json()
    schema = CampaignSchema()
    campaign = schema.load(data)

    write_to_disk(campaign)

    port = int(campaign['port'])
    id = campaign['id']
    existing_proc = check_procs(port)

    if existing_proc is not None:
        app.logger.warning(f'Could not bind campaign {id} to port {port}. Campaign {id} did not start')
        shutil.rmtree('campaigns/%s' % str(int(id)))
        return json.dumps({'success': False, 'msg': f'Failed: Process {existing_proc.name()} using port {port} already'}), 200, {'ContentType':'application/json'}

    cert = campaign['domain']['cert_path']
    key = campaign['domain']['key_path']

    # start the subprocess running the campaign's gunicorn server
    chdir = 'campaigns/%d' % campaign['id']
    logfile = os.path.abspath(f'{chdir}/gunicorn3.log')

    # create the logfile
    with open(logfile, 'w') as f:
        pass

    if campaign['ssl']:
        if not os.path.exists(cert) or not os.path.exists(key):
            app.logger.warning(f'Failed to start campaign {id}. Error accessing cert file {cert} or key file {key}')
            shutil.rmtree('campaigns/%s' % str(int(id)))
            return json.dumps({'success': False, 'msg': 'Failed: Error accessing cert/key files'}), 200, {'ContentType':'application/json'}
        app.logger.info(f'Starting campaign {id} with SSL on port {port}')
        subprocess.Popen(shlex.split('gunicorn3 --chdir %s app:app -b 0.0.0.0:%s --daemon --keyfile %s --certfile %s --log-file %s --capture-output --access-logfile %s' % (chdir, port, key, cert, logfile, logfile)))
    else:
        app.logger.info(f'Starting campaign {id} without SSL on port {port}')
        subprocess.Popen(shlex.split('gunicorn3 --chdir %s app:app -b 0.0.0.0:%s --daemon --log-file %s --capture-output --access-logfile %s' % (chdir, port, logfile, logfile)))

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
        app.logger.info(f'Campaign {id} killed and campaign directory deleted')
        return json.dumps({'success': True}), 200, {'ContentType':'application/json'}
    except Exception as e:
        app.logger.error(f'Error killing campaign {id} and removing files')
        return 'Error Killing Campaign', 400


@app.route('/status', methods=['POST'])
@require_api_key
def status():
    app.logger.info('Received check-in from console')
    console_code = contact_console(False)

    if console_code == 2:
        app.logger.warning('Worker is unsupported by console. Update worker')
        return json.dumps({'success': False, 'msg': 'Unsupported worker version'}), 200, {'ContentType':'application/json'}
    elif console_code == 1:
        app.logger.info('Checked in with console')
        return json.dumps({'success': True}), 200, {'ContentType':'application/json'}
    elif console_code == 0:
        app.logger.warning('Unable to check-in with console. Firewall may be blocking traffic')
        return json.dumps({'success': False, 'msg': 'Worker to console comms failed.'}), 200, {'ContentType':'application/json'}

@app.route('/certificates/generate', methods=['POST'])
@require_api_key
def generate_cert():
    domain = request.form.get('domain')
    try:
        proc = subprocess.run(shlex.split('certbot certonly --standalone -d %s --non-interactive --register-unsafely-without-email --agree-tos' % domain), capture_output=True)
        if b'not yet due for renewal' in proc.stdout:
            app.logger.info(f'Attemped to renew cert for {domain} but not yet due for renewal')
            return json.dumps({'success': False, 'msg': 'Certificate not due for renewal'}), 200, {'ContentType':'application/json'}
        elif b'Congratulations!' in proc.stdout or b'Successfully received certificate' in proc.stdout:
            cert_path = f'/etc/letsencrypt/live/{domain}/cert.pem'
            key_path = f'/etc/letsencrypt/live/{domain}/privkey.pem'
            return json.dumps({'success': True, 'cert_path': cert_path, 'key_path': key_path}), 200, {'ContentType':'application/json'}
        else:
            app.logger.warning(f'Failed to generate certificates for {domain}')
            return json.dumps({'success': False, 'msg': 'Failed to generate certificates'}), 200, {'ContentType':'application/json'}
    except Exception as e:
        app.logger.error(f'Error generating certificates for {domain} - {e}')
        return json.dumps({'success': False, 'msg': 'Error generating certificates'}), 200, {'ContentType':'application/json'}


@app.route('/certificates/check', methods=['POST'])
@require_api_key
def check_certs():
    cert_path = request.form.get('cert_path')
    key_path = request.form.get('key_path')

    cert_exists = os.path.isfile(cert_path)
    key_exists = os.path.isfile(key_path)

    if not cert_exists or not key_exists:
        app.logger.warning(f'Key file {key_path} or cert file {cert_path} not found')
        return json.dumps({'exists': False, 'msg': 'The specified cert path or key path does not exist on the file system'}), 200, {'ContentType': 'application/json'}
    return json.dumps({'exists': True}), 200, {'ContentType':'application/json'}


@app.route('/processes/kill', methods=['POST'])
@require_api_key
def kill_process():
    port = int(request.form.get('port'))
    check_procs(port, kill=True)
    proc = check_procs(port)
    if proc:
        return 'error kiling process', 400
    else:
        app.logger.info(f'Process running on {port} killed')
        return 'process killed', 200


@app.route('/files', methods=['POST'])
@require_api_key
def get_files():
    files = []
    try:
        files = os.listdir(Config.UPLOAD_FOLDER)
    except Exception as e:
        app.logger.error(f'Error listing {Config.UPLOAD_FOLDER} - {e}')
    app.logger.info(f'Returned listing of {Config.UPLOAD_FOLDER}')
    return json.dumps({'files': files}), 200, {'ContentType':'application/json'}


@app.route('/files/upload', methods=['POST'])
@require_api_key
def upload_file():
    try:
        file = request.files['file']
        filename = request.form.get('Filename')
        if file.filename == '':
            return json.dumps({'success': False}), 200, {'ContentType':'application/json'}
        if not os.path.isdir(Config.UPLOAD_FOLDER):
            app.logger.info(f'Made directory {Config.UPLOAD_FOLDER}')
            os.makedirs(os.path.join(Config.UPLOAD_FOLDER, ''))
        filename = secure_filename(filename)
        file.save(os.path.join(Config.UPLOAD_FOLDER, filename))
        app.logger.info(f'Wrote file {filename} to {Config.UPLOAD_FOLDER}')
        return json.dumps({'success': True}), 200, {'ContentType':'application/json'}
    except Exception as e:
        app.logger.error(f'Error writing file {filename} to {Config.UPLOAD_FOLDER} - {e}')
        return json.dumps({'success': False}), 200, {'ContentType':'application/json'}


@app.route('/files/deleteall', methods=['POST'])
@require_api_key
def delete_all_file():
    try:
        shutil.rmtree(Config.UPLOAD_FOLDER)
    except Exception as e:
        app.logger.error(f'Error deleting all files from {Config.UPLOAD_FOLDER} - {e}')
        return json.dumps({'success': False}), 200, {'ContentType':'application/json'}
    app.logger.info(f'All files deleted from {Config.UPLOAD_FOLDER}')
    return json.dumps({'success': True}), 200, {'ContentType':'application/json'}


@app.route('/files/delete', methods=['POST'])
@require_api_key
def delete_file():
    try:
        filename = request.form.get('Filename')
        os.remove(os.path.join(Config.UPLOAD_FOLDER, secure_filename(filename)))
    except Exception as e:
        app.logger.error(f'Error deleting file {filename} from {Config.UPLOAD_FOLDER} - {e}')
        return json.dumps({'success': False}), 200, {'ContentType':'application/json'}
    app.logger.info(f'Deleted file {filename} from {Config.UPLOAD_FOLDER}')
    return json.dumps({'success': True}), 200, {'ContentType':'application/json'}


@app.route('/processes/check', methods=['POST'])
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
        app.logger.info('Returned listening processes')
        return json.dumps({'success': True, 'data': procs}), 200, {'ContentType':'application/json'}
    except Exception as e:
        app.logger.error(f'Error checking listening processes - {e}')
        return json.dumps({'success': False}), 200, {'ContentType':'application/json'}
