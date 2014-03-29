"""
.. include:: ../README.md
.. todo:: Add support for Google Cloud Storage.
.. todo:: Add support for Dropbox.

Requirements
============

The main requirements for the tool are described below.

Security and privacy
--------------------
1. Data **MUST** always be encrypted before it is stored into cloud.
2. Information about the data **MUST NOT** be revealed to cloud provider.
3. Encryption keys **MUST NOT** be stored to cloud.
4. Encryption keys **MUST** be protected by passphrase.
5. Data MUST be encrypted using **AES-256** algorithm.
6. All checksums MUST be calculated using **SHA-256** algorithm.
7. All temporary files created locally MUST be protected with **0600**
   permissions.

Dependencies
------------
GPG must be installed. The current version of GPGCloud is developed and
tested using:

* Python-2.7.5
* gpg (GnuPG/MacGPG2) 2.0.22 (libgcrypt 1.5.3)
* gpg-agent (GnuPG/MacGPG2) 2.0.22 (libgcrypt 1.5.3)

The following Python modules (and their dependencies) must be installed:

.. literalinclude:: ../requirements.txt

Run the following command to install all necessary Python modules:

``pip install -r requirements.txt``

Quality
-------
Test Driver Development (TDD) **MUST** be practiced. Before new functionality
is written test code (unit tests) must be written first.

All code **MUST** have unit tests.

Functionality
-------------

The data **MUST** be identified only by the hash of the original data. The
information about the available files (metadata) **MUST** be stored
separately in cloud and locally (local database). This metadata **MUST** also
be encrypted in cloud so that no information is revealed to cloud provider.

Performance
-----------

TBD.

Scalability
-----------

TBD.

Architecture
============

Store data to cloud
-------------------

Use GPG to encrypt and sign both metadata and data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following flow chart describes the mode where both metadata and file
data are encrypted and signed using GPG:

.. graphviz::

   digraph G {

     node [fontname="helvetica-bold", fontsize=12];

     subgraph cluster_host {
       "File" [shape="box"];
       "Create metadata" [label="Create metadata"];
       "Metadata" [shape="box"];
       "GPG data" [label="Use GPG to encrypt\\nand sign data"];
       "GPG metadata" [label="Use GPG to encrypt\\nand sign metadata"];
       "Store metadata to database" [label="Store metadata\\nto database"];
       "Database" [shape="box"];
       "Encrypted data" [label="Encrypted file data\\nand checksums",
       shape="box"];
       "Store checksums to metadata" [label="Store checksums\\nto metadata"];
       "Encrypted metadata" [label="Encrypted metadata", shape="box"];
       "Store data" [label="Store data to cloud"];
       "Store metadata" [label="Store metadata to cloud"];
       label="User host";
       fontname="helvetica-bold";
       fontsize=16;
     }

     subgraph cluster_s3 {
       "Data bucket" [shape="box"];
       "Metadata bucket" [shape="box"];
       label="Amazon S3";
       fontname="helvetica-bold";
       fontsize=16;
     }

     "File" -> "Create metadata" -> "Metadata" ->
       "Store metadata to database" -> "Database";
     "Metadata" -> "GPG metadata" -> "Encrypted metadata" ->
     "Store metadata";
     "Store metadata" -> "Metadata bucket";
     "File" -> "GPG data" -> "Encrypted data" -> "Store data";
     "Store data" -> "Data bucket";
     "Encrypted data" -> "Store checksums to metadata" -> "Metadata";
   }

Use GPG to only encrypt and sign metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. todo:: Data encryption without GPG is not implemented yet.

The following flow chart describes the mode where only metadata is
encrypted and signed using GPG. File data is encrypted using symmetric
**AES-256** encryption:

.. todo:: Document this.

Use GPG to only encrypt and sign metadata, data in encrypted in cloud
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. todo:: Data encryption in cloud is not implemented yet.

The following flow chart describes the mode where only metadata is
encrypted and signed using GPG. File data is encrypted using symmetric
**AES-256** encryption in another cloud node:

.. todo:: Document this.

Retrieve data from cloud
------------------------

Use GPG to verify and decrypt both metadata and data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The following flow

The following flow chart describes the mode where both metadata and file
data are verified and decrypted using GPG. Metadata is stored in
plaintext in local database:

.. todo:: Document this.

Use GPG to only encrypt and sign metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. todo:: Data encryption without GPG is not implemented yet.

The following flow chart describes the mode where only metadata is
encrypted and signed using GPG. File data is encrypted using symmetric
**AES-256** encryption:

.. todo:: Document this.

Use GPG to only encrypt and sign metadata, data in encrypted in cloud
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. todo:: Data encryption in cloud is not implemented yet.

The following flow chart describes the mode where only metadata is
encrypted and signed using GPG. File data is encrypted using symmetric
**AES-256** encryption in another cloud node:

.. todo:: Document this.

User stories
============

The basic functionality of GPGCloud is described as user stories.

Store one file to cloud
-----------------------

I, as the user of GPGCloud, want to be able to store one file to cloud so
that no information about where the data comes from or what the data is is
revealed to the cloud provider.

List available files in cloud
-----------------------------

I, as the user of GPGCloud, want to be able to list all files stored to cloud.
It must be possible to see the metadata of the stored files, similar to ``ls
-l`` output:

* file path in cloud
* modification timestamp of the original file
* creation timestamp of the original file (in verbose mode)
* permissions of the original file
* uid and gid of the original file
* size of the original file (in verbose mode)
* size of the encrypted data in cloud
* checksum of the original file
* checksum of the encrypted data (in vebose mode)

Retrieve one file from the cloud
--------------------------------

I, as the user of GPGCloud, want to be able to retrieve one file from cloud to
local directory, either to original location or to a given location with a
given file name.

Store directory to cloud
------------------------

I, as the user of GPGCloud, want to be able to store one directory to cloud
so that no information about where the data comes from or what the data is is
revealed to the cloud provider. All files in the given directory are stored
to cloud.

Retrieve directory from cloud
-----------------------------

I, as the user of GPGCloud, want to be able to retrieve one directory from
cloud to local directory, either to original location or to a given location
with a given directory name.

"""

__author__ = "Tommi Linnakangas"
__date__ = "2014-03-23"
__version__ = "0.2.0"
