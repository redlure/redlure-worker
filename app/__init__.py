from flask import Flask
import logging
from logging.handlers import RotatingFileHandler
import os

app = Flask(__name__)

from app import routes, models

# create logs dir if it does not exist
if not os.path.exists('logs'):
    os.mkdir('logs')

# log using rotatingfilehandler, capping log files at 10240 bytes and storing up to 10 logfiles
file_handler = RotatingFileHandler('logs/redlure-worker.log', maxBytes=10240, backupCount=10)

# Set the format and level for the log messages
formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]', datefmt='%m-%d-%y %H:%M')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

# Add the handler and set the required level
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.DEBUG)


