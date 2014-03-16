"""
Handle connection to Amazon S3 cloud storage.
"""

import boto
import boto.exception
import boto.s3.key


class AwsError(Exception):
    pass


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

    def store_data(self, key, data, metadata):
        """
        Store data to Amazon S3 cloud from data buffer.
        """
        k = boto.s3.key.Key(self.bucket)
        k.key = key
        k.set_contents_from_string(data)
        m = boto.s3.key.Key(self.bucket)
        m.key = key + "-metadata"
        m.set_contents_from_string(metadata)

    def store_file(self, key, filename, metadata):
        """
        Store data to Amazon S3 cloud from file.
        """
        k = boto.s3.key.Key(self.bucket)
        k.key = key
        k.set_contents_from_filename(filename)
        m = boto.s3.key.Key(self.bucket)
        m.key = key + "-metadata"
        m.set_contents_from_string(metadata)

    def retrieve(self, key):
        """
        Retrieve data from Amazon S3 cloud. Return data and metadata as
        strings.
        """
        data = metadata = None
        k = self.bucket.get_key(key)
        if k: data = k.get_contents_as_string()
        m = self.bucket.get_key(key + "-metadata")
        if m: metadata = m.get_contents_as_string()
        return data, metadata

    def retrieve_file(self, key, filename):
        """
        Retrieve data from Amazon S3 cloud. Write data to file, return
        metadata as string.
        """
        metadata = None
        k = self.bucket.get_key(key)
        if k: k.get_contents_to_filename(filename)
        m = self.bucket.get_key(key + "-metadata")
        if m: metadata = m.get_contents_as_string()
        return metadata

    def delete(self, key):
        """
        Delete data from Amazon S3 cloud.
        """
        k = self.bucket.get_key(key)
        if k: k.delete()
        m = self.bucket.get_key(key + "-metadata")
        if m: m.delete()

    def list(self):
        """
        List data in Amazon S3 cloud. Return dictionary of keys with
        metadata.
        """
        keys = dict()

        for key in self.bucket.list():
            m = self.bucket.get_key(key.name + "-metadata")
            if m: keys[key.name] = m.get_contents_as_string()

        return keys
