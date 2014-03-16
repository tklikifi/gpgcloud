"""
Handle data encryption and decryption while transferring the file to and
from the cloud.
"""

import base64
import errno
import gnupg
import json
import os

from aws import Aws
from config import Config
from utils import checksum_data


gpg = gnupg.GPG(use_agent=True)


class AwsData(object):

    def __init__(self, config=None):
        if config is None:
            self.config = Config()
        else:
            self.config = config

        self.aws = Aws(self.config.config.get("aws", "access_key"),
                       self.config.config.get("aws", "secret_access_key"),
                       self.config.config.get("aws", "bucket"))

    def list(self):
        """
        List keys from Amazon S3 cloud and decrypt metadata.
        """
        keys = dict()

        for key, encrypted_metadata in self.aws.list().items():
            metadata_str = str(gpg.decrypt(encrypted_metadata))
            metadata = json.loads(metadata_str)
            keys[key] = metadata

        return keys


    def store(self, data, filename, stat_info=None):
        """
        Encrypt file data and metadata and store them to Amazon S3 cloud.
        """
        checksum = checksum_data(data)
        encoded_data = base64.encodestring(data)
        recipient = self.config.config.get("gnupg", "identity")
        encrypted_data = str(gpg.encrypt(encoded_data, [recipient]))
        metadata = {
            "path": filename,
            "size": len(data),
            "mode": 0 if stat_info is None else stat_info.st_mode,
            "uid": 0 if stat_info is None else stat_info.st_uid,
            "gid": 0 if stat_info is None else stat_info.st_gid,
            "atime": 0 if stat_info is None else stat_info.st_atime,
            "mtime": 0 if stat_info is None else stat_info.st_mtime,
            "ctime": 0 if stat_info is None else stat_info.st_ctime,
            "checksum": checksum,
            "encrypted_size": len(encrypted_data),
            "encrypted_checksum": checksum_data(encrypted_data),
            }
        encrypted_metadata = str(gpg.encrypt(
            json.dumps(metadata), [recipient], symmetric="AES256",
            sign=recipient))
        self.aws.store(checksum, encrypted_data, encrypted_metadata)
        return checksum

    def store_from_filename(self, filename, cloud_filename=None):
        """
        Encrypt file data and store it to Amazon S3 cloud.
        """
        if cloud_filename is None:
            cloud_filename = filename
        data = file(filename, "rb").read()
        return self.store(data, cloud_filename, os.stat(filename))

    def retrieve(self, key):
        """
        Retrieve data from Amazon S3 cloud and decrypt it.
        """
        encrypted_data, encrypted_metadata = self.aws.retrieve(key)
        encrypted_checksum = checksum_data(encrypted_data)
        encoded_data = str(gpg.decrypt(encrypted_data))
        data = base64.decodestring(encoded_data)
        checksum = checksum_data(data)
        metadata_str = str(gpg.decrypt(encrypted_metadata))
        metadata = json.loads(metadata_str)
        assert(encrypted_checksum == metadata['encrypted_checksum'])
        assert(checksum == metadata['checksum'])
        return data, metadata

    def retrieve_to_filename(self, key, filename=None):
        """
        Retrieve data from Amazon S3 cloud and decrypt it.
        """
        data, metadata = self.retrieve(key)
        if filename is None:
            filename = metadata["path"]
        directory_name = os.path.dirname(filename)
        if directory_name:
            try:
                os.makedirs(directory_name)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
        file(filename, "wb").write(data)
        os.chmod(filename, metadata["mode"])
        os.utime(filename, (metadata["atime"], metadata["mtime"]))
        return metadata

    def delete(self, key):
        """
        Delete data from Amazon S3 cloud.
        """
        self.aws.delete(key)
