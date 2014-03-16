"""
Handle data encryption and decryption.
"""

import gnupg
import json
from aws import Aws, AwsError
from config import Config
from utils import checksum_data


gpg = gnupg.GPG(use_agent=True)


def list_aws(config=None):
    """
    List keys from Amazon S3 cloud and decrypt metadata.
    """

    if config is None:
        config = Config()

    aws = Aws(
        config.config.get("aws", "access_key"),
        config.config.get("aws", "secret_access_key"),
        config.config.get("aws", "bucket"))

    keys = dict()

    for key, encrypted_metadata in aws.list().items():
        metadata_str = str(gpg.decrypt(encrypted_metadata))
        metadata = json.loads(metadata_str)
        keys[key] = metadata

    return keys


class File(object):
    """
    Class for data objects.
    """
    def __init__(self, filename, config=None):
        self.filename = filename
        self.key = None

        if config is not None:
            self.config = config
        else:
            self.config = Config()

        self.aws = Aws(
            self.config.config.get("aws", "access_key"),
            self.config.config.get("aws", "secret_access_key"),
            self.config.config.get("aws", "bucket"))

    def store_aws(self, filename=None):
        """
        Encrypt file data and store it to Amazon S3 cloud.
        """
        if filename is None:
            filename = self.filename

        data = file(self.filename).read()
        data_checksum = checksum_data(data)
        recipient = self.config.config.get("gnupg", "identity")
        encrypted_data = str(gpg.encrypt(data, [recipient]))
        metadata = {
            "name": filename,
            "data_size": len(data),
            "data_checksum": data_checksum,
            "encrypted_data_size": len(encrypted_data),
            "encrypted_data_checksum": checksum_data(encrypted_data),
            }
        encrypted_metadata = str(gpg.encrypt(
            json.dumps(metadata), [recipient]))
        self.aws.store_data(data_checksum, encrypted_data, encrypted_metadata)
        self.key = data_checksum

    def retrieve_aws(self, filename=None):
        """
        Retrieve data from Amazon S3 cloud and decrypt it.
        """
        if self.key is None:
            raise AwsError("No key set to file")

        if filename is None:
            filename = self.filename

        encrypted_data, encrypted_metadata = self.aws.retrieve(self.key)
        encrypted_data_checksum = checksum_data(encrypted_data)
        data = str(gpg.decrypt(encrypted_data))
        data_checksum = checksum_data(data)
        metadata_str = str(gpg.decrypt(encrypted_metadata))
        metadata = json.loads(metadata_str)
        assert(encrypted_data_checksum == metadata['encrypted_data_checksum'])
        assert(data_checksum == metadata['data_checksum'])
        file(filename, "wb").write(data)

    def delete_aws(self):
        """
        Delete data from Amazon S3 cloud.
        """
        if self.key is None:
            raise AwsError("No key set to file")

        self.aws.delete(self.key)
