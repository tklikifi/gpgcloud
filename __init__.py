"""
Utility to store GPG encrypted data into Amazon S3 cloud.

GPGCloud is a simple tool to store encrypted data into Amazon S3 cloud.
The main focus of the tool is to use secure storage in the cloud: all data
is encrypted and no information about what kind of data is stored is revealed
to cloud provider.

The security and privacy of the data is based on GPG encryption, which is
performed outside the cloud environment. You MUST keep your GPG keyring safe,
otherwise your data is not safe either.

Requirements
============

The main requirements for the tool are described below.

Security and privacy
--------------------
1. Data MUST always be encrypted before it is stored into cloud.
2. Information about the data MUST NOT be revealed to cloud provider.
3. Encryption keys MUST NOT be stored to cloud.
4. Encryption keys MUST be protected by passphrase.
5. Data MUST be encrypted using `AES-256` algorithm.
6. All checksums MUST be calculated using `SHA-256` algorithm.
7. All temporary files created locally MUST be protected with `0600`
   permissions.

Dependencies
------------
GPG must be installed. The current version of `gpgcloud` is developed
and tested using:

* gpg (GnuPG/MacGPG2) 2.0.22 (libgcrypt 1.5.3).

Also the following Python modules must be installed:

* boto==2.27.0
* dataset==0.5.2
* python_gnupg==0.3.6

Quality
-------
Test Driver Development (TDD) MUST be practiced. Before new functionality
is written test code (unit tests) must be written first.

All code MUST have unit tests.

Functionality
-------------

TBD.

Performance
-----------

TBD.

Scalability
-----------

TBD.

Architecture
============

TBD.

User stories
============

The basic functionality of the tool is described as user stories.

Store one file to cloud
-----------------------

I, as the user of the tool, want to be able to store one file to cloud so
that no information about where the data comes from or what the data is is
revealed to the cloud provider.

The data must be identified only by the hash of the original data. The
information about the available files (metadata) must be stored separately
either in cloud or locally. This metadata must also be encrypted so that no
information is revealed to cloud provider.

List available files in cloud
-----------------------------

I, as the user of the tool, want to be able to list all files stored to cloud.
It must be possible to see the metadata of the stored files, similar to `ls
-l` output:

* original file name with absolute path
* creation and modification timestamps of the original file
* permissions of the original file
* uid and gid of the original file
* size of the original file
* size of the encrypted data stored to cloud
* checksum of the original file
* checksum of the encrypted data

Retrieve one file from the cloud
--------------------------------

I, as the user of the tool, want to be able to retrieve one file from cloud to
local directory, either to original location or to a given location with a
given file name. The checksum of the original file is used as the key to
file in cloud.

Store directory to cloud
------------------------

TBD.

Retrieve directory from cloud
-----------------------------

TBD.

"""

__author__ = "Tommi Linnakangas"
__date__ = "2014-03-16"
__version__ = "0.1.0"
