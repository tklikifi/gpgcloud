"""
Handle connection to Amazon S3 cloud storage.
"""

import boto


class AwsError(Exception):
    pass


class Aws(object):

    def __init__(self, access_key, secret_access_key):
        self.access_key = access_key
        self.secret_access_key = secret_access_key


