"""
Unit tests for `GPGCloud` tool.
"""

import os
import tempfile
import unittest
from cloud import Cloud, aws
from config import Config, ConfigError
from database import MetaDataDB
from utils import random_string, checksum_file, checksum_data


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
        config = Config("test_config.conf")
        self.assertIn("gnupg", config.config.sections())
        self.assertIn("aws", config.config.sections())
        self.assertEqual(config.config.get("gnupg", "recipients"), "")
        self.assertEqual(config.config.get("gnupg", "signer"), "")
        self.assertEqual(config.config.get("aws", "access_key"), "")
        self.assertEqual(config.config.get("aws", "secret_access_key"), "")
        os.remove("test_config.conf")

    def test_config_ok_config(self):
        """
        Test configuration handling with config file.
        """
        test_data = ("[gnupg]\n"
                     "recipients = tkl@iki.fi\n"
                     "signer = tommi.linnakangas@iki.fi\n"
                     "\n"
                     "[aws]\n"
                     "access_key = ACCESSKEY\n"
                     "secret_access_key = SECRETACCESSKEY\n"
                     "data_bucket = DATABUCKET\n"
                     "metadata_bucket = METADATABUCKET\n")
        if os.path.isfile("test_config.conf"):
            os.remove("test_config.conf")
        file("test_config.conf", "wb").write(test_data)
        config = Config("test_config.conf")
        self.assertIn("gnupg", config.config.sections())
        self.assertIn("aws", config.config.sections())
        self.assertEqual(config.config.get(
            "gnupg", "recipients"), "tkl@iki.fi")
        self.assertEqual(config.config.get(
            "gnupg", "signer"), "tommi.linnakangas@iki.fi")
        self.assertEqual(config.config.get(
            "aws", "access_key"), "ACCESSKEY")
        self.assertEqual(config.config.get(
            "aws", "secret_access_key"), "SECRETACCESSKEY")
        self.assertEqual(config.config.get(
            "aws", "data_bucket"), "DATABUCKET")
        self.assertEqual(config.config.get(
            "aws", "metadata_bucket"), "METADATABUCKET")
        os.remove("test_config.conf")


    def test_config_wrong_config(self):
        """
        Test configuration handling with config file with wrong config.
        """
        test_data_1 = ("[gnupg_missing]\n"
                       "recipients = tkl@iki.fi\n"
                       "signer = tkl@iki.fi\n"
                       "[aws]\n"
                       "access_key = ACCESSKEY\n"
                       "secret_access_key = SECRETACCESSKEY\n"
                       "data_bucket = DATABUCKET\n"
                       "metadata_bucket = METADATABUCKET\n")
        test_data_2 = ("[gnupg]\n"
                       "recipients_missing = tkl@iki.fi\n"
                       "signer = tkl@iki.fi\n"
                       "[aws]\n"
                       "access_key = ACCESSKEY\n"
                       "secret_access_key = SECRETACCESSKEY\n"
                       "data_bucket = DATABUCKET\n"
                       "metadata_bucket = METADATABUCKET\n")
        if os.path.isfile("test_config.conf"):
            os.remove("test_config.conf")
        file("test_config.conf", "wb").write(test_data_1)
        self.assertRaises(ConfigError, Config, "test_config.conf")
        file("test_config.conf", "wb").write(test_data_2)
        self.assertRaises(ConfigError, Config, "test_config.conf")
        os.remove("test_config.conf")


class TestAws(unittest.TestCase):
    """
    Test cases for Amazon S3 access.
    """
    def setUp(self):
        pass

    def test_aws_store_data(self):
        """
        Test storing data to Amazons S3, both to metadata and data buckets.
        """
        provider = aws.Aws(Config()).connect()

        datas = dict()
        metadatas = dict()

        for data, metadata in (("Data 1", "Metadata 1"),
                               ("Data 2", "Metadata 2")):
            key = checksum_data(data)
            provider.store_metadata(key, metadata)
            provider.store(key, data)
            new_metadata = provider.retrieve_metadata(key)
            new_data = provider.retrieve(key)
            self.assertEqual(new_data, data)
            self.assertEqual(new_metadata, metadata)
            datas[key] = data
            metadatas[key] = metadata

        for key, metadata in provider.list_metadata().items():
            self.assertEqual(metadata, metadatas[key])

        for key, data in provider.list().items():
            self.assertEqual(data, datas[key])

        for key, metadata in metadatas.items():
            provider.delete_metadata(key)

        for key, data in datas.items():
            provider.delete(key)

    def test_aws_store_filename(self):
        """
        Test storing files to Amazons S3, both to metadata and data buckets.
        """
        provider = aws.Aws(Config()).connect()
        key = checksum_file("LICENSE")
        provider.store_metadata(key, "LICENSE METADATA")
        provider.store_from_filename(key, "LICENSE")
        t = tempfile.NamedTemporaryFile()
        metadata = provider.retrieve_metadata(key)
        provider.retrieve_to_filename(key, t.name)
        self.assertEqual(file("LICENSE").read(), file(t.name).read())
        self.assertEqual("LICENSE METADATA", metadata)
        provider.delete(key)
        provider.delete_metadata(key)

    def test_aws_delete_all_keys(self):
        """
        Test deleting all Amazons S3 keys, both from metadata and
        data buckets.
        """
        provider = aws.Aws(Config()).connect()
        for key, metadata in provider.list_metadata().items():
            provider.delete_metadata(key)
        for key, data in provider.list().items():
            provider.delete(key)

class TestCloud(unittest.TestCase):
    """
    Test cases for cloud access, data is encrypted and decrypted.
    """
    def setUp(self):
        pass

    def test_cloud_store_data(self):
        """
        Store encrypted data to cloud.
        """
        config = Config()
        provider = aws.Aws(config).connect()
        database = MetaDataDB(config)
        database.drop()
        cloud = Cloud(config, provider, database)
        data1 = file("testdata/data1.txt").read()
        data2 = file("testdata/data2.txt").read()
        metadata1 = cloud.store(data1, "testdata/data1.txt")
        metadata2 = cloud.store(data2, "testdata/data2.txt")
        metadata3 = cloud.store(data2, "testdata/data3.txt")
        metadata4 = cloud.store(data2, "testdata/data4.txt")
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

    def test_cloud_store_filename(self):
        """
        Store file as encrypted data to cloud.
        """
        config = Config()
        provider = aws.Aws(config).connect()
        database = MetaDataDB(config)
        database.drop()
        cloud = Cloud(config, provider, database)
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
            print metadata
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
        os.remove("testdata/new_data1.txt")
        os.remove("testdata/new_data2.txt")
        os.remove("testdata/new_data3.txt")
        os.remove("testdata/new_data4.txt")


if __name__ == "__main__":
    unittest.main()
