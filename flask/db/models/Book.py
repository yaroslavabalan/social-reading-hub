import re

from db.models.Model import Model


class Book(Model):
    @staticmethod
    def validate(data):
        if 'title' not in data or not isinstance(data['title'], str) or not data['title'].strip():
            raise ValueError("Title is required and must be a non-empty string")

        if 'author' not in data or not isinstance(data['author'], str) or not data['author'].strip():
            raise ValueError("Author is required and must be a non-empty string")

        year = data.get('year')
        if not isinstance(year, int):
            raise ValueError(f"Year must be an integer")

        cover_url = data.get('cover_url', '')

        if not isinstance(cover_url, str):
            raise ValueError("Cover URL must be a valid URL")

        if 'source' not in data or not isinstance(data['source'], str) or not data['source'].strip():
            raise ValueError("Source is required and must be a non-empty string")

        if 'genre' not in data or not isinstance(data['genre'], str) or not data['genre'].strip():
            raise ValueError("Genre is required and must be a non-empty string")

        if 'project_gutenberg_no' in data:
            pg_id = data['project_gutenberg_no']
            if not (isinstance(pg_id, int) or pg_id is None):
                raise ValueError("Project Gutenberg ID must be an integer or None")


    def __init__(self, data):
        Book.validate(data)
        self.raw_attributes = {k: v for k, v in data.items()}
        self.id = data.get('id')
        self.title = data.get('title').strip()
        self.author = data.get('author').strip()
        self.year = data.get('year')
        self.cover_url = data.get('cover_url').strip()
        self.source = data.get('source').strip()
        self.genre = data.get('genre').strip()
        self.project_gutenberg_no = data.get('project_gutenberg_no')



    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'year': self.year,
            'cover_url': self.cover_url,
            'source': self.source,
            'genre': self.genre,
            'project_gutenberg_no': self.project_gutenberg_no,
            # 'raw_attributes': self.raw_attributes
        }

    @property
    def id(self):
        return self._id

    @property
    def title(self):
        return self._title

    @property
    def author(self):
        return self._author

    @property
    def year(self):
        return self._year

    @property
    def cover_url(self):
        return self._cover_url

    @property
    def source(self):
        return self._source

    @property
    def project_gutenberg_no(self):
        return self._project_gutenberg_no

    @property
    def genre(self):
        return self._genre

    @property
    def raw_attributes(self):
        return self._raw_attributes

    @id.setter
    def id(self, value):
        self.raw_attributes['id'] = value
        self._id = value

    @title.setter
    def title(self, value):
        self.raw_attributes['title'] = value
        self._title = value

    @author.setter
    def author(self, value):
        self.raw_attributes['author'] = value
        self._author = value

    @year.setter
    def year(self, value):
        self.raw_attributes['year'] = value
        self._year = value

    @cover_url.setter
    def cover_url(self, value):
        self.raw_attributes['cover_url'] = value
        self._cover_url = value

    @source.setter
    def source(self, value):
        self.raw_attributes['source'] = value
        self._source = value

    @genre.setter
    def genre(self, value):
        self.raw_attributes['genre'] = value
        self._genre = value

    @project_gutenberg_no.setter
    def project_gutenberg_no(self, value):
        self.raw_attributes['project_gutenberg_no'] = value
        self._project_gutenberg_no = value

    @raw_attributes.setter
    def raw_attributes(self, value):
        self._raw_attributes = value
