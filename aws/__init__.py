"""
Handle connection to Amazon S3 cloud storage.
"""

import boto
import boto.exception
import boto.s3.key

from utils import checksum_data, checksum_file


class Aws(object):
    """
    Class for Amazon S3 cloud storage.
    """
    def __init__(self, access_key, secret_access_key, bucket):
        """
        Initialize Amazon S3 connection and create bucket, if it does not
        exist.
        """
        self.access_key = access_key
        self.secret_access_key = secret_access_key
        bucket_name = (access_key + '-' + bucket).lower()
        self.conn = boto.connect_s3(self.access_key, self.secret_access_key)
        self.bucket = self.conn.lookup(bucket_name)
        if self.bucket is None:
            self.bucket = self.conn.create_bucket(bucket_name)

    def store(self, data, metadata):
        """
        Store data to Amazon S3 cloud from data buffer.
        """
        key = checksum_data(data)
        k = boto.s3.key.Key(self.bucket)
        k.key = key
        k.set_metadata('metadata', metadata)
        k.set_contents_from_string(data)
        return key

    def store_from_filename(self, filename, metadata):
        """
        Store data to Amazon S3 cloud from data buffer.
        """
        key = checksum_file(filename)
        k = boto.s3.key.Key(self.bucket)
        k.key = key
        k.set_metadata('metadata', metadata)
        k.set_contents_from_filename(filename)
        return key

    def retrieve(self, key):
        """
        Retrieve data from Amazon S3 cloud. Return data and metadata as
        strings.
        """
        k = self.bucket.get_key(key)
        data = k.get_contents_as_string()
        metadata = k.get_metadata('metadata')
        return data, metadata

    def retrieve_to_filename(self, key, filename):
        """
        Retrieve data from Amazon S3 cloud. Write data to file, return
        metadata as string.
        """
        k = self.bucket.get_key(key)
        k.get_contents_to_filename(filename)
        metadata = k.get_metadata('metadata')
        return metadata

    def delete(self, key):
        """
        Delete data from Amazon S3 cloud.
        """
        k = self.bucket.get_key(key)
        k.delete()

    def list(self):
        """
        List data in Amazon S3 cloud. Return dictionary of keys with
        metadata.
        """
        keys = dict()

        for key in self.bucket.list():
            k = self.bucket.get_key(key.name)
            keys[key.name] = k.get_metadata('metadata')

        return keys
