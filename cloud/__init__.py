"""
Handle data encryption and decryption while transferring the file to and
from the cloud.
"""

import errno
import gnupg
import json
import os

from utils import checksum_data


METADATA_VERSION = 1
gpg = gnupg.GPG(use_agent=True)


class Cloud(object):
    """
    Basic class for cloud access.
    """
    def __init__(self, config, provider, database):
        self.config = config
        self.provider = provider
        self.database = database

    def _create_metadata(self, key, filename=None, size=0, stat_info=None,
                         checksum=None, encrypted_size=0,
                         encrypted_checksum=None):
        metadata = dict(
            metadata_version=METADATA_VERSION,
            provider=self.provider.__name__, key=key, name=None, path=None,
            size=size, mode=0, uid=0, gid=0, atime=0, mtime=0, ctime=0,
            checksum=None, encrypted_size=encrypted_size,
            encrypted_checksum=None)
        if filename is not None:
            metadata["name"] = os.path.basename(filename)
            metadata["path"] = filename
        if stat_info is not None:
            metadata["mode"] = stat_info.st_mode
            metadata["uid"] = stat_info.st_uid
            metadata["gid"] = stat_info.st_gid
            metadata["atime"] = stat_info.st_atime
            metadata["ctime"] = stat_info.st_ctime
            metadata["mtime"] = stat_info.st_mtime
        if checksum is not None:
            metadata["checksum"] = checksum
        if encrypted_checksum is not None:
            metadata["encrypted_checksum"] = encrypted_checksum
        return metadata

    def sync(self):
        """
        Sync metadata database from cloud.
        """
        self.database.drop()
        for key, encrypted_metadata in self.provider.list_metadata().items():
            metadata_str = gpg.decrypt(encrypted_metadata)
            assert(metadata_str.data)
            metadata = json.loads(metadata_str.data)
            assert("metadata_version" in metadata)
            assert(metadata["metadata_version"] == METADATA_VERSION)
            self.database.update(metadata)

    def list(self):
        """
        List metadata from database.
        """
        metadata = list()
        for m in self.database.list():
            metadata.append(m)

        return metadata

    def store(self, data, filename, stat_info=None):
        """
        Encrypt file data and metadata and store them to cloud.
        """
        key = checksum_data(data + filename)
        checksum = checksum_data(data)
        recipients = self.config.config.get("gnupg", "recipients").split(",")
        signer = self.config.config.get("gnupg", "signer")
        encrypted_data = gpg.encrypt(data, recipients, sign=signer)
        metadata = self._create_metadata(
            key, filename=filename, size=len(data), stat_info=stat_info,
            checksum=checksum, encrypted_size=len(encrypted_data.data),
            encrypted_checksum=checksum_data(encrypted_data.data))
        encrypted_metadata = gpg.encrypt(
            json.dumps(metadata), recipients, sign=signer)
        self.provider.store_metadata(key, encrypted_metadata.data)
        self.provider.store(checksum, encrypted_data.data)
        self.database.update(metadata)
        return metadata

    def store_from_filename(self, filename, cloud_filename=None):
        """
        Encrypt file data and store it to cloud.
        """
        if cloud_filename is None:
            cloud_filename = filename
        data = file(filename, "rb").read()
        return self.store(data, cloud_filename, os.stat(filename))

    def retrieve(self, metadata):
        """
        Retrieve data from cloud and decrypt it.
        """
        encrypted_data = self.provider.retrieve(metadata["checksum"])
        encrypted_checksum = checksum_data(encrypted_data)
        data = gpg.decrypt(encrypted_data)
        checksum = checksum_data(data.data)
        assert(encrypted_checksum == metadata['encrypted_checksum'])
        assert(checksum == metadata['checksum'])
        return data.data

    def retrieve_to_filename(self, metadata, filename=None):
        """
        Retrieve data from cloud and decrypt it.
        """
        data = self.retrieve(metadata)
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

    def delete(self, metadata):
        """
        Delete data from cloud.
        """
        self.provider.delete(metadata["checksum"])
        self.provider.delete_metadata(metadata["key"])
        self.database.delete(metadata["key"])
