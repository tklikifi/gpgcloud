"""
Handle configurations. Configuration file format is basic python config
file. Example configuration file:

    [general]
    database = sqlite:////home/tkl/.gpgcloud/metadata.db

    [gnupg]
    recipients = tkl@iki.fi
    signer = tkl@iki.fi

    [amazon-s3]
    access_key = ACCESSKEY
    secret_access_key = SECRETACCESSKEY
    data_bucket = DATABUCKET
    metadata_bucket = METADATABUCKET

    [sftp]
    host = localhost
    port = 22
    username = tkl
    identity_file = /home/tkl/.ssh/testkey
    data_bucket = /home/tkl/GPGCloud/backup/DATABUCKET
    metadata_bucket = /home/tkl/GPGCloud/backup/METADATABUCKET
"""

import ConfigParser
import os


class ConfigError(Exception):
    """
    Exception raised if some mandatory configuration is missing.
    """
    pass


class Config(object):
    """
    Class for `gpgcloud` configuration.
    """
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
            raise ConfigError("No configuration file found: {0}".format(
                self.config_file))

    def check(self, section, keys):
        """
        Check that all necessary configuration options are found.
        """
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
