import re

from db.models.Model import Model


class ShelfBook(Model):
    @staticmethod
    def is_junction_table():
        return True

    @staticmethod
    def validate(data):
        progress = data.get('progress')
        try:
            progress_value = float(progress)
        except (TypeError, ValueError):
            raise ValueError("Progress must be a number between 0 and 100")
        if isinstance(progress, bool) or progress_value < 0 or progress_value > 100:
            raise ValueError("Progress must be a number between 0 and 100")


    def __init__(self, data):
        ShelfBook.validate(data)
        self.raw_attributes = {k: v for k, v in data.items()}
        self.progress = data.get('progress')

    def to_dict(self):
        return {
            'progress': self.progress,
            # 'raw_attributes': self.raw_attributes
        }

    @property
    def progress(self):
        return self._progress

    @property
    def raw_attributes(self):
        return self._raw_attributes

    @progress.setter
    def progress(self, value):
        self.raw_attributes['progress'] = value
        self._progress = value

    @raw_attributes.setter
    def raw_attributes(self, value):
        self._raw_attributes = value