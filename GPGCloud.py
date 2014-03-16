#!/usr/bin/env python
"""
Main program for `GPGCloud` tool.
"""

import argparse
from config import Config, ConfigError
from data import list_aws, File
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
    parser.add_argument(
        'command', type=str, nargs='?',
        help="command (list|store|retrieve|remove) (default: list)",
        default="list")
    parser.add_argument(
        'inputfile', type=str, nargs='?',
        help="the name of the local file when storing file to cloud; "
             "the name of the file in cloud when retrieving file from cloud")
    parser.add_argument(
        'outputfile', type=str, nargs='?',
        help="the name of the file in cloud when storing file to cloud; "
             "the name of the local file when retrieving file from cloud")

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

    input_file = None
    output_file = None

    if args.inputfile:
        input_file = args.inputfile
    if args.outputfile:
        output_file = args.outputfile

    if args.command == "list":
        keys = list_aws(config=config)
        print "Number of files in Amazon S3:", len(keys)
        for key, metadata in keys.items():
            print "{0} ({1}/{2})".format(
                metadata["name"], metadata["data_size"],
                metadata["encrypted_data_size"])

    elif args.command == "store":
        if not input_file:
            error_exit("Local filename not given.")
        if not output_file:
            output_file = input_file
        data_file = File(input_file, config=config)
        print "Storing file:", input_file, "->", output_file
        data_file.store_aws(output_file)

    elif args.command == "retrieve":
        if not input_file:
            error_exit("Cloud filename not given.")
        if not output_file:
            output_file = input_file
        keys = list_aws(config=config)
        for key, metadata in keys.items():
            if metadata["name"] == input_file:
                print "Retrieving file:", input_file, "->", output_file
                data_file = File(output_file, config=config)
                data_file.key = key
                data_file.retrieve_aws()

    elif args.command == "remove":
        if not input_file:
            error_exit("Cloud filename not given.")
        keys = list_aws(config=config)
        for key, metadata in keys.items():
            if metadata["name"] == input_file:
                print "Deleting file:", input_file
                data_file = File(input_file, config=config)
                data_file.key = key
                data_file.delete_aws()

if __name__ == "__main__":
    main()
