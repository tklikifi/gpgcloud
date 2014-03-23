"""
Handle connection to Amazon S3 cloud storage.
"""

import boto
import boto.exception
import boto.s3.key

from cloud import Provider


class AwsError(Exception):
    pass


class Aws(Provider):
    """
    Class for Amazon S3 cloud provider.
    """
    def _create_bucket(self, bucket_name):
        """
        Create bucket, if it does not exist.
        """
        bucket = self.conn.lookup(bucket_name.lower())
        if bucket is None:
            bucket = self.conn.create_bucket(bucket_name.lower())
        return bucket

    def __init__(self, config):
        """
        Initialize Amazon S3 cloud provider.
        """
        super(Aws, self).__init__(config)
        self.access_key = self.config.config.get("aws", "access_key")
        self.secret_access_key = self.config.config.get(
            "aws", "secret_access_key")
        self.conn = None

    def connect(self):
        """
        Connect to Amazon S3 and create buckets.

        """
        if self.conn is not None:
            return self
        self.conn = boto.connect_s3(self.access_key, self.secret_access_key)
        self.data_bucket = self._create_bucket(
            self.access_key + '-' + self.config.config.get(
                "aws", "data_bucket"))
        self.metadata_bucket = self._create_bucket(
            self.access_key + '-' + self.config.config.get(
                "aws", "metadata_bucket"))
        return self

    @property
    def __name__(self):
        """
        Amazon S3 cloud provider name as a simple string.
        """
        return "AmazonS3"

    def store_metadata(self, key, metadata):
        """
        Store metadata to Amazon S3 cloud.
        """
        assert(self.conn is not None)
        m = boto.s3.key.Key(self.metadata_bucket)
        m.key = key
        m.set_contents_from_string(metadata)

    def store(self, key, data):
        """
        Store data to Amazon S3 cloud from data buffer.
        """
        assert(self.conn is not None)
        k = boto.s3.key.Key(self.data_bucket)
        k.key = key
        k.set_contents_from_string(data)

    def store_from_filename(self, key, filename):
        """
        Store data to Amazon S3 cloud from file.
        """
        assert(self.conn is not None)
        k = boto.s3.key.Key(self.data_bucket)
        k.key = key
        k.set_contents_from_filename(filename)

    def retrieve_metadata(self, key):
        """
        Retrieve metadata from Amazon S3 cloud.
        """
        assert(self.conn is not None)
        metadata = None
        m = self.metadata_bucket.get_key(key)
        if m: metadata = m.get_contents_as_string()
        return metadata

    def retrieve(self, key):
        """
        Retrieve data from Amazon S3 cloud. Return data as string.
        """
        assert(self.conn is not None)
        data = None
        k = self.data_bucket.get_key(key)
        if k: data = k.get_contents_as_string()
        return data

    def retrieve_to_filename(self, key, filename):
        """
        Retrieve data from Amazon S3 cloud. Write data to file.
        """
        assert(self.conn is not None)
        k = self.data_bucket.get_key(key)
        if k: k.get_contents_to_filename(filename)

    def delete_metadata(self, key):
        """
        Delete metadata from Amazon S3 cloud.
        """
        assert(self.conn is not None)
        m = self.metadata_bucket.get_key(key)
        if m: m.delete()

    def delete(self, key):
        """
        Delete data from Amazon S3 cloud.
        """
        assert(self.conn is not None)
        k = self.data_bucket.get_key(key)
        if k: k.delete()

    def list_metadata(self):
        """
        List metadata in Amazon S3 cloud. Return dictionary of keys with
        metadata.
        """
        assert(self.conn is not None)
        keys = dict()
        for key in self.metadata_bucket.list():
            m = self.metadata_bucket.get_key(key.name)
            if m: keys[key.name] = m.get_contents_as_string()
        return keys

    def list_metadata_keys(self):
        """
        List metadata keys in Amazon S3 cloud.
        """
        assert(self.conn is not None)
        keys = dict()
        for key in self.metadata_bucket.list():
            k = self.metadata_bucket.lookup(key.name)
            if k: keys[key.name] = k.__dict__
        return keys

    def list(self):
        """
        List data in Amazon S3 cloud. Return dictionary of keys with
        data.
        """
        assert(self.conn is not None)
        keys = dict()
        for key in self.data_bucket.list():
            k = self.data_bucket.get_key(key.name)
            if k: keys[key.name] = k.get_contents_as_string()
        return keys

    def list_keys(self):
        """
        List data keys in Amazon S3 cloud.
        """
        assert(self.conn is not None)
        keys = dict()
        for key in self.data_bucket.list():
            k = self.data_bucket.lookup(key.name)
            if k: keys[key.name] = k.__dict__
        return keys
