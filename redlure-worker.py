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
    configs = Config

    # generate certs if they dont exist
    ssl = (configs.CERT_PATH, configs.KEY_PATH)
    if ssl == ('redlure-cert.pem', 'redlure-key.pem'):
        if not os.path.isfile('redlure-cert.pem') or not os.path.isfile('redlure-key.pem'):
            gen_certs()
    
    # start the server
    #subprocess.Popen(['gunicorn', 'redlure-worker:app', '-b 0.0.0.0:8000', '--certfile', 'redlure-cert.pem', '--keyfile', 'redlure-key.pem'])
    app.run(host='0.0.0.0', port=configs.PORT, ssl_context=ssl)