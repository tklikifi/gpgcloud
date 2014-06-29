"""
Handle connection to SFTP filesystem.
"""

import errno
import os
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
        bucket_path = os.path.join(self.remote_directory, bucket_name)
        try:
            self.connection.stat(bucket_path)
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise SftpError(
                    "Could not access bucket directory: '{0}': {1}: "
                    "Check that parent path exists and has proper "
                    "file ownership and permissions".format(
                        bucket_path, str(e)))
            try:
                self.connection.mkdir(bucket_path, mode=0700)
            except IOError as e:
                if e.errno != errno.EEXIST:
                    raise SftpError(
                        "Could not create bucket directory: '{0}': {1}: "
                        "Check that parent path exists and has proper "
                        "file ownership and permissions".format(
                            bucket_path, str(e)))
        return bucket_path

    def __init__(self, config, bucket_name, encryption_method="gpg"):
        """
        Initialize SFTP filesystem provider.
        """
        super(Sftp, self).__init__(config, bucket_name, encryption_method)
        self.config.check(
            "sftp",
            ["host", "port", "username", "identity_file",
             "remote_directory", ])
        self.host = self.config.config.get("sftp", "host")
        self.port = self.config.config.get("sftp", "port")
        self.username = self.config.config.get("sftp", "username")
        self.identity_file = self.config.config.get("sftp", "identity_file")
        self.remote_directory = self.config.config.get(
            "sftp", "remote_directory")
        self.encryption_method = encryption_method
        self.connection = None

    @property
    def __name__(self):
        """
        SFTP filesystem provider name as a simple string.
        """
        return "sftp-bucket:" + self.bucket_name

    def connect(self):
        """
        Connect to host and create buckets.
        """
        if self.connection is not None:
            return self
        try:
            pkey = paramiko.RSAKey.from_private_key_file(self.identity_file)
        except paramiko.SSHException:
            pkey = paramiko.DSSKey.from_private_key_file(self.identity_file)
        self.transport = paramiko.Transport((self.host, int(self.port)))
        self.transport.connect(username=self.username, pkey=pkey)
        self.connection = paramiko.SFTPClient.from_transport(self.transport)
        self.bucket = self._create_bucket(self.bucket_name)
        return self

    def disconnect(self):
        """
        Disconnect from host.
        """
        if self.connection is None:
            return
        self.connection.close()
        self.transport.close()

    def store(self, key, data):
        """
        Store data to SFTP filesystem.
        """
        assert(self.connection is not None)
        data_file = self.connection.file(self.bucket + "/" + key, "w")
        data_file.write(data)
        data_file.close()

    def store_from_filename(self, key, filename):
        """
        Store file to SFTP filesystem.
        """
        assert(self.connection is not None)
        self.connection.put(filename, self.bucket + "/" + key)

    def retrieve(self, key):
        """
        Retrieve data from SFTP filesystem.
        """
        assert(self.connection is not None)
        data_file = self.connection.file(self.bucket + "/" + key)
        data = data_file.read()
        data_file.close()
        return data

    def retrieve_to_filename(self, key, filename):
        """
        Retrieve data from SFTP filesystem.
        """
        assert(self.connection is not None)
        self.connection.get(self.bucket + "/" + key, filename)

    def delete(self, key):
        """
        Delete data from SFTP filesystem using.
        """
        assert(self.connection is not None)
        self.connection.remove(self.bucket + "/" + key)

    def list(self):
        """
        List data in SFTP filesystem. Return dictionary of keys with data.
        """
        assert(self.connection is not None)
        keys = dict()
        for key in self.connection.listdir(self.bucket):
            data_file = self.connection.file(self.bucket + "/" + key)
            keys[key] = data_file.read()
            data_file.close()
        return keys

    def list_keys(self):
        """
        List data keys in SFTP filesystem. Return dictionary of keys.
        """
        assert(self.connection is not None)
        keys = dict()
        for key in self.connection.listdir_attr(self.bucket):
            keys[key.filename] = key.__dict__
            keys[key.filename]["name"] = key.filename
            keys[key.filename]["size"] = key.st_size
            keys[key.filename]["last_modified"] = time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(key.st_mtime))
        return keys
