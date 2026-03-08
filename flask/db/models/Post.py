from db.models.Model import Model


class Post(Model):
    @staticmethod
    def validate(data):
        description = data.get('description')
        if not isinstance(description, str) or not description.strip():
            raise ValueError("Description is required and must be a non-empty string")

        background = data.get('background')
        if background is not None and not isinstance(background, str):
            raise ValueError("Background must be a string if provided")
        return


    def __init__(self, data):
        Post.validate(data)
        self.raw_attributes = {k: v for k, v in data.items()}
        self.id = data.get('id')
        self.background = data.get('background')
        self.description = data.get('description')


    def to_dict(self):
        return {
            'id': self.id,
            'background': self.background,
            'description': self.description,
            # 'raw_attributes': self.raw_attributes
        }

    @property
    def background(self):
        return self._background

    @property
    def description(self):
        return self._description

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

    @background.setter
    def background(self, value):
        self.raw_attributes['background'] = value
        self._background = value

    @description.setter
    def description(self, value):
        self.raw_attributes['description'] = value
        self._description = value

    @raw_attributes.setter
    def raw_attributes(self, value):
        self._raw_attributes = value