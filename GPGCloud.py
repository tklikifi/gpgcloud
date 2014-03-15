#!/usr/bin/env python
"""
Main program for `GPGCloud` tool.
"""

import argparse
from config import Config, ConfigError
from aws import Aws, AwsError
import os
import sys

def error_exit(message):
    """
    Write error message and exit.
    """
    sys.stderr.write("ERROR: " + message + "\n")
    sys.exit(1)


def show_version():
    """
    Show the version of `GPGCloud` tool.
    """
    from gpgcloud import __version__
    print "GPGCloud", __version__
    sys.exit(0)


def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="store and retrieve GPG encypted data to and from Amazon "
                    "S3 cloud service")
    parser.add_argument(
        '-c', '--config', type=str,
        help="configuration file for GPGCloud",
        default="~/.gpgcloud/gpgcloud.conf")
    parser.add_argument(
        '-V', '--version', help="show version", action="store_true")

    return parser.parse_args()


def main():
    """
    Main function for `GPGCloud`.
    """
    args = parse_args()
    if args.version:
        show_version()

    config = None

    try:
        config = Config(args.config)
    except ConfigError as e:
        error_exit(str(e))

    aws = Aws(config.config.get("aws", "access_key"),
              config.config.get("aws", "secret_access_key"))

    print "ACCESS KEY:", aws.access_key
    print "SECRET ACCESS KEY:", aws.secret_access_key


if __name__ == "__main__":
    main()
