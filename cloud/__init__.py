"""
Handle data encryption and decryption while transferring the file to and
from the cloud.
"""

import dataset
import errno
import gnupg
import json
import os

from config import ConfigError
from utils import checksum_data


METADATA_VERSION = 1
gpg = gnupg.GPG(use_agent=True)


class Cloud(object):
    """
    Basic class for cloud access.
    """
    def __init__(self, config, cloud):
        self.config = config
        self.cloud = cloud

        # Initialize internal file database if it is configured.
        try:
            self._db = dataset.connect(
                'sqlite:///' + config.config.get("general", "database"))
            self._file_table = self._db["files"]
        except ConfigError:
            self._file_table = None

    def _create_metadata(self, key, filename=None, size=0, stat_info=None,
                         checksum=None, encrypted_size=0,
                         encrypted_checksum=None):
        metadata = dict(
            metadata_version=METADATA_VERSION, key=key, path="UNKNOWN",
            size=size, mode=0, uid=0, gid=0, atime=0, mtime=0, ctime=0,
            checksum=None, encrypted_size=encrypted_size,
            encrypted_checksum=None)
        if filename is not None:
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

    def _file_db_drop_table(self):
        """
        Drop file database.
        """
        if self._file_table is not None:
            self._file_table.drop()
            self._file_table = self._db["files"]

    def _file_db_update_entry(self, metadata):
        """
        Update file database with new or existing metadata.
        """
        if self._file_table is not None:
            self._file_table.upsert(metadata, ["name", "key"])

    def _file_db_delete_entry(self, key):
        """
        Delete key from file database.
        """
        if self._file_table is not None:
            self._file_table.delete(key=key)

    def list(self, sync_file_db=False):
        """
        List keys from cloud and decrypt metadata.
        """
        keys = list()

        if self._file_table is None or sync_file_db:
            # If database is not used or we need to sync the database,
            # read metadata from cloud.
            self._file_db_drop_table()
            for key, encrypted_metadata in self.cloud.list().items():
                metadata_str = gpg.decrypt(encrypted_metadata)
                if metadata_str.data:
                    metadata = json.loads(metadata_str.data)
                    if "metadata_version" not in metadata:
                        raise ValueError("File metadata is invalid")
                    assert(metadata["metadata_version"] == METADATA_VERSION)
                else:
                    metadata = self._create_metadata(key)
                self._file_db_update_entry(metadata)
                keys.append(metadata)
        else:
            # Read metadata from database.
            for metadata in self._file_table.all():
                keys.append(metadata)

        return keys

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
        self.cloud.store(key, encrypted_data.data, encrypted_metadata.data)
        self._file_db_update_entry(metadata)
        return key

    def store_from_filename(self, filename, cloud_filename=None):
        """
        Encrypt file data and store it to cloud.
        """
        if cloud_filename is None:
            cloud_filename = filename
        data = file(filename, "rb").read()
        return self.store(data, cloud_filename, os.stat(filename))

    def retrieve(self, key):
        """
        Retrieve data from cloud and decrypt it.
        """
        encrypted_data, encrypted_metadata = self.cloud.retrieve(key)
        encrypted_checksum = checksum_data(encrypted_data)
        data = gpg.decrypt(encrypted_data)
        checksum = checksum_data(data.data)
        metadata = gpg.decrypt(encrypted_metadata)
        if metadata.data:
            metadata = json.loads(metadata.data)
            if "metadata_version" not in metadata:
                raise ValueError("File metadata is invalid")
            assert(metadata["metadata_version"] == METADATA_VERSION)
            assert(encrypted_checksum == metadata['encrypted_checksum'])
            assert(checksum == metadata['checksum'])
            self._file_db_update_entry(metadata)
        else:
            metadata = None
        return data.data, metadata

    def retrieve_to_filename(self, key, filename=None):
        """
        Retrieve data from cloud and decrypt it.
        """
        data, metadata = self.retrieve(key)
        if filename is None:
            if metadata is None:
                filename = "UNKNOWN"
            else:
                filename = metadata["path"]
        directory_name = os.path.dirname(filename)
        if directory_name:
            try:
                os.makedirs(directory_name)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
        file(filename, "wb").write(data)
        if metadata is not None:
            os.chmod(filename, metadata["mode"])
            os.utime(filename, (metadata["atime"], metadata["mtime"]))
        return metadata

    def delete(self, key):
        """
        Delete data from cloud.
        """
        self.cloud.delete(key)
        self._file_db_delete_entry(key)
