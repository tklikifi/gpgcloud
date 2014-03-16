#!/usr/bin/env python
"""
Main program for `GPGCloud` tool.
"""

import argparse
from operator import itemgetter
from config import Config, ConfigError
from data import AwsData
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
        description="store and retrieve GPG encypted data to and from Amazon "
                    "S3 cloud service")
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

    aws_data = AwsData(config=config)

    input_file = None
    output_file = None

    if args.inputfile:
        input_file = args.inputfile
    if args.outputfile:
        output_file = args.outputfile

    if args.command == "list":
        keys = aws_data.list()
        if len(keys) == 0:
            print "No files found in Amazon S3 cloud."
            sys.exit(0)

        if not args.verbose:
            print "{0:<8}{1:<7}{2:<7}{3:<10}{4:<21}{5}".format(
                "Mode", "Uid", "Gid", "Size", "Date", "Path")
            print "".join('-' for i in range(78))

        for metadata in sorted(keys.values(), key=itemgetter('path')):
            if args.verbose:
                print ("Path: '{path}', Size: {size}, "
                       "Encrypted size: {encrypted_size}, "
                       "Mode: {mode:o}, Uid: {uid}, Gid: {gid}, "
                       "Ctime: {ctime}, Mtime: {mtime}, Atime: {atime}, "
                       "Checksum: {checksum}".format(**metadata))
            else:
                mtime = time.strftime(
                    '%Y-%m-%d %H:%M:%S',
                    time.localtime(metadata["mtime"]))
                metadata["mtime"] = mtime
                print ("{mode:<8o}{uid:<7}{gid:<7}{encrypted_size:<10}"
                       "{mtime:<21}{path}".format(**metadata))

    elif args.command == "store":
        if not input_file:
            error_exit("Local filename not given.")
        if not output_file:
            output_file = input_file
        print "Storing file:", input_file, "->", output_file
        aws_data.store_from_filename(input_file, output_file)

    elif args.command == "retrieve":
        if not input_file:
            error_exit("Cloud filename not given.")
        if not output_file:
            output_file = input_file
        keys = aws_data.list()
        for key, metadata in keys.items():
            if metadata["path"] == input_file:
                print "Retrieving file:", input_file, "->", output_file
                aws_data.retrieve_to_filename(key, output_file)
                sys.exit(0)
        error_exit("File not found in Amazon S3 cloud: " + input_file)

    elif args.command == "remove":
        if not input_file:
            error_exit("Cloud filename not given.")
        keys = aws_data.list()
        for key, metadata in keys.items():
            if metadata["path"] == input_file:
                print "Deleting file:", input_file
                aws_data.delete(key)

if __name__ == "__main__":
    main()
