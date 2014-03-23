"""
Handle connection to SFTP filesystem.
"""

import errno
import paramiko
import paramiko.pkey
import time

from cloud import Provider


class SftpError(Exception):
    pass


class Sftp(Provider):
    """
    Class for SFTP filesystem provider.
    """
    def _create_bucket(self, bucket_name):
        """
        Create bucket, if it does not exist.
        """
        assert(self.connection is not None)
        try:
            self.connection.stat(bucket_name)
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise
        try:
            self.connection.mkdir(bucket_name)
        except IOError as e:
            if e.errno == errno.EEXIST:
                pass
        return bucket_name

    def __init__(self, config):
        """
        Initialize SFTP filesystem provider.
        """
        super(Sftp, self).__init__(config)
        self.config.check(
            "sftp",
            ["host", "port", "username", "identity_file", "data_bucket",
             "metadata_bucket"])
        self.host = self.config.config.get(
            "sftp", "host")
        self.port = self.config.config.get(
            "sftp", "port")
        self.username = self.config.config.get(
            "sftp", "username")
        self.identity_file = self.config.config.get(
            "sftp", "identity_file")
        self.connection = None

    @property
    def __name__(self):
        """
        SFTP filesystem provider name as a simple string.
        """
        return "sftp"

    def connect(self):
        """
        Connect to host and create buckets.
        """
        if self.connection is not None:
            return self
        pkey = paramiko.RSAKey.from_private_key_file(self.identity_file)
        self.transport = paramiko.Transport((self.host, int(self.port)))
        self.transport.connect(username=self.username, pkey=pkey)
        self.connection = paramiko.SFTPClient.from_transport(self.transport)
        self.data_bucket = self._create_bucket(
            self.config.config.get("sftp", "data_bucket"))
        self.metadata_bucket = self._create_bucket(
            self.config.config.get("sftp", "metadata_bucket"))
        return self

    def disconnect(self):
        """
        Disconnect from host.
        """
        if self.connection is None:
            return
        self.connection.close()
        self.transport.close()

    def store_metadata(self, key, metadata):
        """
        Store metadata to SFTP filesystem.
        """
        assert(self.connection is not None)
        metadata_file = self.connection.file(
            self.metadata_bucket + "/" + key, "w")
        metadata_file.write(metadata)
        metadata_file.close()

    def store(self, key, data):
        """
        Store data to SFTP filesystem.
        """
        assert(self.connection is not None)
        data_file = self.connection.file(self.data_bucket + "/" + key, "w")
        data_file.write(data)
        data_file.close()

    def store_from_filename(self, key, filename):
        """
        Store file to SFTP filesystem.
        """
        assert(self.connection is not None)
        self.connection.put(filename, self.data_bucket + "/" + key)

    def retrieve_metadata(self, key):
        """
        Retrieve metadata from SFTP filesystem.
        """
        assert(self.connection is not None)
        metadata_file = self.connection.file(self.metadata_bucket + "/" + key)
        metadata = metadata_file.read()
        metadata_file.close()
        return metadata

    def retrieve(self, key):
        """
        Retrieve data from SFTP filesystem.
        """
        assert(self.connection is not None)
        data_file = self.connection.file(self.data_bucket + "/" + key)
        data = data_file.read()
        data_file.close()
        return data

    def retrieve_to_filename(self, key, filename):
        """
        Retrieve data from SFTP filesystem.
        """
        assert(self.connection is not None)
        self.connection.get(self.data_bucket + "/" + key, filename)

    def delete_metadata(self, key):
        """
        Delete metadata from SFTP filesystem.
        """
        assert(self.connection is not None)
        self.connection.remove(self.metadata_bucket + "/" + key)

    def delete(self, key):
        """
        Delete data from SFTP filesystem using.
        """
        assert(self.connection is not None)
        self.connection.remove(self.data_bucket + "/" + key)

    def list_metadata(self):
        """
        List metadata in SFTP filesystem. Return dictionary of keys with
        metadata.
        """
        assert(self.connection is not None)
        keys = dict()
        for key in self.connection.listdir(self.metadata_bucket):
            metadata_file = self.connection.file(
                self.metadata_bucket + "/" + key)
            keys[key] = metadata_file.read()
            metadata_file.close()
        return keys

    def list_metadata_keys(self):
        """
        List metadata keys in SFTP filesystem. Return dictionary of keys.
        """
        assert(self.connection is not None)
        keys = dict()
        for key in self.connection.listdir_attr(self.metadata_bucket):
            keys[key.filename] = key.__dict__
            keys[key.filename]["name"] = key.filename
            keys[key.filename]["size"] = key.st_size
            keys[key.filename]["last_modified"] = time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(key.st_mtime))
        return keys

    def list(self):
        """
        List data in SFTP filesystem. Return dictionary of keys with data.
        """
        assert(self.connection is not None)
        keys = dict()
        for key in self.connection.listdir(self.data_bucket):
            data_file = self.connection.file(self.data_bucket + "/" + key)
            keys[key] = data_file.read()
            data_file.close()
        return keys

    def list_keys(self):
        """
        List data keys in SFTP filesystem. Return dictionary of keys.
        """
        assert(self.connection is not None)
        keys = dict()
        for key in self.connection.listdir_attr(self.data_bucket):
            keys[key.filename] = key.__dict__
            keys[key.filename]["name"] = key.filename
            keys[key.filename]["size"] = key.st_size
            keys[key.filename]["last_modified"] = time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(key.st_mtime))
        return keys
