from app import app
from flask import request, jsonify
from app.models import CampaignSchema

class Phish:
    page1 = ''
    page2 = ''

phish = Phish()

@app.route('/start', methods=['POST'])
def start():
    json = request.get_json()[0]
    schema = CampaignSchema(strict=True)
    result = schema.load(json)
    print(json['pages'][0]['html'])
    phish.page1 = json['pages'][0]['html']
    return 'hi'


@app.route('/')
def index():
    return phish.page1

