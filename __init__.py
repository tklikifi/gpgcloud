"""
Utility to store GPG encrypted data into Amazon S3 cloud.

`gpgcloud` is a simple tool to store encrypted data into Amazon S3 cloud.
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
6. All checksums MUST be calculated using `SHA-512` algorithm.
7. All temporary files created locally MUST be protected with `0600`
   permissions.

Dependencies
------------
GPG must be installed. The current version of `gpgcloud` is tested using:

* gpg (GnuPG/MacGPG2) 2.0.22 (libgcrypt 1.5.3).

Also the following Python modules must be installed:

* boto==2.27.0
* gnupg==1.2.5

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
TBD.

"""

__author__ = "Tommi Linnakangas"
__date__ = "2014-03-16"
__version__ = "0.1.0"
