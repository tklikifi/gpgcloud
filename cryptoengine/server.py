"""
Main server application for crypto engine.
"""

import base64
from celery import Celery
from flask import Flask
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


@celery.task()
def encrypt(data, encryption_key):
    """
    Encrypt data with the given encryption key.
    """
    plaintext_fp = StringIO(data)
    encrypted_fp = StringIO()
    encryption.encrypt(plaintext_fp, encrypted_fp, encryption_key)
    encrypted_fp.seek(0)
    encrypted_data = encrypted_fp.read()
    base64_data = base64.encodestring(encrypted_data)
    base64_size = len(base64_data)
    encrypted_checksum = checksum_data(base64_data)
    return (encryption_key, base64_data, base64_size, encrypted_checksum)


@celery.task()
def decrypt(encrypted_data, encryption_key):
    """
    Decrypt encrypted data with the given encryption key.
    """
    encrypted_fp = StringIO(base64.decodestring(encrypted_data))
    plaintext_fp = StringIO()
    _, checksum = encryption.decrypt(
        encrypted_fp, plaintext_fp, encryption_key)
    plaintext_fp.seek(0)
    data = plaintext_fp.read()
    return data, checksum


@app.route("/")
def hello():
    return "Hello World!"


if __name__ == "__main__":
    app.run()
