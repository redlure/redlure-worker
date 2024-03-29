#!/usr/bin/env python3
from marshmallow import Schema, fields
from app import app
import string
import random
from datetime import datetime
import os
import subprocess
import shutil
from binascii import hexlify
import requests

WORKER_VERSION = '0.11'

class WorkspaceSchema(Schema):
    id = fields.Number()
    name = fields.Str()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class ProfileSchema(Schema):
    id = fields.Number()
    name = fields.Str()
    from_address = fields.Str()
    smtp_host = fields.Str()
    smtp_port = fields.Number()
    username = fields.Str()
    password = fields.Str()
    tls = fields.Boolean()
    ssl = fields.Boolean()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class PersonSchema(Schema):
    id = fields.Number()
    first_name = fields.Str()
    last_name = fields.Str()
    email = fields.Str()


class ListSchema(Schema):
    id = fields.Number()
    name = fields.Str()
    targets = fields.Nested(PersonSchema, many=True, strict=True)
    workspace_id = fields.Number()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class EmailSchema(Schema):
    id = fields.Number()
    name = fields.Str()
    subject = fields.Str()
    html = fields.Str()
    track = fields.Boolean()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class PageSchema(Schema):
    id = fields.Number()
    name = fields.Str()
    html = fields.Str()
    url = fields.Str()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class DomainSchema(Schema):
    id = fields.Number()
    domain = fields.Str()
    ip = fields.Str()
    cert_path = fields.Str(allow_none=True)
    key_path = fields.Str(allow_none=True)


class ResultSchema(Schema):
    campaign_id = fields.Number()
    person_id = fields.Nested(PersonSchema, strict=True)
    tracker = fields.Str()
    status = fields.Str()


class ServerSchema(Schema):
    id = fields.Number()
    ip = fields.Str()
    alias = fields.Str()
    port = fields.Number()
    status = fields.Str()


class CampaignpagesSchema(Schema):
    index = fields.Number()
    page = fields.Nested(PageSchema, strict=True)


class CampaignSchema(Schema):
    id = fields.Number()
    name = fields.Str()
    pages = fields.Nested(CampaignpagesSchema, strict=True, many=True)
    redirect_url = fields.Str(allow_none=True)
    safety_url = fields.Str(allow_none=True)
    domain = fields.Nested(DomainSchema, strict=True)
    server = fields.Nested(ServerSchema, strict=True)
    port = fields.Number()
    ssl = fields.Boolean()
    payload_url = fields.Str(allow_none=True)
    payload_file = fields.Str(allow_none=True)
