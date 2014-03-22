"""
Handle data encryption and decryption while transferring the file to and
from the cloud.
"""

import errno
import gnupg
import json
import os
import tempfile

from utils import checksum_data, checksum_file


METADATA_VERSION = 1
gpg = gnupg.GPG(use_agent=True)


class GPGError(Exception):
    """
    Exception raised if GPG encryption or decryption fails.
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return "gpg: " + self.value.status


class MetadataError(Exception):
    """
    Exception raised for metadata errors.
    """
    def __init__(self, key, message):
        self.key = key
        self.message = message

    def __str__(self):
        return self.message


class DataError(MetadataError):
    """
    Exception raised for data errors.
    """
    pass


class Cloud(object):
    """
    Basic class for cloud access.
    """
    def __init__(self, config, provider, database):
        self.config = config
        self.provider = provider
        self.database = database
        self.recipients = self.config.config.get(
            "gnupg", "recipients").split(",")
        self.signer = self.config.config.get("gnupg", "signer")

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
            metadata = gpg.decrypt(encrypted_metadata)
            if not metadata.ok:
                raise GPGError(metadata)
            if not metadata.data:
                raise MetadataError(key, "No metadata")
            try:
                metadata = json.loads(metadata.data)
            except ValueError as e:
                raise MetadataError(key, "Invalid metadata: {0}".format(e))
            if "metadata_version" not in metadata:
                raise MetadataError(key, "No metadata version available")
            if metadata["metadata_version"] != METADATA_VERSION:
                raise MetadataError(
                    key, "Wrong metadata version: {0} != {1}".format(
                        metadata["metadata_version"], METADATA_VERSION))
            self.database.update(metadata)

    def list(self):
        """
        List metadata from database.
        """
        metadata = list()
        for m in self.database.list():
            metadata.append(m)

        return metadata

    def store(self, data, cloud_filename, stat_info=None):
        """
        Encrypt data and store it to cloud.
        """
        # Create encrypted data.
        key = checksum_data(data + cloud_filename)
        checksum = checksum_data(data)
        encrypted_data = gpg.encrypt(data, self.recipients, sign=self.signer)
        if not encrypted_data.ok:
            raise GPGError(encrypted_data)
        encrypted_checksum = checksum_data(encrypted_data.data)

        # Create encrypted metadata.
        metadata = self._create_metadata(
            key, filename=cloud_filename, size=len(data), stat_info=stat_info,
            checksum=checksum, encrypted_size=len(encrypted_data.data),
            encrypted_checksum=encrypted_checksum)
        encrypted_metadata = gpg.encrypt(
            json.dumps(metadata), self.recipients, sign=self.signer)
        if not encrypted_metadata.ok:
            raise GPGError(encrypted_metadata)

        # Store metadata and data to cloud and update database.
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

        # Create encrypted data file.
        stat_info = os.stat(filename)
        encrypted_file = tempfile.NamedTemporaryFile()
        key = checksum_file(filename, extra_data=cloud_filename)
        checksum = checksum_file(filename)
        encrypted_data = gpg.encrypt_file(
            file(filename), self.recipients, sign=self.signer,
            output=encrypted_file.name)
        if not encrypted_data.ok:
            raise GPGError(encrypted_data)
        encrypted_stat_info = os.stat(encrypted_file.name)
        encrypted_checksum = checksum_file(encrypted_file.name)

        # Create encrypted metadata.
        metadata = self._create_metadata(
            key, filename=cloud_filename, size=stat_info.st_size,
            stat_info=stat_info, checksum=checksum,
            encrypted_size=encrypted_stat_info.st_size,
            encrypted_checksum=encrypted_checksum)
        encrypted_metadata = gpg.encrypt(
            json.dumps(metadata), self.recipients, sign=self.signer)
        if not encrypted_metadata.ok:
            raise GPGError(encrypted_metadata)

        # Store metadata and data to cloud and update database.
        self.provider.store_metadata(key, encrypted_metadata.data)
        self.provider.store_from_filename(checksum, encrypted_file.name)
        self.database.update(metadata)

        encrypted_file.close()

        return metadata

    def retrieve(self, metadata):
        """
        Retrieve data from cloud and decrypt it.
        """
        # Get data from cloud.
        encrypted_data = self.provider.retrieve(metadata["checksum"])
        encrypted_checksum = checksum_data(encrypted_data)
        if encrypted_checksum != metadata['encrypted_checksum']:
            raise DataError(
                metadata["checksum"],
                "Wrong encrypted data checksum: {0} != {1}".format(
                    encrypted_checksum, metadata["encrypted_checksum"]))

        # Decrypt data.
        data = gpg.decrypt(encrypted_data)
        if not data.ok:
            raise GPGError(data)
        checksum = checksum_data(data.data)
        if checksum != metadata['checksum']:
            raise DataError(
                metadata["checksum"],
                "Wrong data checksum: {0} != {1}".format(
                    checksum, metadata["checksum"]))
        return data.data

    def retrieve_to_filename(self, metadata, filename=None):
        """
        Retrieve data from cloud and decrypt it.
        """
        if filename is None:
            filename = metadata["path"]

        directory_name = os.path.dirname(filename)
        if directory_name:
            try:
                os.makedirs(directory_name)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

        # Get data from cloud and store it to a temporary file.
        encrypted_file = tempfile.NamedTemporaryFile()
        self.provider.retrieve_to_filename(
            metadata["checksum"], encrypted_file.name)
        encrypted_checksum = checksum_file(encrypted_file.name)
        if encrypted_checksum != metadata['encrypted_checksum']:
            raise DataError(
                metadata["checksum"],
                "Wrong encrypted data checksum: {0} != {1}".format(
                    encrypted_checksum, metadata["encrypted_checksum"]))

        # Decrypt the data in temporary file and store it to given filename.
        data = gpg.decrypt_file(
            file(encrypted_file.name), output=filename)
        if not data.ok:
            raise GPGError(data)
        checksum = checksum_file(filename)
        if checksum != metadata['checksum']:
            raise DataError(
                metadata["checksum"],
                "Wrong data checksum: {0} != {1}".format(
                    checksum, metadata["checksum"]))

        # Set file attributes.
        os.chmod(filename, metadata["mode"])
        os.utime(filename, (metadata["atime"], metadata["mtime"]))

        encrypted_file.close()

    def delete(self, metadata):
        """
        Delete data from cloud.
        """
        self.provider.delete(metadata["checksum"])
        self.provider.delete_metadata(metadata["key"])
        self.database.delete(metadata["key"])
