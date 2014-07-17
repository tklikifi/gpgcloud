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
def encrypt_data(base64_data, encryption_key):
    """
    Encrypt data with the given encryption key.
    """
    data = base64.decodestring(base64_data)
    plaintext_fp = StringIO(data)
    encrypted_fp = StringIO()
    checksum, _= encryption.encrypt(
        plaintext_fp, encrypted_fp, encryption_key)
    encrypted_fp.seek(0)
    encrypted_data = encrypted_fp.read()
    # Encrypted data is BASE64 encoded string. Checksum for the encrypted
    # data is always calculated over BASE64 encoded data which is stored
    # into the cloud.
    base64_encrypted_data = base64.encodestring(encrypted_data)
    encrypted_checksum = checksum_data(base64_encrypted_data)
    return {"checksum": checksum,
            "encrypted_data": base64_encrypted_data,
            "encrypted_checksum": encrypted_checksum, }


class Encrypt(Resource):
    """
    API for encrypting data.
    """
    def post(self):
        args = parser.parse_args()
        base64_data = args.get('data', None)
        encryption_key = args.get('key', None)
        if not encryption_key:
            abort(409, message="No encryption key")
        if not base64_data:
            abort(409, message="No data")
        try:
            res = encrypt_data.delay(base64_data, encryption_key)
            res.wait()
            return res.get(), 201
        except Exception as e:
            abort(409, message="Encryption failed: {0}".format(str(e)))


@celery.task()
def decrypt_data(base64_encrypted_data, encryption_key):
    """
    Decrypt encrypted data with the given encryption key.

    Encrypted data is BASE64 encoded string. Checksum for the encrypted
    data is always calculated over BASE64 encoded data which is stored
    into the cloud. Return decrypted data as BASE64 encoded string.
    """
    encrypted_checksum = checksum_data(base64_encrypted_data)
    encrypted_data = base64.decodestring(base64_encrypted_data)
    encrypted_fp = StringIO(encrypted_data)
    plaintext_fp = StringIO()
    _, checksum = encryption.decrypt(
        encrypted_fp, plaintext_fp, encryption_key)
    plaintext_fp.seek(0)
    data = plaintext_fp.read()
    base64_data = base64.encodestring(data)
    return {"encrypted_checksum": encrypted_checksum,
            "data": base64_data,
            "checksum": checksum, }


class Decrypt(Resource):
    """
    API for decrypting data.
    """
    def post(self):
        args = parser.parse_args()
        encryption_key = args.get('key', None)
        if not encryption_key:
            abort(409, message="No encryption key")
        base64_encrypted_data = args.get('data', None)
        if not base64_encrypted_data:
            abort(409, message="No encrypted data")
        try:
            res = decrypt_data.delay(base64_encrypted_data, encryption_key)
            res.wait()
            return res.get(), 201
        except Exception as e:
            abort(409, message="Decryption failed: {0}".format(str(e)))


API_URL = '/api/v1'

api.add_resource(Encrypt, API_URL + '/encrypt')
api.add_resource(Decrypt, API_URL + '/decrypt')


if __name__ == "__main__":
    app.run(port=8000, debug=True)
