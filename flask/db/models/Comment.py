from db.models.Model import Model


class Comment(Model):
    @staticmethod
    def validate(data):
        if 'timestamp' not in data or not data['timestamp']:
            raise ValueError("Timestamp is required")
        if 'content' not in data or not data['content'].strip():
            raise ValueError("Content is required")



    def __init__(self, data):
        Comment.validate(data)
        self.raw_attributes = {k: v for k, v in data.items()}
        self.id = data.get('id')
        self.timestamp = data.get('timestamp')
        self.content = data.get('content').strip()


    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'content': self.content,
            # 'raw_attributes': self.raw_attributes
        }

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def content(self):
        return self._content

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

    @timestamp.setter
    def timestamp(self, value):
        self.raw_attributes['timestamp'] = value
        self._timestamp = value

    @content.setter
    def content(self, value):
        self.raw_attributes['content'] = value
        self._content = value

    @raw_attributes.setter
    def raw_attributes(self, value):
        self._raw_attributes = value