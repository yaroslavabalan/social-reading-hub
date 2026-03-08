import re

from db.models.Model import Model


class Shelf(Model):
    @staticmethod
    def validate(data):
        color = data.get('color')
        hex_color_regex = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')
        if not isinstance(color, str) or not hex_color_regex.match(color):
            raise ValueError("Color must be a valid hex string like '#RRGGBB' or '#RGB'")

        background_url = data.get('background_url')
        if background_url is not None and not isinstance(background_url, str):
            raise ValueError("Background URL must be a string if provided")
        return


    def __init__(self, data):
        Shelf.validate(data)
        self.raw_attributes = {k: v for k, v in data.items()}
        self.shelf_no = data.get('shelf_no')
        self.background_url = data.get('background_url')
        self.color = data.get('color')


    def to_dict(self):
        return {
            'shelf_no': self.shelf_no,
            'background_url': self.background_url,
            'color': self.color,
            # 'raw_attributes': self.raw_attributes
        }

    @property
    def color(self):
        return self._color

    @property
    def background_url(self):
        return self._background_url

    @property
    def shelf_no(self):
        return self._shelf_no

    @property
    def raw_attributes(self):
        return self._raw_attributes

    @shelf_no.setter
    def shelf_no(self, value):
        self.raw_attributes['shelf_no'] = value
        self._shelf_no = value

    @color.setter
    def color(self, value):
        self.raw_attributes['color'] = value
        self._color = value

    @background_url.setter
    def background_url(self, value):
        self.raw_attributes['background_url'] = value
        self._background_url = value

    @raw_attributes.setter
    def raw_attributes(self, value):
        self._raw_attributes = value