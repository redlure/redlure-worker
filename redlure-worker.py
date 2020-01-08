#!/usr/bin/env python3
from app import app
import subprocess
import os
import shlex
from config import Config
import shutil


def gen_certs():
    proc = subprocess.Popen(shlex.split('openssl req -x509 -newkey rsa:4096 -nodes -subj "/" -out redlure-cert.pem -keyout redlure-key.pem -days 365'))
    proc.wait()

if __name__ == '__main__':
    if Config.API_KEY == '' or Config.SERVER_IP == '':
        print('[!] API_KEY and SERVER_IP attributes required to be set in config.py')
        exit()

    # generate certs if they dont exist
    ssl = (Config.CERT_PATH, Config.KEY_PATH)
    if ssl == ('redlure-cert.pem', 'redlure-key.pem'):
        if not os.path.isfile('redlure-cert.pem') or not os.path.isfile('redlure-key.pem'):
            gen_certs()

    # start the server
    #subprocess.Popen(['gunicorn', 'redlure-worker:app', '-b 0.0.0.0:8000', '--certfile', 'redlure-cert.pem', '--keyfile', 'redlure-key.pem'])
    app.run(debug=True, host='0.0.0.0', port=Config.WORKER_PORT, ssl_context=ssl)
