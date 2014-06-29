#!/usr/bin/env python
"""
Main program for `GPGBackup` tool.
"""

import argparse
from operator import itemgetter
from config import Config, ConfigError
from cloud import amazon, Cloud, DataError, GPGError, MetadataError, sftp
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
    Show the version of `GPGBackup` tool.
    """
    from gpgcloud import __version__
    print os.path.basename(sys.argv[0]), __version__
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
        '-p', '--provider', type=str,
        help="cloud provider for GPGBackup: amazon-s3|sftp (default: "
             "amazon-s3)",
        default="amazon-s3")
    parser.add_argument(
        '-v', '--verbose', help="show more verbose information",
        action="store_true")
    parser.add_argument(
        '-V', '--version', help="show version", action="store_true")
    parser.add_argument(
        'command', type=str, nargs='?',
        help="command to execute: list|backup|restore|remove|sync|"
             "list-cloud-keys|list-cloud-data (default: list)",
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
    """
    Show files stored in cloud. In verbose mode all metadata fields
    are shown.
    """
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
    if cloud.find_one(path=output_file):
        return False

    print "Backing up file:", input_file, "->", output_file
    cloud.store_from_filename(input_file, output_file)

    return True

def backup_directory(cloud, input_file, output_file):
    """
    Backup directory to cloud.
    """
    if cloud.find_one(path=output_file):
        return False

    for root, dirnames, filenames in os.walk(input_file):
        for filename in filenames:
            filename = root + "/" + filename
            if filename.startswith("./"):
                filename = filename[2:]
            if output_file != input_file:
                cloud_file = os.path.normpath(output_file + "/" + filename)
            else:
                cloud_file = filename
            if not backup_file(cloud, filename, cloud_file):
                print "File already exists: {0}".format(cloud_file)

    return True

def main():
    """
    Main function for `GPGBackup` tool.
    """
    args = parse_args()
    if args.version:
        show_version()

    config = None
    metadata_provider = None
    provider = None

    try:
        config = Config(args.config)
    except ConfigError as e:
        error_exit(e)

    metadata_bucket = config.config.get("metadata", "bucket")
    data_bucket = config.config.get("data", "bucket")

    # Initialize cloud provider and metadata database.
    if args.provider == "amazon-s3":
        metadata_provider = amazon.S3(config, metadata_bucket)
        provider = amazon.S3(config, data_bucket)
    elif args.provider == "sftp":
        metadata_provider = sftp.Sftp(config, metadata_bucket)
        provider = sftp.Sftp(config, data_bucket)
    else:
        error_exit("Unknown cloud provider: {0}".format(args.provider))

    cloud = Cloud(config, metadata_provider, provider, MetaDataDB(config))

    input_file = None
    output_file = None

    if args.inputfile:
        input_file = args.inputfile
    if args.outputfile:
        output_file = args.outputfile

    exit_value = 0

    try:
        if args.command == "list":
            metadata_list = cloud.list()
            if len(metadata_list) == 0:
                print "No files found."
                sys.exit(0)
            show_files(metadata_list, args.verbose)
        elif args.command == "list-cloud-keys":
            # This is a utility command to list keys in cloud.
            cloud.connect()
            msg = "Cloud metadata keys: " + str(cloud.metadata_provider)
            print msg
            print "=" * len(msg)
            for metadata in cloud.metadata_provider.list_keys().values():
                print "Key: {name}\nSize: {size}\n" \
                      "Last modified: {last_modified}\n".format(**metadata)
            msg = "Cloud data keys: " + str(cloud.provider)
            print msg
            print "=" * len(msg)
            for metadata in cloud.provider.list_keys().values():
                print "Key: {name}\nSize: {size}\n" \
                      "Last modified: {last_modified}\n".format(**metadata)
            cloud.disconnect()
        elif args.command == "list-cloud-data":
            # This is a utility command to list raw data in cloud.
            cloud.connect()
            msg = "Cloud metadata: " + str(cloud.metadata_provider)
            print msg
            print "=" * len(msg)
            for k, data in cloud.metadata_provider.list().items():
                print "Key:", k
                print "Data:", data
            msg = "Cloud data: " + str(cloud.provider)
            print msg
            print "=" * len(msg)
            for k, data in cloud.provider.list().items():
                print "Key:", k
                print "Data:", data
            cloud.disconnect()
        elif args.command == "sync":
            cloud.connect()
            cloud.sync()
            cloud.disconnect()
            metadata_list = cloud.list()
            if len(metadata_list) == 0:
                print "No files found."
                sys.exit(0)
            show_files(metadata_list, args.verbose)
        elif args.command == "backup":
            if not input_file:
                error_exit("Local filename not given.")
            if not output_file:
                output_file = input_file
            if os.path.isdir(input_file):
                cloud.connect()
                if not backup_directory(cloud, input_file, output_file):
                    print "File already exists: {0}".format(output_file)
                    exit_value = 1
                cloud.disconnect()
                sys.exit(exit_value)
            elif os.path.isfile(input_file) or os.path.islink(input_file):
                cloud.connect()
                if not backup_file(cloud, input_file, output_file):
                    print "File already exists: {0}".format(output_file)
                    exit_value = 1
                cloud.disconnect()
                sys.exit(exit_value)
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
            cloud.connect()
            for metadata in cloud_list:
                if metadata["path"] != input_file:
                    continue
                if not output_file:
                    output_file = input_file
                print "Restoring file:", input_file, "->", output_file
                cloud.retrieve_to_filename(metadata, output_file)
                cloud.disconnect()
                sys.exit(0)

            # Then, try to find all files, that have the same directory.
            file_found = False
            for metadata in cloud_list:
                if not metadata["path"].startswith(input_file + "/"):
                    continue
                file_found = True
                if not output_file:
                    local_file = metadata["path"]
                else:
                    local_file = output_file + "/" + metadata["path"]
                print "Restoring file:", metadata["path"], "->", local_file
                cloud.retrieve_to_filename(metadata, local_file)
            cloud.disconnect()
            if file_found:
                sys.exit(0)
            error_exit("File not found: " + input_file)
        elif args.command == "remove":
            if not input_file:
                error_exit("Cloud filename not given.")

            # Get the list of files.
            cloud_list = cloud.list()

            # First, check whether we have an exact match.
            cloud.connect()
            for metadata in cloud_list:
                if metadata["path"] != input_file:
                    continue
                print "Removing file:", input_file
                cloud.delete(metadata)
                cloud.disconnect()
                sys.exit(0)

            # Then, try to find all files, that have the same directory.
            file_found = False
            for metadata in cloud_list:
                if not metadata["path"].startswith(input_file + "/"):
                    continue
                file_found = True
                print "Removing file:", metadata["path"]
                cloud.delete(metadata)
            cloud.disconnect()
            if file_found:
                sys.exit(0)
            error_exit("File not found: " + input_file)
        else:
            error_exit("Unknown command: {0}".format(args.command))
    except Exception as e:
        cloud.disconnect()
        error_exit(e)

if __name__ == "__main__":
    main()
