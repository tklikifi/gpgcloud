#!/usr/bin/env python
"""
Main program for `GPGCloud` tool.
"""

import argparse
from operator import itemgetter
from aws import Aws
from config import Config, ConfigError
from cloud import Cloud, GPGError
from database import MetaDataDB
import sys
import time


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
        description="store and retrieve GPG encrypted data to and from "
                    "cloud service")
    parser.add_argument(
        '-c', '--config', type=str,
        help="configuration file for GPGCloud",
        default="~/.gpgcloud/gpgcloud.conf")
    parser.add_argument(
        '-v', '--verbose', help="show more verbose information",
        action="store_true")
    parser.add_argument(
        '-V', '--version', help="show version", action="store_true")
    parser.add_argument(
        'command', type=str, nargs='?',
        help="command (list|store|retrieve|remove|sync) (default: list)",
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


def show_files(metadata_list, verbose=False):
    if not verbose:
        print "{0:<8}{1:<7}{2:<7}{3:<10}{4:<21}{5:<12}{6}".format(
            "Mode", "Uid", "Gid", "Size", "Date", "Checksum", "Path")
        print "".join('-' for i in range(78))

    for metadata in sorted(metadata_list, key=itemgetter('path')):
        if verbose:
            for k, v in metadata.items():
                print "{0}: {1}".format(k.capitalize().replace('_', ' '), v)
            print
        else:
            mtime = time.strftime(
                '%Y-%m-%d %H:%M:%S',
                time.localtime(metadata["mtime"]))
            metadata["mtime"] = mtime
            metadata["checksum"] = metadata["checksum"][-10:]
            print ("{mode:<8o}{uid:<7}{gid:<7}{encrypted_size:<10}"
                   "{mtime:<21}{checksum:<12}{path}".format(**metadata))


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

    # Initialize cloud provider.
    aws_cloud = Aws(
        config.config.get("aws", "access_key"),
        config.config.get("aws", "secret_access_key"),
        config.config.get("aws", "data_bucket"),
        config.config.get("aws", "metadata_bucket"))
    database = MetaDataDB(
        config.config.get("general", "database"))
    cloud = Cloud(config, aws_cloud, database)

    input_file = None
    output_file = None

    if args.inputfile:
        input_file = args.inputfile
    if args.outputfile:
        output_file = args.outputfile

    if args.command == "list":
        metadata_list = cloud.list()
        if len(metadata_list) == 0:
            print "No files found in cloud."
            sys.exit(0)
        show_files(metadata_list, args.verbose)

    elif args.command == "list-aws":
        # This is a utility command to list raw data in Amazon S3.
        print "AWS metadata:"
        print "============="
        for k, data in cloud.provider.list_metadata().items():
            print "Key:", k
            print "Data:"
            print data

        print "AWS data:"
        print "========="
        for k, data in cloud.provider.list().items():
            print "Key:", k
            print "Data:"
            print data

    elif args.command == "sync":
        try:
            cloud.sync()
        except GPGError as e:
            error_exit(str(e))
        metadata_list = cloud.list()
        if len(metadata_list) == 0:
            print "No files found in cloud."
            sys.exit(0)
        show_files(metadata_list, args.verbose)

    elif args.command == "store":
        if not input_file:
            error_exit("Local filename not given.")
        if not output_file:
            output_file = input_file
        print "Storing file:", input_file, "->", output_file
        try:
            cloud.store_from_filename(input_file, output_file)
        except GPGError as e:
            error_exit(str(e))

    elif args.command == "retrieve":
        if not input_file:
            error_exit("Cloud filename not given.")
        if not output_file:
            output_file = input_file
        for metadata in cloud.list():
            if metadata["path"] == input_file:
                print "Retrieving file:", input_file, "->", output_file
                try:
                    cloud.retrieve_to_filename(metadata, output_file)
                except GPGError as e:
                    error_exit(str(e))
                sys.exit(0)
        error_exit("File not found in cloud: " + input_file)

    elif args.command == "remove":
        if not input_file:
            error_exit("Cloud filename not given.")
        for metadata in cloud.list():
            if metadata["path"] == input_file:
                print "Removing file:", input_file
                cloud.delete(metadata)

    else:
        error_exit("Unknown command: {0}".format(args.command))


if __name__ == "__main__":
    main()
