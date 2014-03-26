"""
Library module for `gpgcloud`.
"""

import hashlib
import random
import string


def random_string(length=8, string_type=None):
    """
    Generate random string of given length.
    """
    if string_type is None:
        string_type = string.lowercase + string.uppercase + string.digits
    return ''.join(random.choice(string_type) for i in range(length))


def checksum_data(data):
    """
    Calculate SHA-256 checksum over given data.
    """
    return hashlib.sha256(data).hexdigest()


def checksum_stream(f, extra_data=None, block_size=2**20):
    """
    Calculate SHA-256 checksum for opened data stream.
    """
    sha256 = hashlib.sha256()
    while True:
        data = f.read(block_size)
        if not data:
            break
        sha256.update(data)
    if extra_data is not None:
        sha256.update(extra_data)
    return sha256.hexdigest()


def checksum_file(filename, extra_data=None, block_size=2**20):
    """
    Calculate SHA-256 checksum for given file.
    """
    return checksum_stream(
        file(filename), extra_data=extra_data, block_size=block_size)
