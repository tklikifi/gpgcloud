GPGCloud
========

GPGCloud is a simple tool to store encrypted data into different cloud
environments. The main focus of the tool is to use secure storage in the
cloud: all data is encrypted and no information about what kind of data is
stored is revealed to cloud provider.

The security and privacy of the data is based on GPG encryption, which is
performed outside the cloud environment. You MUST keep your GPG keyring safe,
otherwise your data is not safe either.

Currently Amazon S3 clouds and SFTP filesystems are supported.
