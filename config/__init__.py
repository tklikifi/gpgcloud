"""
Handle configurations.
"""

import ConfigParser
import os
from utils import random_string


class ConfigError(Exception):
    """
    Exception raised if some mandatory configuration is missing.
    """
    pass


class Config(object):
    """
    Class for `gpgcloud` configuration.
    """
    MANDATORY_CONFIGS = {
        "gnupg": ["recipients", "signer"],
        "aws": ["access_key", "secret_access_key", "bucket"], }

    def __init__(self, config_file="~/.gpgcloud/gpgcloud.conf"):
        """
        Initialize config object. If config file does not exist,
        create new one with defaults.
        """
        self.config_file = os.path.expanduser(config_file)
        self.config = ConfigParser.SafeConfigParser()

        if os.path.isfile(self.config_file):
            self.config.read(self.config_file)
        else:
            fp = file(self.config_file, "wb")
            self.config.add_section("gnupg")
            self.config.set("gnupg", "recipients", "")
            self.config.set("gnupg", "signer", "")
            self.config.add_section("aws")
            self.config.set("aws", "access_key", "")
            self.config.set("aws", "secret_access_key", "")
            self.config.set("aws", "bucket", random_string(20))
            self.config.write(fp)
        self.check()

    def check(self):
        """
        Check that all necessary configuration options are found.
        """
        for section, keys in self.MANDATORY_CONFIGS.items():
            if section not in self.config.sections():
                raise ConfigError(
                    "Section '{section}' missing from config file: "
                    "'{config_file}'".format(
                        section=section, config_file=self.config_file))
            for key in keys:
                try:
                    self.config.get(section, key)
                except ConfigParser.NoOptionError as e:
                    raise ConfigError(
                        "Error in config file: '{config_file}': ".format(
                        config_file=self.config_file) + str(e))
