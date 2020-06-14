#!/usr/bin/env python3
from app import app
import subprocess
import os
import shlex
from config import Config
import shutil
from app.functions import contact_console
import urllib3

# Suppress insecure requests warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

    print(f'[*] Contacting the redlure console at https://{Config.SERVER_IP}:{Config.SERVER_PORT}')
    if contact_console():
        print('[+] Successfully checked in with console')
    else:
        print('[-] Failed console check-in. Console may not be running or firewall is blocking communication\n')
        input('[ Press enter to continue booting the worker ]')

    # start the server
    #subprocess.Popen(['gunicorn', 'redlure-worker:app', '-b 0.0.0.0:8000', '--certfile', 'redlure-cert.pem', '--keyfile', 'redlure-key.pem'])
    app.logger.info('redlure-worker starting up')
    app.run(debug=False, host='0.0.0.0', port=Config.WORKER_PORT, ssl_context=ssl)
