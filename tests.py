import os
import tempfile
import unittest
from aws import Aws
from data import list_aws, File
from config import Config, ConfigError
from utils import random_string, checksum_file, checksum_data


class TestUtils(unittest.TestCase):

    def setUp(self):
        pass

    def test_random_string(self):
        """
        Test random string creation.
        """
        for length in range(10, 100, 10):
            random_1 = random_string(length)
            random_2 = random_string(length)
            self.assertEqual(len(random_1), length)
            self.assertEqual(len(random_2), length)
            self.assertNotEqual(random_1, random_2)

    def test_checksum(self):
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
        self.assertEqual(config.config.get("gnupg", "identity"), "")
        self.assertEqual(config.config.get("aws", "access_key"), "")
        self.assertEqual(config.config.get("aws", "secret_access_key"), "")
        os.remove("test_config.conf")

    def test_config(self):
        """
        Test configuration handling with config file.
        """
        test_data = ("[gnupg]\n"
                     "identity = tkl@iki.fi\n"
                     "\n"
                     "[aws]\n"
                     "access_key = ACCESSKEY\n"
                     "secret_access_key = SECRETACCESSKEY\n"
                     "bucket = BUCKET\n")
        if os.path.isfile("test_config.conf"):
            os.remove("test_config.conf")
        file("test_config.conf", "wb").write(test_data)
        config = Config("test_config.conf")
        self.assertIn("gnupg", config.config.sections())
        self.assertIn("aws", config.config.sections())
        self.assertEqual(config.config.get("gnupg", "identity"), "tkl@iki.fi")
        self.assertEqual(config.config.get("aws", "access_key"), "ACCESSKEY")
        self.assertEqual(config.config.get(
            "aws", "secret_access_key"), "SECRETACCESSKEY")
        self.assertEqual(config.config.get("aws", "bucket"), "BUCKET")
        os.remove("test_config.conf")


    def test_config_wrong_config(self):
        """
        Test configuration handling with config file with wrong config.
        """
        test_data_1 = ("[gnupg_missing]\n"
                       "identity = tkl@iki.fi\n"
                       "[aws]\n"
                       "access_key = ACCESSKEY\n"
                       "secret_access_key = SECRETACCESSKEY\n"
                       "bucket = BUCKET\n")
        test_data_2 = ("[gnupg]\n"
                       "identity_missing = tkl@iki.fi\n"
                       "[aws]\n"
                       "access_key = ACCESSKEY\n"
                       "secret_access_key = SECRETACCESSKEY\n"
                       "bucket = BUCKET\n")
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

    def test_store_data(self):
        c = Config()
        aws = Aws(c.config.get("aws", "access_key"),
                  c.config.get("aws", "secret_access_key"),
                  c.config.get("aws", "bucket"))

        keys = dict()

        for data, metadata in (("Data 1", "Metadata 1"),
                               ("Data 2", "Metadata 2")):
            key = checksum_data(data)
            aws.store_data(key, data, metadata)
            new_data, new_metadata = aws.retrieve(key)
            self.assertEqual(new_data, data)
            self.assertEqual(new_metadata, metadata)
            keys[key] = metadata

        for key, metadata in aws.list().items():
            self.assertEqual(metadata, keys[key])

        for key, metadata in keys.items():
            aws.delete(key)

    def test_store_file(self):
        c = Config()
        aws = Aws(c.config.get("aws", "access_key"),
                  c.config.get("aws", "secret_access_key"),
                  c.config.get("aws", "bucket"))
        key = checksum_file("LICENSE")
        aws.store_file(key, "LICENSE", "LICENSE METADATA")
        t = tempfile.NamedTemporaryFile()
        metadata = aws.retrieve_file(key, t.name)
        self.assertEqual(file("LICENSE").read(), file(t.name).read())
        self.assertEqual("LICENSE METADATA", metadata)
        aws.delete(key)

    def test_delete_all_keys(self):
        c = Config()
        aws = Aws(c.config.get("aws", "access_key"),
                  c.config.get("aws", "secret_access_key"),
                  c.config.get("aws", "bucket"))
        for key, metadata in aws.list().items():
            aws.delete(key)

class TestData(unittest.TestCase):

    def setUp(self):
        pass

    def test_store_file(self):
        c = Config()
        data_file_1 = File("testdata/data1.txt", config=c)
        data_file_1.store_aws()
        data_file_2 = File("testdata/data2.txt", config=c)
        data_file_2.store_aws()

        for key, metadata in list_aws().items():
            if key == data_file_1.key:
                self.assertEqual(data_file_1.filename, metadata["name"])
            if key == data_file_2.key:
                self.assertEqual(data_file_2.filename, metadata["name"])

        new_data_file_1 = File("testdata/new_data1.txt", config=c)
        new_data_file_1.key = data_file_1.key
        new_data_file_1.retrieve_aws()
        self.assertEqual(
            file("testdata/data1.txt").read(),
            file("testdata/new_data1.txt").read())
        os.remove("testdata/new_data1.txt")

        new_data_file_2 = File("testdata/new_data2.txt", config=c)
        new_data_file_2.key = data_file_2.key
        new_data_file_2.retrieve_aws()
        self.assertEqual(
            file("testdata/data2.txt").read(),
            file("testdata/new_data2.txt").read())
        os.remove("testdata/new_data2.txt")

        data_file_1.delete_aws()
        data_file_2.delete_aws()

if __name__ == "__main__":
    unittest.main()
