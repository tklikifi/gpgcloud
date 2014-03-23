"""
Handle metadata database.
"""

import dataset


class MetaDataDB(object):

    def __init__(self, database):
        """
        Initialize internal file database.
        """
        self._db = dataset.connect(database)
        self._metadata = self._db["metadata"]

    def drop(self):
        """
        Drop database table and create it again.
        """
        self._metadata.drop()
        self._metadata = self._db["metadata"]

    def update(self, metadata):
        """
        Update database with new or existing metadata.
        """
        self._metadata.upsert(metadata, ["name", "key"])

    def delete(self, key):
        """
        Delete key from file database.
        """
        self._metadata.delete(key=key)

    def list(self):
        """
        List all entries in the database.
        """
        return self._metadata.all()

    def find(self, **filter):
        """
        Find metadata in database.
        """
        return self._metadata.find(**filter)

    def find_one(self, **filter):
        """
        Find metadata in database.
        """
        return self._metadata.find_one(**filter)