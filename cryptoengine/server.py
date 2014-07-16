"""
Main server application for crypto engine.
"""

import base64
from celery import Celery
from flask import Flask
from flask.ext.restful import abort, Api, reqparse, Resource
from lib import checksum_data, encryption
from StringIO import StringIO


def make_celery(flask_app):
    """
    Bind Flask application and Celery application.
    """
    celery = Celery('cryptoengine', include=['cryptoengine.server'])
    celery.config_from_object('cryptoengine.celeryconfig')
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery


app = Flask(__name__)
app.config.update(CELERY_BROKER_URL='redis://localhost:6379',
                  CELERY_RESULT_BACKEND='redis://localhost:6379')

celery = make_celery(app)

api = Api(app)

parser = reqparse.RequestParser()
parser.add_argument('data', type=str)
parser.add_argument('key', type=str)


@celery.task()
def encrypt_data(data, encryption_key):
    """
    Encrypt data with the given encryption key.
    """
    plaintext_fp = StringIO(data)
    encrypted_fp = StringIO()
    checksum, _= encryption.encrypt(
        plaintext_fp, encrypted_fp, encryption_key)
    encrypted_fp.seek(0)
    encrypted_data = encrypted_fp.read()
    base64_data = base64.encodestring(encrypted_data)
    encrypted_checksum = checksum_data(base64_data)
    return {"checksum": checksum,
            "encrypted_data": base64_data,
            "encrypted_checksum": encrypted_checksum, }


class Encrypt(Resource):
    """
    API for encrypting data.
    """
    def post(self):
        args = parser.parse_args()
        data = args.get('data', None)
        if not data:
            abort(409, message="No data")
        encryption_key = args.get('key', None)
        if not encryption_key:
            abort(409, message="No encryption key")
        try:
            res = encrypt_data.delay(data, encryption_key)
            res.wait()
            return res.get(), 201
        except Exception as e:
            abort(409, message="Encryption failed: {0}".format(str(e)))


@celery.task()
def decrypt_data(encrypted_data, encryption_key):
    """
    Decrypt encrypted data with the given encryption key.
    """
    encrypted_fp = StringIO(base64.decodestring(encrypted_data))
    plaintext_fp = StringIO()
    encrypted_checksum, checksum = encryption.decrypt(
        encrypted_fp, plaintext_fp, encryption_key)
    plaintext_fp.seek(0)
    data = plaintext_fp.read()
    return {"encrypted_checksum": encrypted_checksum,
            "data": data,
            "checksum": checksum, }


class Decrypt(Resource):
    """
    API for decrypting data.
    """
    def post(self):
        args = parser.parse_args()
        data = args.get('data', None)
        if not data:
            abort(409, message="No encrypted data")
        encryption_key = args.get('key', None)
        if not encryption_key:
            abort(409, message="No encryption key")
        try:
            res = decrypt_data.delay(data, encryption_key)
            res.wait()
            return res.get(), 201
        except Exception as e:
            abort(409, message="Decryption failed: {0}".format(str(e)))


API_URL = '/api/v1'

api.add_resource(Encrypt, API_URL + '/encrypt')
api.add_resource(Decrypt, API_URL + '/decrypt')


if __name__ == "__main__":
    app.run()
