"""
Unit tests for `GPGCloud` project.
"""

import os
import tempfile
import unittest
from cloud import Cloud, amazon, sftp
from config import Config, ConfigError
from database import MetaDataDB
from lib import random_string, checksum_file, checksum_data


class TestUtils(unittest.TestCase):
    """
    Test cases for utility functions.
    """
    def setUp(self):
        pass

    def test_utils_random_string(self):
        """
        Test random string creation.
        """
        for length in range(10, 100, 10):
            random_1 = random_string(length)
            random_2 = random_string(length)
            self.assertEqual(len(random_1), length)
            self.assertEqual(len(random_2), length)
            self.assertNotEqual(random_1, random_2)

    def test_utils_checksum(self):
        """
        Test checksum functions.
        """
        checksum = "ba5d39304c72c92f73203798033eb52b" \
                   "e1830da828d4c82ee7023b74b81949d8"
        data = file("LICENSE").read()
        self.assertEqual(checksum_data(data), checksum)
        self.assertEqual(checksum_file("LICENSE"), checksum)


class TestConfig(unittest.TestCase):
    """
    Test cases for configuration handling.
    """
    def setUp(self):
        pass

    def test_config_no_file(self):
        """
        Test configuration handling without config file.
        """
        if os.path.isfile("test_config.conf"):
            os.remove("test_config.conf")
        self.assertRaises(ConfigError, Config, "test_config.conf")

    def test_config_ok_config(self):
        """
        Test configuration handling with config file.
        """
        test_data = ("[gnupg]\n"
                     "recipients = tkl@iki.fi\n"
                     "signer = tommi.linnakangas@iki.fi\n"
                     "\n"
                     "[amazon-s3]\n"
                     "access_key = ACCESSKEY\n"
                     "secret_access_key = SECRETACCESSKEY\n"
                     "\n"
                     "[data]\n"
                     "\n"
                     "bucket = DATABUCKET\n"
                     "[metadata]\n"
                     "bucket = METADATABUCKET\n"
                     "\n")
        if os.path.isfile("test_config.conf"):
            os.remove("test_config.conf")
        file("test_config.conf", "wb").write(test_data)
        config = Config("test_config.conf")
        self.assertIn("gnupg", config.config.sections())
        self.assertIn("amazon-s3", config.config.sections())
        self.assertEqual(config.config.get(
            "gnupg", "recipients"), "tkl@iki.fi")
        self.assertEqual(config.config.get(
            "gnupg", "signer"), "tommi.linnakangas@iki.fi")
        self.assertEqual(config.config.get(
            "amazon-s3", "access_key"), "ACCESSKEY")
        self.assertEqual(config.config.get(
            "amazon-s3", "secret_access_key"), "SECRETACCESSKEY")
        self.assertEqual(config.config.get(
            "data", "bucket"), "DATABUCKET")
        self.assertEqual(config.config.get(
            "metadata", "bucket"), "METADATABUCKET")
        os.remove("test_config.conf")

    def test_config_wrong_config(self):
        """
        Test configuration handling with config file with wrong config.
        """
        test_data_1 = ("[gnupg_missing]\n"
                       "recipients = tkl@iki.fi\n"
                       "signer = tkl@iki.fi\n"
                       "[amazon-s3]\n"
                       "access_key = ACCESSKEY\n"
                       "secret_access_key = SECRETACCESSKEY\n"
                       "[data]\n"
                       "bucket = DATABUCKET\n"
                       "[metadata]\n"
                       "bucket = METADATABUCKET\n")
        test_data_2 = ("[gnupg]\n"
                       "recipients_missing = tkl@iki.fi\n"
                       "signer = tkl@iki.fi\n"
                       "[amazon-s3]\n"
                       "access_key = ACCESSKEY\n"
                       "secret_access_key = SECRETACCESSKEY\n"
                       "[data]\n"
                       "bucket = DATABUCKET\n"
                       "[metadata]\n"
                       "bucket = METADATABUCKET\n")
        if os.path.isfile("test_config.conf"):
            os.remove("test_config.conf")
        file("test_config.conf", "wb").write(test_data_1)
        config = Config("test_config.conf")
        self.assertRaises(
            ConfigError, config.check, "gnupg", ["recipients", "signer"])
        file("test_config.conf", "wb").write(test_data_2)
        config = Config("test_config.conf")
        self.assertRaises(
            ConfigError, config.check, "gnupg", ["recipients", "signer"])
        os.remove("test_config.conf")


class TestAmazonS3(unittest.TestCase):
    """
    Test cases for Amazon S3 access.
    """
    def setUp(self):
        pass

    def test_amazon_s3_store_data(self):
        """
        Test storing data to Amazons S3, both to metadata and data buckets.
        """
        config = Config()
        metadata_bucket = config.config.get("metadata", "bucket")
        data_bucket = config.config.get("data", "bucket")
        metadata_provider = amazon.S3(config, metadata_bucket).connect()
        provider = amazon.S3(config, data_bucket).connect()

        datas = dict()
        metadatas = dict()

        for data, metadata in (("Data 1", "Metadata 1"),
                               ("Data 2", "Metadata 2")):
            key = checksum_data(data)
            metadata_provider.store(key, metadata)
            provider.store(key, data)
            new_metadata = metadata_provider.retrieve(key)
            new_data = provider.retrieve(key)
            self.assertEqual(new_data, data)
            self.assertEqual(new_metadata, metadata)
            datas[key] = data
            metadatas[key] = metadata
        for key, metadata in metadata_provider.list().items():
            self.assertEqual(metadata, metadatas[key])
        for key, data in provider.list().items():
            self.assertEqual(data, datas[key])
        for key, metadata in metadatas.items():
            metadata_provider.delete(key)
        for key, data in datas.items():
            provider.delete(key)
        metadata_provider.disconnect()
        provider.disconnect()

    def test_amazon_s3_store_filename(self):
        """
        Test storing files to Amazons S3, both to metadata and data buckets.
        """
        config = Config()
        metadata_bucket = config.config.get("metadata", "bucket")
        data_bucket = config.config.get("data", "bucket")
        metadata_provider = amazon.S3(config, metadata_bucket).connect()
        provider = amazon.S3(config, data_bucket).connect()
        key = checksum_file("LICENSE")
        metadata_provider.store(key, "LICENSE METADATA")
        provider.store_from_filename(key, "LICENSE")
        t = tempfile.NamedTemporaryFile()
        metadata = metadata_provider.retrieve(key)
        provider.retrieve_to_filename(key, t.name)
        self.assertEqual(file("LICENSE").read(), file(t.name).read())
        self.assertEqual("LICENSE METADATA", metadata)
        metadata_provider.delete(key)
        provider.delete(key)
        metadata_provider.disconnect()
        provider.disconnect()

    def test_amazon_s3_delete_all_keys(self):
        """
        Test deleting all Amazons S3 keys, both from metadata and
        data buckets.
        """
        config = Config()
        metadata_bucket = config.config.get("metadata", "bucket")
        data_bucket = config.config.get("data", "bucket")
        metadata_provider = amazon.S3(config, metadata_bucket).connect()
        provider = amazon.S3(config, data_bucket).connect()
        for key, metadata in metadata_provider.list().items():
            metadata_provider.delete(key)
        for key, data in provider.list().items():
            provider.delete(key)
        metadata_provider.disconnect()
        provider.disconnect()

class TestSftp(unittest.TestCase):
    """
    Test cases for SFTP filesystem.
    """
    def setUp(self):
        pass

    def test_sftp_store_data(self):
        """
        Test storing data to filesystem, both to metadata and data buckets.
        """
        config = Config()
        metadata_bucket = config.config.get("metadata", "bucket")
        data_bucket = config.config.get("data", "bucket")
        metadata_provider = sftp.Sftp(config, metadata_bucket).connect()
        provider = sftp.Sftp(config, data_bucket).connect()

        datas = dict()
        metadatas = dict()

        for data, metadata in (("Data 1", "Metadata 1"),
                               ("Data 2", "Metadata 2")):
            key = checksum_data(data)
            metadata_provider.store(key, metadata)
            provider.store(key, data)
            new_metadata = metadata_provider.retrieve(key)
            new_data = provider.retrieve(key)
            self.assertEqual(new_data, data)
            self.assertEqual(new_metadata, metadata)
            datas[key] = data
            metadatas[key] = metadata
        for key, metadata in metadata_provider.list().items():
            self.assertEqual(metadata, metadatas[key])
        for key, data in provider.list().items():
            self.assertEqual(data, datas[key])
        for key, metadata in metadatas.items():
            metadata_provider.delete(key)
        for key, data in datas.items():
            provider.delete(key)
        metadata_provider.disconnect()
        provider.disconnect()

    def test_sftp_store_filename(self):
        """
        Test storing files to SFTP filesystem, both to metadata and data
        buckets.
        """
        config = Config()
        metadata_bucket = config.config.get("metadata", "bucket")
        data_bucket = config.config.get("data", "bucket")
        metadata_provider = sftp.Sftp(config, metadata_bucket).connect()
        provider = sftp.Sftp(config, data_bucket).connect()
        key = checksum_file("LICENSE")
        metadata_provider.store(key, "LICENSE METADATA")
        provider.store_from_filename(key, "LICENSE")
        t = tempfile.NamedTemporaryFile()
        metadata = metadata_provider.retrieve(key)
        provider.retrieve_to_filename(key, t.name)
        self.assertEqual(file("LICENSE").read(), file(t.name).read())
        self.assertEqual("LICENSE METADATA", metadata)
        metadata_provider.delete(key)
        provider.delete(key)
        metadata_provider.disconnect()
        provider.disconnect()

    def test_sftp_delete_all_keys(self):
        """
        Test deleting all filesystem keys, both from metadata and
        data buckets.
        """
        config = Config()
        metadata_bucket = config.config.get("metadata", "bucket")
        data_bucket = config.config.get("data", "bucket")
        metadata_provider = sftp.Sftp(config, metadata_bucket).connect()
        provider = sftp.Sftp(config, data_bucket).connect()
        for key, metadata in metadata_provider.list().items():
            metadata_provider.delete(key)
        for key, data in provider.list().items():
            provider.delete(key)
        metadata_provider.disconnect()
        provider.disconnect()


class TestCloud(unittest.TestCase):
    """
    Test cases for cloud access, data is encrypted and decrypted.
    """
    def setUp(self):
        pass

    def _test_cloud_store_data(self, config, metadata_provider, provider):
        """
        Store encrypted data to cloud.
        """
        database = MetaDataDB(config)
        database.drop()
        cloud = Cloud(config, metadata_provider, provider, database).connect()
        data1 = file("testdata/data1.txt").read()
        data2 = file("testdata/data2.txt").read()
        data3 = file("testdata/data2.txt").read()
        data4 = file("testdata/data2.txt").read()
        metadata1 = cloud.store(data1, "testdata/data1.txt")
        metadata2 = cloud.store(data2, "testdata/data2.txt")
        metadata3 = cloud.store(data3, "testdata/data3.txt")
        metadata4 = cloud.store(data4, "testdata/data4.txt")
        for metadata in cloud.list():
            if metadata["key"] == metadata1["key"]:
                self.assertEqual("testdata/data1.txt", metadata["path"])
            if metadata["key"] == metadata2["key"]:
                self.assertEqual("testdata/data2.txt", metadata["path"])
            if metadata["key"] == metadata3["key"]:
                self.assertEqual("testdata/data3.txt", metadata["path"])
            if metadata["key"] == metadata4["key"]:
                self.assertEqual("testdata/data4.txt", metadata["path"])
        new_data1 = cloud.retrieve(metadata1)
        new_data2 = cloud.retrieve(metadata2)
        new_data3 = cloud.retrieve(metadata3)
        new_data4 = cloud.retrieve(metadata4)
        self.assertEqual(data1, new_data1)
        self.assertEqual("testdata/data1.txt", metadata1["path"])
        self.assertEqual(data2, new_data2)
        self.assertEqual("testdata/data2.txt", metadata2["path"])
        self.assertEqual(data2, new_data3)
        self.assertEqual("testdata/data3.txt", metadata3["path"])
        self.assertEqual(data2, new_data4)
        self.assertEqual("testdata/data4.txt", metadata4["path"])
        cloud.delete(metadata1)
        cloud.delete(metadata2)
        cloud.delete(metadata3)
        cloud.delete(metadata4)
        cloud.disconnect()

    def _test_cloud_amazon_s3_store_data(self, encryption_method):
        config = Config()
        metadata_bucket = config.config.get("metadata", "bucket")
        data_bucket = config.config.get("data", "bucket")
        metadata_provider = amazon.S3(config, metadata_bucket).connect()
        provider = amazon.S3(config, data_bucket, encryption_method).connect()
        self._test_cloud_store_data(config, metadata_provider, provider)

    def _test_cloud_sftp_store_data(self, encryption_method):
        config = Config()
        metadata_bucket = config.config.get("metadata", "bucket")
        data_bucket = config.config.get("data", "bucket")
        metadata_provider = sftp.Sftp(config, metadata_bucket).connect()
        provider = sftp.Sftp(config, data_bucket, encryption_method).connect()
        self._test_cloud_store_data(config, metadata_provider, provider)

    def _test_cloud_store_filename(self, config, metadata_provider, provider):
        """
        Store file as encrypted data to cloud.
        """
        database = MetaDataDB(config)
        database.drop()
        cloud = Cloud(config, metadata_provider, provider, database).connect()
        data1 = file("testdata/data1.txt").read()
        data2 = file("testdata/data2.txt").read()
        metadata1 = cloud.store_from_filename(
            "testdata/data1.txt", "testdata/data1.txt")
        metadata2 = cloud.store_from_filename(
            "testdata/data2.txt", "testdata/data2.txt")
        metadata3 = cloud.store_from_filename(
            "testdata/data2.txt", "testdata/data3.txt")
        metadata4 = cloud.store_from_filename(
            "testdata/data2.txt", "testdata/data4.txt")
        for metadata in cloud.list():
            if metadata["key"] == metadata1["key"]:
                self.assertEqual("testdata/data1.txt", metadata["path"])
            if metadata["key"] == metadata2["key"]:
                self.assertEqual("testdata/data2.txt", metadata["path"])
            if metadata["key"] == metadata3["key"]:
                self.assertEqual("testdata/data3.txt", metadata["path"])
            if metadata["key"] == metadata4["key"]:
                self.assertEqual("testdata/data4.txt", metadata["path"])
        cloud.retrieve_to_filename(
            metadata1, "testdata/new_data1.txt")
        cloud.retrieve_to_filename(
            metadata2, "testdata/new_data2.txt")
        cloud.retrieve_to_filename(
            metadata3, "testdata/new_data3.txt")
        cloud.retrieve_to_filename(
            metadata4, "testdata/new_data4.txt")
        self.assertEqual(data1, file("testdata/new_data1.txt").read())
        self.assertEqual("testdata/data1.txt", metadata1["path"])
        self.assertEqual(data2, file("testdata/new_data2.txt").read())
        self.assertEqual("testdata/data2.txt", metadata2["path"])
        self.assertEqual(data2, file("testdata/new_data3.txt").read())
        self.assertEqual("testdata/data3.txt", metadata3["path"])
        self.assertEqual(data2, file("testdata/new_data4.txt").read())
        self.assertEqual("testdata/data4.txt", metadata4["path"])
        cloud.delete(metadata1)
        cloud.delete(metadata2)
        cloud.delete(metadata3)
        cloud.delete(metadata4)
        cloud.disconnect()
        os.remove("testdata/new_data1.txt")
        os.remove("testdata/new_data2.txt")
        os.remove("testdata/new_data3.txt")
        os.remove("testdata/new_data4.txt")

    def _test_cloud_amazon_s3_store_filename(self, encryption_method):
        config = Config()
        metadata_bucket = config.config.get("metadata", "bucket")
        data_bucket = config.config.get("data", "bucket")
        metadata_provider = amazon.S3(config, metadata_bucket).connect()
        provider = amazon.S3(config, data_bucket, encryption_method).connect()
        self._test_cloud_store_filename(config, metadata_provider, provider)

    def _test_cloud_sftp_store_filename(self, encryption_method):
        config = Config()
        metadata_bucket = config.config.get("metadata", "bucket")
        data_bucket = config.config.get("data", "bucket")
        metadata_provider = sftp.Sftp(config, metadata_bucket).connect()
        provider = sftp.Sftp(config, data_bucket, encryption_method).connect()
        self._test_cloud_store_filename(config, metadata_provider, provider)


class TestCloudGpgEncryption(TestCloud):

    def test_cloud_amazon_s3_store_data(self):
        self._test_cloud_amazon_s3_store_data(encryption_method="gpg")

    def test_cloud_sftp_store_data(self):
        self._test_cloud_sftp_store_data(encryption_method="gpg")

    def test_cloud_amazon_s3_store_filename(self):
        self._test_cloud_amazon_s3_store_filename(encryption_method="gpg")

    def test_cloud_sftp_store_filename(self):
        self._test_cloud_sftp_store_filename(encryption_method="gpg")


class TestCloudSymmetricEncryption(TestCloud):

    def test_cloud_amazon_s3_store_data(self):
        self._test_cloud_amazon_s3_store_data(encryption_method="symmetric")

    def test_cloud_sftp_store_data(self):
        self._test_cloud_sftp_store_data(encryption_method="symmetric")

    def test_cloud_amazon_s3_store_filename(self):
        self._test_cloud_amazon_s3_store_filename(
            encryption_method="symmetric")

    def test_cloud_sftp_store_filename(self):
        self._test_cloud_sftp_store_filename(encryption_method="symmetric")

class TestCloudCryptoEngineEncryption(TestCloud):

    def test_cloud_amazon_s3_store_data(self):
        self._test_cloud_amazon_s3_store_data(encryption_method="cryptoengine")

    def test_cloud_sftp_store_data(self):
        self._test_cloud_sftp_store_data(encryption_method="cryptoengine")

    def test_cloud_amazon_s3_store_filename(self):
        self._test_cloud_amazon_s3_store_filename(
            encryption_method="cryptoengine")

    def test_cloud_sftp_store_filename(self):
        self._test_cloud_sftp_store_filename(encryption_method="cryptoengine")


if __name__ == "__main__":
    unittest.main()
