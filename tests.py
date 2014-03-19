import os
import tempfile
import unittest
from aws import Aws
from cloud import Cloud
from config import Config, ConfigError
from database import MetaDataDB
from utils import random_string, checksum_file, checksum_data


class TestUtils(unittest.TestCase):

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

    def setUp(self):
        pass

    def test_aws_store_data(self):
        c = Config()
        aws = Aws(c.config.get("aws", "access_key"),
                  c.config.get("aws", "secret_access_key"),
                  c.config.get("aws", "data_bucket"),
                  c.config.get("aws", "metadata_bucket"))

        datas = dict()
        metadatas = dict()

        for data, metadata in (("Data 1", "Metadata 1"),
                               ("Data 2", "Metadata 2")):
            key = checksum_data(data)
            aws.store_metadata(key, metadata)
            aws.store(key, data)
            new_metadata = aws.retrieve_metadata(key)
            new_data = aws.retrieve(key)
            self.assertEqual(new_data, data)
            self.assertEqual(new_metadata, metadata)
            datas[key] = data
            metadatas[key] = metadata

        for key, metadata in aws.list_metadata().items():
            self.assertEqual(metadata, metadatas[key])

        for key, data in aws.list().items():
            self.assertEqual(data, datas[key])

        for key, metadata in metadatas.items():
            aws.delete_metadata(key)

        for key, data in datas.items():
            aws.delete(key)

    def test_aws_store_filename(self):
        c = Config()
        aws = Aws(c.config.get("aws", "access_key"),
                  c.config.get("aws", "secret_access_key"),
                  c.config.get("aws", "data_bucket"),
                  c.config.get("aws", "metadata_bucket"))
        key = checksum_file("LICENSE")
        aws.store_metadata(key, "LICENSE METADATA")
        aws.store_from_filename(key, "LICENSE")
        t = tempfile.NamedTemporaryFile()
        metadata = aws.retrieve_metadata(key)
        aws.retrieve_to_filename(key, t.name)
        self.assertEqual(file("LICENSE").read(), file(t.name).read())
        self.assertEqual("LICENSE METADATA", metadata)
        aws.delete(key)
        aws.delete_metadata(key)

    def test_aws_delete_all_keys(self):
        c = Config()
        aws = Aws(c.config.get("aws", "access_key"),
                  c.config.get("aws", "secret_access_key"),
                  c.config.get("aws", "data_bucket"),
                  c.config.get("aws", "metadata_bucket"))
        for key, metadata in aws.list_metadata().items():
            aws.delete_metadata(key)
        for key, data in aws.list().items():
            aws.delete(key)

class TestCloud(unittest.TestCase):

    def setUp(self):
        pass

    def test_cloud_store_data(self):
        c = Config()
        aws = Aws(c.config.get("aws", "access_key"),
                  c.config.get("aws", "secret_access_key"),
                  c.config.get("aws", "data_bucket"),
                  c.config.get("aws", "metadata_bucket"))
        database = MetaDataDB(c.config.get("general", "database"))
        database.drop()
        cloud = Cloud(c, aws, database)
        data1 = file("testdata/data1.txt").read()
        data2 = file("testdata/data2.txt").read()
        metadata1 = cloud.store(data1, "testdata/data1.txt")
        metadata2 = cloud.store(data2, "testdata/data2.txt")
        for metadata in cloud.list():
            if metadata["key"] == metadata1["key"]:
                self.assertEqual("testdata/data1.txt", metadata["path"])
            if metadata["key"] == metadata2["key"]:
                self.assertEqual("testdata/data2.txt", metadata["path"])
        new_data1 = cloud.retrieve(metadata1)
        new_data2 = cloud.retrieve(metadata2)
        self.assertEqual(data1, new_data1)
        self.assertEqual("testdata/data1.txt", metadata1["path"])
        self.assertEqual(data2, new_data2)
        self.assertEqual("testdata/data2.txt", metadata2["path"])
        cloud.delete(metadata1)
        cloud.delete(metadata2)

    def test_cloud_store_filename(self):
        c = Config()
        aws = Aws(c.config.get("aws", "access_key"),
                  c.config.get("aws", "secret_access_key"),
                  c.config.get("aws", "data_bucket"),
                  c.config.get("aws", "metadata_bucket"))
        database = MetaDataDB(c.config.get("general", "database"))
        database.drop()
        cloud = Cloud(c, aws, database)
        data1 = file("testdata/data1.txt").read()
        data2 = file("testdata/data2.txt").read()
        metadata1 = cloud.store_from_filename("testdata/data1.txt")
        metadata2 = cloud.store_from_filename("testdata/data2.txt")
        for metadata in cloud.list():
            print metadata
            if metadata["key"] == metadata1["key"]:
                self.assertEqual("testdata/data1.txt", metadata["path"])
            if metadata["key"] == metadata2["key"]:
                self.assertEqual("testdata/data2.txt", metadata["path"])
        cloud.retrieve_to_filename(
            metadata1, "testdata/new_data1.txt")
        cloud.retrieve_to_filename(
            metadata2, "testdata/new_data2.txt")
        self.assertEqual(data1, file("testdata/new_data1.txt").read())
        self.assertEqual("testdata/data1.txt", metadata1["path"])
        self.assertEqual(data2, file("testdata/new_data2.txt").read())
        self.assertEqual("testdata/data2.txt", metadata2["path"])
        cloud.delete(metadata1)
        cloud.delete(metadata2)
        os.remove("testdata/new_data1.txt")
        os.remove("testdata/new_data2.txt")


if __name__ == "__main__":
    unittest.main()
