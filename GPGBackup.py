#!/usr/bin/env python
"""
Main program for `GPGBackup` tool.
"""

import argparse
from operator import itemgetter
from aws import Aws
from config import Config, ConfigError
from cloud import Cloud, DataError, GPGError, MetadataError
from database import MetaDataDB
import os
import sys
import time


def error_exit(error):
    """
    Write error message and exit.
    """
    if isinstance(error, (DataError, MetadataError)):
        error = "{0}: {1} (key: {2})".format(
            error.__class__.__name__, str(error), error.key)
    elif isinstance(error, Exception):
        error = "{0}: {1}".format(
            error.__class__.__name__, str(error))
    sys.stderr.write("ERROR: " + error + "\n")
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
        description="Backup and restore GPG encrypted files to and from "
                    "cloud service. List files in cloud service. Remove "
                    "files from cloud service.")
    parser.add_argument(
        '-c', '--config', type=str,
        help="configuration file for GPGBackup",
        default="~/.gpgcloud/gpgcloud.conf")
    parser.add_argument(
        '-v', '--verbose', help="show more verbose information",
        action="store_true")
    parser.add_argument(
        '-V', '--version', help="show version", action="store_true")
    parser.add_argument(
        'command', type=str, nargs='?',
        help="command to execute: list|backup|restore|remove|sync|"
             "list-aws-keys|list-aws-data (default: list)",
        default="list")
    parser.add_argument(
        'inputfile', type=str, nargs='?',
        help="the name of the local file when backing up file to cloud; "
             "the name of the file in cloud when restoring file from cloud")
    parser.add_argument(
        'outputfile', type=str, nargs='?',
        help="the name of the file in cloud when backing up file to cloud; "
             "the name of the local file when restoring file from cloud")

    return parser.parse_args()


def show_files(metadata_list, verbose=False):
    if not verbose:
        # Show header line if we are not in verbose mode.
        print "{0:<8}{1:<7}{2:<7}{3:<10}{4:<21}{5:<12}{6}".format(
            "Mode", "Uid", "Gid", "Size", "Date", "Checksum", "Path")
        print "".join('-' for i in range(78))

    for metadata in sorted(metadata_list, key=itemgetter('path')):
        if verbose:
            # In verbose mode, show all details from the metadata.
            for k, v in metadata.items():
                print "{0}: {1}".format(k.capitalize().replace('_', ' '), v)
            print
        else:
            # Only show the information required in the header line.
            mtime = time.strftime(
                '%Y-%m-%d %H:%M:%S',
                time.localtime(metadata["mtime"]))
            metadata["mtime"] = mtime
            metadata["checksum"] = metadata["checksum"][-10:]
            print ("{mode:<8o}{uid:<7}{gid:<7}{encrypted_size:<10}"
                   "{mtime:<21}{checksum:<12}{path}".format(**metadata))


def backup_file(cloud, input_file, output_file):
    """
    Backup one file to cloud.
    """
    print "Backing up file:", input_file, "->", output_file
    try:
        cloud.store_from_filename(input_file, output_file)
    except Exception as e:
        error_exit(e)


def backup_directory(cloud, input_file, output_file):
    """
    Backup directory to cloud.
    """
    for root, dirnames, filenames in os.walk(input_file):
        for filename in filenames:
            filename = root + "/" + filename
            if filename.startswith("./"):
                filename = filename[2:]
            if output_file != input_file:
                cloud_file = os.path.normpath(output_file + "/" + filename)
            else:
                cloud_file = filename
            backup_file(cloud, filename, cloud_file)


def main():
    """
    Main function for `GPGBackup` tool.
    """
    args = parse_args()
    if args.version:
        show_version()

    config = None

    try:
        config = Config(args.config)
    except ConfigError as e:
        error_exit(e)

    # Initialize cloud provider and metadata database.
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

    elif args.command == "list-aws-keys":
        # This is a utility command to list keys in Amazon S3.
        print "AWS metadata keys:"
        print "=================="
        for metadata in cloud.provider.list_metadata_keys().values():
            print "Key: {name}\nSize: {size}\n" \
                  "Last modified: {last_modified}\n".format(**metadata)
        print "AWS data keys:"
        print "=============="
        for metadata in cloud.provider.list_keys().values():
            print "Key: {name}\nSize: {size}\n" \
                  "Last modified: {last_modified}\n".format(**metadata)

    elif args.command == "list-aws-data":
        # This is a utility command to list raw data in Amazon S3.
        print "AWS metadata:"
        print "============="
        for k, data in cloud.provider.list_metadata().items():
            print "Key:", k
            print "Data:", data
        print "AWS data:"
        print "========="
        for k, data in cloud.provider.list().items():
            print "Key:", k
            print "Data:", data

    elif args.command == "sync":
        try:
            cloud.sync()
        except (GPGError, MetadataError, DataError) as e:
            error_exit(e)
        metadata_list = cloud.list()
        if len(metadata_list) == 0:
            print "No files found in cloud."
            sys.exit(0)
        show_files(metadata_list, args.verbose)

    elif args.command == "backup":

        if not input_file:
            error_exit("Local filename not given.")
        if not output_file:
            output_file = input_file
        if os.path.isdir(input_file):
            backup_directory(cloud, input_file, output_file)
            sys.exit(0)
        elif os.path.isfile(input_file) or os.path.islink(input_file):
            backup_file(cloud, input_file, output_file)
        else:
            error_exit("No such file or directory: '{0}'".format(input_file))

    elif args.command == "restore":
        if not input_file:
            error_exit("Cloud filename not given.")
        input_file = os.path.normpath(input_file)

        if output_file:
            output_file = os.path.normpath(output_file)

        # Get the list of files.
        cloud_list = cloud.list()

        # First, check whether we have an exact match.
        for metadata in cloud_list:
            if metadata["path"] == input_file:
                if not output_file:
                    output_file = input_file
                print "Restoring file:", input_file, "->", output_file
                try:
                    cloud.retrieve_to_filename(metadata, output_file)
                except (GPGError, MetadataError, DataError) as e:
                    error_exit(e)
                sys.exit(0)

        # Then, try to find all files, that have the same directory.
        file_found = False
        for metadata in cloud_list:
            if metadata["path"].startswith(input_file + "/"):
                file_found = True
                if not output_file:
                    local_file = metadata["path"]
                else:
                    local_file = output_file + "/" + metadata["path"]
                print "Restoring file:", metadata["path"], "->", local_file
                try:
                    cloud.retrieve_to_filename(metadata, local_file)
                except (GPGError, MetadataError, DataError) as e:
                    error_exit(e)

        if file_found:
            sys.exit(0)

        error_exit("File not found in cloud: " + input_file)

    elif args.command == "remove":
        if not input_file:
            error_exit("Cloud filename not given.")

        # Get the list of files.
        cloud_list = cloud.list()

        # First, check whether we have an exact match.
        for metadata in cloud_list:
            if metadata["path"] == input_file:
                print "Removing file:", input_file
                cloud.delete(metadata)
                sys.exit(0)

        # Then, try to find all files, that have the same directory.
        file_found = False
        for metadata in cloud_list:
            if metadata["path"].startswith(input_file + "/"):
                file_found = True
                print "Removing file:", metadata["path"]
                cloud.delete(metadata)

        if file_found:
            sys.exit(0)

        error_exit("File not found in cloud: " + input_file)

    else:
        error_exit("Unknown command: {0}".format(args.command))


if __name__ == "__main__":
    main()
