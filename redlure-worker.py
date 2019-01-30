#!/usr/bin/env python3
from app import app
import subprocess
import os
import shlex


def gen_certs():
    proc = subprocess.Popen(shlex.split('openssl req -x509 -newkey rsa:4096 -nodes -subj "/" -out redlure-cert.pem -keyout redlure-key.pem -days 365'))
    proc.wait()


if __name__ == '__main__':
    # generate certs if they dont exist
    if not os.path.isfile('redlure-cert.pem') or not os.path.isfile('redlure-key.pem'):
        gen_certs()
    
    # start the server
    #subprocess.Popen(['gunicorn', 'redlure-server:app', '-b 0.0.0.0:8000', '--certfile', 'redlure-cert.pem', '--keyfile', 'redlure-key.pem'])
    app.run(debug=True, host='0.0.0.0', port=8000, ssl_context=('redlure-cert.pem','redlure-key.pem'))