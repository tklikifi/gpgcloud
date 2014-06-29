"""
Handle metadata database.
"""

import dataset


class MetaDataDB(object):

    def __init__(self, config):
        """
        Initialize internal file database.
        """
        self.config = config
        self._database = dataset.connect(
            self.config.config.get("general", "database"))
        self._metadata = self._database["metadata"]

    def drop(self, provider=None):
        """
        Drop database table and create it again.
        """
        if provider is not None:
            self._metadata.delete(provider=provider)
        else:
            self._metadata.drop()
            self._metadata = self._database["metadata"]

    def update(self, metadata):
        """
        Update database with new or existing metadata.
        """
        self._metadata.upsert(metadata, ["name", "key"])

    def delete(self, key, provider=None):
        """
        Delete key from file database.
        """
        if provider is not None:
            self._metadata.delete(provider=provider, key=key)
        else:
            self._metadata.delete(key=key)

    def list(self, provider=None):
        """
        List all entries in the database.
        """
        if provider is not None:
            return self._metadata.find(provider=provider)
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
