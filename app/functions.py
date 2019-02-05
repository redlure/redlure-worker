#!/usr/bin/env python3
import os
from string import Template


app_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))


def write_to_disk(campaign):
    # create campaigns folder if it doesnt exist
    if not os.path.isdir(os.path.join(app_dir, 'campaigns')):
        os.mkdir(os.path.join(app_dir, 'campaigns'))
    
    id = str(int(campaign[0]['id']))
    campaign_dir = os.path.join(app_dir, 'campaigns', id)
    
    # create campaign dir
    if not os.path.isdir(campaign_dir):
        os.mkdir(campaign_dir)

    # create basic app folder structure
    if not os.path.isdir(os.path.join(campaign_dir, 'app')):
        os.mkdir(os.path.join(campaign_dir, 'app'))
    if not os.path.isdir(os.path.join(campaign_dir, 'app', 'templates')):
        os.mkdir(os.path.join(campaign_dir, 'app', 'templates'))

     # create campaigns/<id>/app.py
    with open(os.path.join(campaign_dir, 'app.py'), 'w') as f:
        f.write('#!/usr/bin/env python3\nfrom app import app')

    # create campaigns/<id>/app/__init__.py
    with open(os.path.join(campaign_dir, 'app', '__init__.py'), 'w') as f:
        tmp = open(os.path.join(app_dir, 'templates', '__init__.txt')).read()
        f.write(tmp)

    # create campaigns/<id>/app/routes.py
    routes_template = Template(open(os.path.join(app_dir, 'templates', 'routes.txt')).read())

    values = {'url1': '', 'url2': '', 'url3': '','url4': '', 'url5': '', 'redirect_url': ''}
    values['url1'] = '/google'

    with open(os.path.join(campaign_dir, 'app', 'routes.py'), 'w') as f:
        f.write(routes_template.substitute(values))

    # create templates in campaigns/<id>/templates
    for idx, page in enumerate(campaign[0]['pages']):
        template_name = '%d.html' % (idx + 1)
        with open(os.path.join(campaign_dir, 'app', 'templates', template_name), 'w') as f:
            f.write(page['html'])



    

    