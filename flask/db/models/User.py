from db.models.Model import Model


class User(Model):
    @staticmethod
    def validate(data):
        if 'name' not in data or not data['name']:
            raise ValueError("Name is required")
        if 'email' not in data or not data['email']:
            raise ValueError("Email is required")
        if 'reading_speed' in data:
            try:
                speed = int(data['reading_speed'])
                if speed <= 0:
                    raise ValueError("Reading speed must be a positive integer")
            except ValueError:
                raise ValueError("Reading speed must be a positive integer")

    def __init__(self, data):
        User.validate(data)
        self.raw_attributes = {k: v for k, v in data.items()}
        self.id = data.get('id')
        self.name = data.get('name')
        self.email = data.get('email')
        self.reading_speed = data.get('reading_speed')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'reading_speed': self.reading_speed,
            # 'raw_attributes': self.raw_attributes
        }

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        return self._id

    @property
    def email(self):
        return self._email

    @property
    def reading_speed(self):
        return self._reading_speed

    @property
    def raw_attributes(self):
        return self._raw_attributes

    @id.setter
    def id(self, value):
        self.raw_attributes['id'] = value
        self._id = value

    @name.setter
    def name(self, value):
        self.raw_attributes['name'] = value
        self._name = value

    @email.setter
    def email(self, value):
        self.raw_attributes['email'] = value
        self._email = value

    @reading_speed.setter
    def reading_speed(self, value):
        self.raw_attributes['reading_speed'] = value
        self._reading_speed = value

    @raw_attributes.setter
    def raw_attributes(self, value):
        self._raw_attributes = value