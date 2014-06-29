"""
Handle connection to Amazon S3 cloud provider.
"""

import boto
import boto.exception
import boto.s3.key

from cloud import Provider


class S3Error(Exception):
    pass


class S3(Provider):
    """
    Class for Amazon S3 cloud provider.
    """
    def _create_bucket(self, bucket_name):
        """
        Create bucket, if it does not exist.
        """
        bucket = self.connection.lookup(bucket_name.lower())
        if bucket is None:
            bucket = self.connection.create_bucket(bucket_name.lower())
        return bucket

    def __init__(self, config, bucket_name, encryption_method="gpg"):
        """
        Initialize Amazon S3 cloud provider.
        """
        super(S3, self).__init__(config, bucket_name, encryption_method)
        self.config.check(
            "amazon-s3",
            ["access_key", "secret_access_key", ])
        self.access_key = self.config.config.get("amazon-s3", "access_key")
        self.secret_access_key = self.config.config.get(
            "amazon-s3", "secret_access_key")
        self.connection = None

    @property
    def __name__(self):
        """
        Amazon S3 cloud provider name as a simple string.
        """
        return "amazon-s3-bucket:" + self.bucket_name

    def connect(self):
        """
        Connect to Amazon S3 and create buckets.
        """
        if self.connection is not None:
            return self
        self.connection = boto.connect_s3(
            self.access_key, self.secret_access_key)
        self.bucket = self._create_bucket(
            self.access_key + '-' + self.bucket_name)
        return self

    def disconnect(self):
        """
        Disconnect from Amazon S3.
        """
        self.connection = None

    def store(self, key, data):
        """
        Store data to Amazon S3 cloud from data buffer.
        """
        assert(self.connection is not None)
        k = boto.s3.key.Key(self.bucket)
        k.key = key
        k.set_contents_from_string(data)

    def store_from_filename(self, key, filename):
        """
        Store data to Amazon S3 cloud from file.
        """
        assert(self.connection is not None)
        k = boto.s3.key.Key(self.bucket)
        k.key = key
        k.set_contents_from_filename(filename)

    def retrieve(self, key):
        """
        Retrieve data from Amazon S3 cloud. Return data as string.
        """
        assert(self.connection is not None)
        data = None
        k = self.bucket.get_key(key)
        if k: data = k.get_contents_as_string()
        return data

    def retrieve_to_filename(self, key, filename):
        """
        Retrieve data from Amazon S3 cloud. Write data to file.
        """
        assert(self.connection is not None)
        k = self.bucket.get_key(key)
        if k: k.get_contents_to_filename(filename)

    def delete(self, key):
        """
        Delete data from Amazon S3 cloud.
        """
        assert(self.connection is not None)
        k = self.bucket.get_key(key)
        if k: k.delete()

    def list(self):
        """
        List data in Amazon S3 cloud. Return dictionary of keys with
        data.
        """
        assert(self.connection is not None)
        keys = dict()
        for key in self.bucket.list():
            k = self.bucket.get_key(key.name)
            if k: keys[key.name] = k.get_contents_as_string()
        return keys

    def list_keys(self):
        """
        List data keys in Amazon S3 cloud.
        """
        assert(self.connection is not None)
        keys = dict()
        for key in self.bucket.list():
            k = self.bucket.lookup(key.name)
            if k: keys[key.name] = k.__dict__
        return keys
