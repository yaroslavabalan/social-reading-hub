from db.models.Model import Model


class Highlight(Model):
    @staticmethod
    def validate(data):
        text = data.get('text')
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Text is required and must be a non-empty string")

        color = data.get('color')
        if not isinstance(color, str) or not color.strip():
            raise ValueError("Color is required and must be a non-empty string")

    def __init__(self, data):
        Highlight.validate(data)
        self.raw_attributes = {k: v for k, v in data.items()}
        self.id = data.get('id')
        self.text = data.get('text')
        self.timestamp = data.get('timestamp')
        self.color = data.get('color')


    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'timestamp': self.timestamp,
            'color': self.color,
            # 'raw_attributes': self.raw_attributes
        }

    @property
    def text(self):
        return self._text

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def color(self):
        return self._color

    @property
    def id(self):
        return self._id

    @property
    def raw_attributes(self):
        return self._raw_attributes

    @id.setter
    def id(self, value):
        self.raw_attributes['id'] = value
        self._id = value

    @text.setter
    def text(self, value):
        self.raw_attributes['text'] = value
        self._text = value

    @timestamp.setter
    def timestamp(self, value):
        self.raw_attributes['timestamp'] = value
        self._timestamp = value

    @color.setter
    def color(self, value):
        self.raw_attributes['color'] = value
        self._color = value

    @raw_attributes.setter
    def raw_attributes(self, value):
        self._raw_attributes = value