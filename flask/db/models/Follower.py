import re

from db.models.Model import Model


class Follower(Model):
    @staticmethod
    def is_junction_table():
        return True

    @staticmethod
    def validate(data):
        return

    def __init__(self, data):
        Follower.validate(data)
        self.raw_attributes = {k: v for k, v in data.items()}

    def to_dict(self):
        return {}

    @property
    def raw_attributes(self):
        return self._raw_attributes

    @raw_attributes.setter
    def raw_attributes(self, value):
        self._raw_attributes = value