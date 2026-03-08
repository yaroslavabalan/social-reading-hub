from abc import ABC, abstractmethod

class DBProvider(ABC):
    @abstractmethod
    def __init__(self, db_configuration):
        """
        Creates a connection to the database based on the provided db_configuration.
        """
        pass

    @abstractmethod
    def initialize_database(self):
        """
        Initializes the database, creating necessary tables and schemas.
        """
        pass

    def get(self, model_class, primary_keys):
        """
        Retrieves a single object of type model_class based on the provided primary_keys and their values.
        """
        results = self.get_list(model_class, filters=primary_keys)
        return results[0] if results else None

    def get_by_id(self, model_class, object_id):
        """
        A shorthand for get() when querying by 'id' column.
        """
        return self.get(model_class, {"id": object_id})

    @abstractmethod
    def get_list(self, model_class, filters=None):
        """
        Retrieves a list of objects of type model_class based on the provided filters.
        The filters are to be provided as a dictionary of structure {column_name: value},
        where these will be applied as WHERE conditions in the query for exact matching.
        """
        pass

    @abstractmethod
    def insert(self, input_object):
        """
        Inserts the provided object into the database.
        """
        pass

    @abstractmethod
    def delete(self, object):
        """
        Deletes the provided object from the database.
        """
        pass

    @abstractmethod
    def get_related(self, input_object, related_class, skip_to=None):
        """
        Retrieves related objects of type related_class for the given input_object.
        input_object should be a specific instance of a model, related_class is supposed to be a model class.

        If skip_to is provided, it indicates that the relationship should be traversed through an intermediate model,
        skipping directly to the skip_to class.
        """
        pass

    @abstractmethod
    def update(self, input_object):
        """
        Updates the provided object in the database based on its primary value(s).
        """
        pass

    @abstractmethod
    def drop_all_collections(self):
        """
        Drops all collections or tables in the database.
        """
        pass

    @abstractmethod
    def get_subclass(self, source_object, subclass):
        """
        Retrieves a subclass instance of the source_object if it exists.
        """
        pass