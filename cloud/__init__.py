"""
Handle data encryption and decryption while transferring the file to and
from the cloud.
"""

import base64
import errno
import gnupg
import json
import os
import tempfile
from StringIO import StringIO

from lib import checksum_data, checksum_file
from lib.encryption import generate_random_password, encrypt, decrypt

from cryptoengine.server import encrypt_data as encrypt_task
from cryptoengine.server import decrypt_data as decrypt_task


METADATA_VERSION = 1
gpg = gnupg.GPG(use_agent=True)


class GPGError(Exception):
    """
    Exception raised if GPG encryption or decryption fails.
    """
    def __init__(self, result):
        self.result = result

    def __str__(self):
        return self.result.status


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


class Provider(object):
    """
    Base class for cloud provider.
    """
    def  __init__(self, config, bucket_name, encryption_method="gpg"):
        """
        Initialize cloud provider.
        """
        self.config = config
        self.config.check("general", ["database"])
        self.config.check("gnupg", ["recipients", "signer"])
        self.bucket_name = bucket_name
        if encryption_method.lower() not in ["gpg", "symmetric", 
                                             "cryptoengine", ]:
            raise ValueError(
                "Encryption method must be either 'gpg', 'symmetric' or "
                "'cryptoengine'")
        self.encryption_method = encryption_method

    @property
    def __name__(self):
        return "cloud-provider-bucket:" + self.bucket_name

    def __str__(self):
        return self.__name__

    def connect(self):
        """
        Connect to cloud provider.
        """
        pass

    def disconnect(self):
        """
        Disconnect from cloud provider.
        """
        pass

    def store(self, key, data):
        """
        Store data to cloud provider.
        """
        pass

    def store_from_filename(self, key, filename):
        """
        Store data to cloud provider from file.
        """
        pass

    def retrieve(self, key):
        """
        Retrieve data from cloud provider. Return data as string.
        """
        return None

    def retrieve_to_filename(self, key, filename):
        """
        Retrieve data from cloud provider. Write data to file.
        """
        pass

    def delete(self, key):
        """
        Delete data from cloud provider.
        """
        pass

    def list(self):
        """
        List data in cloud provider. Return dictionary of keys with
        data.
        """
        return dict()

    def list_keys(self):
        """
        List data keys in cloud provider.
        """
        return dict()


class Cloud(object):
    """
    Basic class for cloud access.
    """
    def __init__(self, config, metadata_provider, provider, database):
        self.config = config
        self.metadata_provider = metadata_provider
        self.provider = provider
        self.database = database
        self.recipients = self.config.config.get(
            "gnupg", "recipients").split(",")
        self.signer = self.config.config.get("gnupg", "signer")

    def _create_metadata(self, key, filename=None, size=0, stat_info=None,
                         checksum=None, encryption_key=None,
                         encrypted_size=0, encrypted_checksum=None):
        metadata = dict(
            metadata_version=METADATA_VERSION,
            provider=self.metadata_provider.__name__, key=key, name=None,
            path=None, size=size, mode=0, uid=0, gid=0, atime=0, mtime=0,
            ctime=0, checksum=None, encryption_key=encryption_key,
            encrypted_size=encrypted_size, encrypted_checksum=None)
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

    def connect(self):
        """
        Open connection to cloud.
        """
        self.metadata_provider.connect()
        self.provider.connect()
        return self

    def disconnect(self):
        """
        Close cloud connection.
        """
        self.metadata_provider.disconnect()
        self.provider.disconnect()

    def sync(self):
        """
        Sync metadata database from cloud.
        """
        self.database.drop(provider=self.metadata_provider.__name__)
        for key, encrypted_metadata in self.metadata_provider.list().items():
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
        for m in self.database.list(provider=self.metadata_provider.__name__):
            metadata.append(m)

        return metadata

    def find(self, **filter):
        """
        Find metadata in database.
        """
        return self.database.find(**filter)

    def find_one(self, **filter):
        """
        Find metadata in database.
        """
        return self.database.find_one(**filter)

    def _encrypt_gpg(self, data):
        encryption_key = None
        encrypted_data = gpg.encrypt(
            data, self.recipients, sign=self.signer)
        if not encrypted_data.ok:
            raise GPGError(encrypted_data)
        encrypted_size = len(encrypted_data.data)
        encrypted_checksum = checksum_data(encrypted_data.data)
        return (encryption_key, encrypted_data.data, encrypted_size,
                encrypted_checksum)

    def _encrypt_file_gpg(self, plaintext_file, encrypted_file):
        encryption_key = None
        encrypted_data = gpg.encrypt_file(
            file(plaintext_file), self.recipients, sign=self.signer,
            output=encrypted_file)
        if not encrypted_data.ok:
            raise GPGError(encrypted_data)
        encrypted_stat_info = os.stat(encrypted_file)
        encrypted_checksum = checksum_file(encrypted_file)
        encrypted_size = encrypted_stat_info.st_size
        return (encryption_key, encrypted_size, encrypted_checksum)

    def _encrypt_symmetric(self, data):
        encryption_key = generate_random_password()
        plaintext_fp = StringIO(data)
        encrypted_fp = StringIO()
        encrypt(plaintext_fp, encrypted_fp, encryption_key)
        encrypted_fp.seek(0)
        encrypted_data = encrypted_fp.read()
        base64_data = base64.encodestring(encrypted_data)
        base64_size = len(base64_data)
        encrypted_checksum = checksum_data(base64_data)
        return (encryption_key, base64_data, base64_size,
                encrypted_checksum)

    def _encrypt_cryptoengine(self, data):
        encryption_key = generate_random_password()
        res = encrypt_task.delay(data, encryption_key)
        res.wait()
        result = res.get()
        base64_data = result["encrypted_data"]
        base64_size = len(base64_data)
        encrypted_checksum = result["encrypted_checksum"]
        return (encryption_key, base64_data, base64_size,
                encrypted_checksum)

    def _encrypt_file_symmetric(self, plaintext_file, encrypted_file):
        encryption_key = generate_random_password()
        plaintext_fp = file(plaintext_file)
        encrypted_fp = tempfile.TemporaryFile()
        encrypt(plaintext_fp, encrypted_fp, encryption_key)
        encrypted_fp.flush()
        encrypted_fp.seek(0)
        base64_fp = file(encrypted_file, "wb")
        base64.encode(encrypted_fp, base64_fp)
        base64_fp.close()
        encrypted_fp.close()
        plaintext_fp.close()
        encrypted_stat_info = os.stat(encrypted_file)
        encrypted_size = encrypted_stat_info.st_size
        encrypted_checksum = checksum_file(encrypted_file)
        return (encryption_key, encrypted_size, encrypted_checksum)

    def _encrypt_file_cryptoengine(self, plaintext_file, encrypted_file):
        encryption_key = generate_random_password()
        data = file(plaintext_file).read()
        res = encrypt_task.delay(data, encryption_key)
        res.wait()
        result = res.get()
        base64_data = result["encrypted_data"]
        base64_size = len(base64_data)
        encrypted_checksum = result["encrypted_checksum"]
        encrypted_fp = file(encrypted_file, "wb")
        encrypted_fp.write(base64_data)
        encrypted_fp.close()
        return (encryption_key, base64_size, encrypted_checksum)

    def store(self, data, cloud_filename, stat_info=None):
        """
        Encrypt data and store it to cloud.
        """
        key = checksum_data(data + cloud_filename)
        checksum = checksum_data(data)
        size = len(data)

        # Do we have the data already stored into cloud?
        old_metadata = self.database.find_one(
            provider=self.metadata_provider.__name__, checksum=checksum)
        if old_metadata:
            encrypted_data = None
            encryption_key = old_metadata["encryption_key"]
            encrypted_checksum = old_metadata["encrypted_checksum"]
            encrypted_size = old_metadata["encrypted_size"]
        else:
            # Create encrypted data.
            if self.provider.encryption_method == "symmetric":
                (encryption_key, encrypted_data, encrypted_size,
                 encrypted_checksum) = self._encrypt_symmetric(data)
            elif self.provider.encryption_method == "cryptoengine":
                (encryption_key, encrypted_data, encrypted_size,
                 encrypted_checksum) = self._encrypt_cryptoengine(data)
            else:
                (encryption_key, encrypted_data, encrypted_size,
                 encrypted_checksum) = self._encrypt_gpg(data)

        # Create encrypted metadata.
        metadata = self._create_metadata(
            key, filename=cloud_filename, size=size, stat_info=stat_info,
            checksum=checksum, encryption_key=encryption_key,
            encrypted_size=encrypted_size,
            encrypted_checksum=encrypted_checksum)
        encrypted_metadata = gpg.encrypt(
            json.dumps(metadata), self.recipients, sign=self.signer)
        if not encrypted_metadata.ok:
            raise GPGError(encrypted_metadata)

        # Store metadata and data to cloud and update database.
        self.metadata_provider.store(key, encrypted_metadata.data)
        if not old_metadata:
            self.provider.store(checksum, encrypted_data)
        self.database.update(metadata)
        return metadata

    def store_from_filename(self, filename, cloud_filename=None):
        """
        Encrypt file data and store it to cloud.
        """
        if cloud_filename is None:
            cloud_filename = filename

        stat_info = os.stat(filename)
        key = checksum_file(filename, extra_data=cloud_filename)
        checksum = checksum_file(filename)
        size = stat_info.st_size

        # Do we have the data already stored into cloud?
        old_metadata = self.database.find_one(
            provider=self.metadata_provider.__name__, checksum=checksum)
        if old_metadata:
            encrypted_file = None
            encryption_key = old_metadata["encryption_key"]
            encrypted_checksum = old_metadata["encrypted_checksum"]
            encrypted_size = old_metadata["encrypted_size"]
        else:
            # Create encrypted data file.
            encrypted_file = tempfile.NamedTemporaryFile()
            if self.provider.encryption_method == "symmetric":
                (encryption_key, encrypted_size, encrypted_checksum) =\
                    self._encrypt_file_symmetric(filename, encrypted_file.name)
            elif self.provider.encryption_method == "cryptoengine":
                (encryption_key, encrypted_size, encrypted_checksum) =\
                    self._encrypt_file_cryptoengine(
                        filename, encrypted_file.name)
            else:
                (encryption_key, encrypted_size, encrypted_checksum) =\
                    self._encrypt_file_gpg(filename, encrypted_file.name)

        # Create encrypted metadata.
        metadata = self._create_metadata(
            key, filename=cloud_filename, size=size, stat_info=stat_info,
            checksum=checksum, encryption_key=encryption_key,
            encrypted_size=encrypted_size,
            encrypted_checksum=encrypted_checksum)
        encrypted_metadata = gpg.encrypt(
            json.dumps(metadata), self.recipients, sign=self.signer)
        if not encrypted_metadata.ok:
            raise GPGError(encrypted_metadata)

        # Store metadata and data to cloud and update database.
        self.metadata_provider.store(key, encrypted_metadata.data)
        if not old_metadata:
            self.provider.store_from_filename(checksum, encrypted_file.name)
        self.database.update(metadata)

        return metadata

    def _decrypt_gpg(self, encrypted_data):
        data = gpg.decrypt(encrypted_data)
        if not data.ok:
            raise GPGError(data)
        checksum = checksum_data(data.data)
        return data.data, checksum

    def _decrypt_file_gpg(self, encrypted_file, plaintext_file):
        data = gpg.decrypt_file(
            file(encrypted_file), output=plaintext_file)
        if not data.ok:
            raise GPGError(data)
        checksum = checksum_file(plaintext_file)
        return checksum

    def _decrypt_symmetric(self, encrypted_data, encryption_key):
        encrypted_fp = StringIO(base64.decodestring(encrypted_data))
        plaintext_fp = StringIO()
        _, checksum = decrypt(encrypted_fp, plaintext_fp, encryption_key)
        plaintext_fp.seek(0)
        data = plaintext_fp.read()
        return data, checksum

    def _decrypt_cryptoengine(self, encrypted_data, encryption_key):
        res = decrypt_task.delay(encrypted_data, encryption_key)
        res.wait()
        result = res.get()
        data = result["data"]
        checksum = result["checksum"]
        return data, checksum

    def _decrypt_file_symmetric(self, encrypted_file, plaintext_file,
                                encryption_key):
        base64_fp = file(encrypted_file)
        encrypted_fp = tempfile.TemporaryFile()
        base64.decode(base64_fp, encrypted_fp)
        encrypted_fp.flush()
        encrypted_fp.seek(0)
        plaintext_fp = file(plaintext_file, "wb")
        _, checksum = decrypt(encrypted_fp, plaintext_fp, encryption_key)
        plaintext_fp.close()
        encrypted_fp.close()
        base64_fp.close()
        return checksum

    def _decrypt_file_cryptoengine(self, encrypted_file, plaintext_file,
                                   encryption_key):
        encrypted_data = file(encrypted_file).read()
        res = decrypt_task.delay(encrypted_data, encryption_key)
        res.wait()
        result = res.get()
        data = result["data"]
        checksum = result["checksum"]
        plaintext_fp = file(plaintext_file, "wb")
        plaintext_fp.write(data)
        plaintext_fp.close()
        return checksum

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
        if self.provider.encryption_method == "symmetric":
            data, checksum = self._decrypt_symmetric(
                encrypted_data, metadata["encryption_key"])
        elif self.provider.encryption_method == "cryptoengine":
            data, checksum = self._decrypt_cryptoengine(
                encrypted_data, metadata["encryption_key"])
        else:
            data, checksum = self._decrypt_gpg(encrypted_data)
        if checksum != metadata['checksum']:
            raise DataError(
                metadata["checksum"],
                "Wrong data checksum: {0} != {1}".format(
                    checksum, metadata["checksum"]))
        return data

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
        if self.provider.encryption_method == "symmetric":
            checksum = self._decrypt_file_symmetric(
                encrypted_file.name, filename, metadata["encryption_key"])
        elif self.provider.encryption_method == "cryptoengine":
            checksum = self._decrypt_file_cryptoengine(
                encrypted_file.name, filename, metadata["encryption_key"])
        else:
            checksum = self._decrypt_file_gpg(
                encrypted_file.name, filename)
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
        self.metadata_provider.delete(metadata["key"])
        self.database.delete(metadata["key"])
        if not self.database.find_one(
                provider=self.metadata_provider.__name__,
                checksum=metadata["checksum"]):
            # Metadata is removed, remove the data.
            self.provider.delete(metadata["checksum"])
