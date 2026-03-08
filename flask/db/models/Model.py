from abc import ABC, abstractmethod

class Model(ABC):
    @staticmethod
    def is_junction_table():
        return False

    @staticmethod
    def validate(data):
        pass

    @abstractmethod
    def __init__(self, data):
        pass

    @abstractmethod
    def to_dict(self):
        pass

    def has_field(self, field_name):
        return hasattr(self, field_name)

    def __eq__(self, other):
        if not isinstance(other, Model):
            return False
        return self.to_dict() == other.to_dict()