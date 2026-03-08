from db.models.Model import Model


class Discussion(Model):
    @staticmethod
    def validate(data):
        if not isinstance(data.get('locked'), bool) and not isinstance(data.get('locked'), int):
            raise ValueError("Locked must be a boolean or integer")
        if data.get('visibility') != 'public' and data.get('visibility') != 'hidden':
            raise ValueError("Invalid visibility value")
        return


    def __init__(self, data):
        Discussion.validate(data)
        self.raw_attributes = {k: v for k, v in data.items()}
        self.id = data.get('id')
        self.locked = bool(data.get('locked'))
        self.visibility = data.get('visibility', 'hidden')


    def to_dict(self):
        return {
            'id': self.id,
            'locked': self.locked,
            'visibility': self.visibility,
            # 'raw_attributes': self.raw_attributes
        }

    @property
    def locked(self):
        return self._locked

    @property
    def visibility(self):
        return self._visibility

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

    @locked.setter
    def locked(self, value):
        self.raw_attributes['locked'] = value
        self._locked = value

    @visibility.setter
    def visibility(self, value):
        self.raw_attributes['visibility'] = value
        self._visibility = value

    @raw_attributes.setter
    def raw_attributes(self, value):
        self._raw_attributes = value