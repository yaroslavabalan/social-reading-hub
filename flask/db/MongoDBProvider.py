import logging
from enum import Enum

from bson import ObjectId
from flask import current_app, g
from flask_pymongo import PyMongo

from db.DBProvider import DBProvider
from db.models.Follower import Follower
from db.models.Follows import Follows
from db.models.Shelf import Shelf
from db.models.Book import Book
from db.models.Post import Post
from db.models.ShelfBook import ShelfBook
from db.models.Comment import Comment
from db.models.Discussion import Discussion
from db.models.Highlight import Highlight
from db.models.User import User

logger = logging.getLogger(__name__)

class RelationDirection(Enum):
    EMBEDDED = 'embedded'
    REFERENCE = 'reference'
    OWNER = 'owner'
    REFERENCED_BY = 'referenced_by'

model_collection_mapping = {
    User: ("users", "", {}, {"id": "_id"}),
    Book: ("books", "", {}, {"id": "_id"}),
    Shelf: ('users', "shelves",
        {'user_id': '_id'},
        {'shelf_no': 'shelves.shelf_no'}
    ),
    Discussion: ("highlights", "", {}, {"id": "_id"}),
    Post: ("highlights", "", {}, {"id": "_id"}),
    ShelfBook: ['users', 'shelves.books',
                {'user_id': '_id',
                 'shelf_no': 'shelves.shelf_no'},
                {'book_id': 'shelves.books.book_id'}
    ],
    Follower: ('users', "followers",
            {'followee_id': '_id'},
            {'follower_id': 'followers.follower_id'}
            ),
    Follows: ('users', "follows",
            {'follower_id': '_id'},
            {'followee_id': 'follows.followee_id'}
            ),
    Comment: ('highlights', "comments",
            {'discussion_id': '_id'},
            {'id': 'discussions.comments._id'}
            ),
    Highlight: ("highlights", "", {}, {"id": "_id"}),
}

model_relations = {
    User: {
        Shelf: (RelationDirection.OWNER, 'shelves'),
        Follower: (RelationDirection.OWNER, 'followers'),
        Follows: (RelationDirection.OWNER, 'follows'),
        Highlight: (RelationDirection.REFERENCED_BY, {'user_id': '_id'}),
    },
    Shelf: {
        User: (RelationDirection.EMBEDDED, {'user_id': '_id'}),
        ShelfBook: (RelationDirection.OWNER, 'books'),
    },
    ShelfBook: {
        Shelf: (RelationDirection.EMBEDDED, {'user_id': 'user_id', 'shelf_no': 'shelf_no'}),
        Book: (RelationDirection.REFERENCE, {'book_id': '_id'}),
    },
    Book: {
        ShelfBook: (RelationDirection.REFERENCED_BY, {'book_id': '_id'}),
        Highlight: (RelationDirection.REFERENCED_BY, {'book_id': '_id'}),
    },
    Follower: {
        User: (RelationDirection.REFERENCE, {'follower_id': '_id'}),
    },
    Follows: {
        User: (RelationDirection.REFERENCE, {'followee_id': '_id'}),
    },
    Highlight: {
        User: (RelationDirection.REFERENCE, {'user_id': '_id'}),
        Book: (RelationDirection.REFERENCE, {'book_id': '_id'}),
    },
    Discussion: {
        Highlight: (RelationDirection.EMBEDDED, {'id': '_id'}),
        Comment: (RelationDirection.OWNER, 'comments'),
    },
    Post: {
        Highlight: (RelationDirection.EMBEDDED, {'id': '_id'}),
    },
    Comment: {
        Discussion: (RelationDirection.EMBEDDED, {'discussion_id': '_id'}),
    }
}

class MongoDBProvider(DBProvider):
    @staticmethod
    def mongo_to_model(model_class, data):
        if '_id' in data:
            data['id'] = data['_id']
            del data['_id']
        return model_class(data)

    @staticmethod
    def model_to_mongo(data):
        for key, value in data.items():
            if key.endswith('_id'):
                data[key] = ObjectId(data[key])

        if 'id' in data:
            data['_id'] = ObjectId(data['id'])
            del data['id']

        return data

    def get_list(self, model_class, filters=None):
        if filters is None:
            filters = {}

        collection_info = model_collection_mapping.get(model_class)
        if not collection_info:
            raise ValueError(f"No collection mapping found for model class {model_class}")

        parent_collection = collection_info[0]
        embedded_path = collection_info[1]

        parent_filters = {}
        embedded_filters = {}

        for key, value in collection_info[2].items():
            if key in filters:
                mongo_field = value
                filter_value = ObjectId(filters[key]) if (value == '_id' or key.endswith('_id')) else filters[key]

                if embedded_path and mongo_field.startswith(embedded_path.split('.')[0] + '.'):
                    embedded_filters[mongo_field] = filter_value
                else:
                    parent_filters[mongo_field] = filter_value
                del filters[key]

        for key, value in collection_info[3].items():
            if key in filters:
                mongo_field = value
                filter_value = ObjectId(filters[key]) if (value == '_id' or key.endswith('_id')) else filters[key]

                if embedded_path:
                    embedded_filters[mongo_field] = filter_value
                else:
                    parent_filters[mongo_field] = filter_value
                del filters[key]

        pipeline = [
            {"$match": parent_filters}
        ]

        if embedded_path:
            parts = embedded_path.split('.')
            prefix = []
            for part in parts:
                prefix.append(part)
                path = '.'.join(prefix)
                pipeline.append({
                    "$unwind": {
                        "path": f"${path}",
                        "preserveNullAndEmptyArrays": True
                    }
                })

            pipeline.append({
                "$match": {
                    embedded_path: {"$exists": True, "$ne": None}
                }
            })

            if embedded_filters:
                pipeline.append({"$match": embedded_filters})

        if filters:
            pipeline.append({"$match": filters})

        if embedded_path:
            pipeline.append({"$replaceRoot": {"newRoot": f"${embedded_path}"}})

        result = self.db[parent_collection].aggregate(pipeline)
        result_list = list(result)

        result_models = []
        for data in result_list:
            try:
                model_instance = self.mongo_to_model(model_class, data)
                result_models.append(model_instance)
            except ValueError as e:
                logger.warning(f"Skipping invalid data for {model_class}: {e} (possibly a different subclass)")

        return result_models

    def insert(self, input_object):
        collection_info = model_collection_mapping.get(input_object.__class__)
        if not collection_info:
            raise ValueError(f"No collection mapping found for model class {input_object.__class__}")

        parent_collection = collection_info[0]
        embedded_path = collection_info[1]

        data = self.model_to_mongo(input_object.raw_attributes)

        if embedded_path:
            primary_filters = {}
            for key, value in collection_info[2].items():
                if key in data:
                    if value == '_id' or key.endswith('_id'):
                        primary_filters[value] = ObjectId(data[key])
                    else:
                        primary_filters[value] = data[key]

            path_parts = embedded_path.split('.')
            is_nested = len(path_parts) > 1

            if is_nested:
                array_filters = []
                push_path_parts = []

                for i, part in enumerate(path_parts[:-1]):
                    filter_identifier = f"elem{i}"
                    push_path_parts.append(f"{part}.$[{filter_identifier}]")

                    level_conditions = {}
                    for key, value in collection_info[2].items():
                        if key in data and value != '_id':
                            value_parts = value.split('.')
                            if len(value_parts) == i + 2 and value_parts[:i + 1] == path_parts[:i + 1]:
                                element_field = value_parts[-1]
                                raw_val = data[key]
                                if element_field == '_id' or element_field.endswith('_id'):
                                    level_conditions[f"{filter_identifier}.{element_field}"] = ObjectId(raw_val)
                                else:
                                    level_conditions[f"{filter_identifier}.{element_field}"] = raw_val

                    if level_conditions:
                        array_filters.append(level_conditions)

                push_path = '.'.join(push_path_parts + [path_parts[-1]])

                self.db[parent_collection].update_one(
                    primary_filters,
                    {"$push": {push_path: data}},
                    array_filters=array_filters
                )
            else:
                self.db[parent_collection].update_one(
                    primary_filters,
                    {"$push": {embedded_path: data}}
                )
        else:
            self.db[parent_collection].insert_one(data)

    def delete(self, input_object):
        collection_info = model_collection_mapping.get(input_object.__class__)

        if not collection_info:
            raise ValueError(f"No collection mapping found for model class {input_object.__class__}")

        parent_collection = collection_info[0]
        embedded_path = collection_info[1]

        if embedded_path:
            primary_filters = {}
            for key, value in collection_info[2].items():
                if key in input_object.raw_attributes:
                    if value == '_id' or key.endswith('_id'):
                        primary_filters[value] = ObjectId(input_object.raw_attributes[key])
                    else:
                        primary_filters[value] = input_object.raw_attributes[key]

            removal_criteria = {}
            for key, value in collection_info[3].items():
                if key in input_object.raw_attributes:
                    element_field = value.split('.')[-1]
                    raw_val = input_object.raw_attributes[key]
                    if element_field == '_id' or key.endswith('_id') or element_field.endswith('_id'):
                        removal_criteria[element_field] = ObjectId(raw_val)
                    else:
                        removal_criteria[element_field] = raw_val

            path_parts = embedded_path.split('.')
            is_nested = len(path_parts) > 1

            if is_nested:
                array_filters = []
                pull_path_parts = []

                for i, part in enumerate(path_parts[:-1]):
                    filter_identifier = f"elem{i}"
                    pull_path_parts.append(f"{part}.$[{filter_identifier}]")

                    level_conditions = {}
                    for key, value in collection_info[2].items():
                        if key in input_object.raw_attributes and value != '_id':
                            value_parts = value.split('.')
                            if len(value_parts) == i + 2 and value_parts[:i + 1] == path_parts[:i + 1]:
                                element_field = value_parts[-1]
                                raw_val = input_object.raw_attributes[key]
                                if element_field == '_id' or element_field.endswith('_id'):
                                    level_conditions[f"{filter_identifier}.{element_field}"] = ObjectId(raw_val)
                                else:
                                    level_conditions[f"{filter_identifier}.{element_field}"] = raw_val

                    if level_conditions:
                        array_filters.append(level_conditions)

                pull_path = '.'.join(pull_path_parts + [path_parts[-1]])

                self.db[parent_collection].update_one(
                    primary_filters,
                    {"$pull": {pull_path: removal_criteria}},
                    array_filters=array_filters
                )
            else:
                self.db[parent_collection].update_one(
                    primary_filters,
                    {"$pull": {embedded_path: removal_criteria}}
                )
        else:
            self.db[parent_collection].delete_one(
                {'_id': ObjectId(input_object.raw_attributes['id'])}
            )

    def get_related(self, input_object, related_class, skip_to=None):
        relation = model_relations.get(input_object.__class__).get(related_class)

        if relation is None:
            raise ValueError("No relation found between the provided classes")

        if relation[0] == RelationDirection.OWNER:
            nested_array = relation[1]
            result = input_object.raw_attributes.get(nested_array)
            if result is None:
                logger.warning("Embedded object was not returned with the parent object")
                return []

            result = [self.mongo_to_model(related_class, item) for item in result]
        elif relation[0] == RelationDirection.EMBEDDED:
            filters = {}
            primary_key_dict = relation[1]

            for local, foreign in primary_key_dict.items():
                if local in self.model_to_mongo(input_object.raw_attributes):
                    if foreign == '_id' or foreign.endswith('_id'):
                        filters[foreign] = ObjectId(input_object.raw_attributes[local])
                    else:
                        filters[foreign] = input_object.raw_attributes[local]

            result = self.get_list(related_class, filters=filters)
        elif relation[0] == RelationDirection.REFERENCE:
            filters = {}
            primary_key_dict = relation[1]

            for local, foreign in primary_key_dict.items():
                if local in input_object.raw_attributes:
                    if local.endswith('_id'):
                        filters[foreign] = ObjectId(input_object.raw_attributes[local])
                    else:
                        filters[foreign] = input_object.raw_attributes[local]

            result = self.get_list(related_class, filters=filters)

        elif relation[0] == RelationDirection.REFERENCED_BY:
            filters = {}
            primary_key_dict = relation[1]

            for foreign, local in primary_key_dict.items():
                if local in self.model_to_mongo(input_object.raw_attributes):
                    if local.endswith('_id'):
                        filters[foreign] = ObjectId(input_object.raw_attributes[local])
                    else:
                        filters[foreign] = input_object.raw_attributes[local]

            result = self.get_list(related_class, filters=filters)
        else:
            raise AssertionError("Unhandled relation direction in get_related")

        if skip_to is not None:
            intermediate_results = []
            for item in result:
                intermediate_related = self.get_related(item, skip_to)
                intermediate_results.extend(intermediate_related)
            return intermediate_results
        return result

    def update(self, input_object):
        collection_info = model_collection_mapping.get(input_object.__class__)

        if not collection_info:
            raise ValueError(f"No collection mapping found for model class {input_object.__class__}")

        parent_collection = collection_info[0]
        embedded_path = collection_info[1]

        data = input_object.raw_attributes

        if embedded_path:
            primary_filters = {}
            for key, value in collection_info[2].items():
                if key in data:
                    if value == '_id' or key.endswith('_id'):
                        primary_filters[value] = ObjectId(data[key])
                    else:
                        primary_filters[value] = data[key]

            path_parts = embedded_path.split('.')
            is_nested = len(path_parts) > 1

            if is_nested:
                array_filters = []
                filter_path_parts = []

                for i, part in enumerate(path_parts):
                    filter_identifier = f"elem{i}"
                    filter_path_parts.append(f"{part}.$[{filter_identifier}]")

                    level_conditions = {}

                    for key, value in collection_info[2].items():
                        if key in data and value != '_id':
                            value_parts = value.split('.')
                            if len(value_parts) == i + 2 and value_parts[:i+1] == path_parts[:i+1]:
                                element_field = value_parts[-1]
                                raw_val = data[key]
                                if element_field == '_id' or element_field.endswith('_id'):
                                    level_conditions[f"{filter_identifier}.{element_field}"] = ObjectId(raw_val)
                                else:
                                    level_conditions[f"{filter_identifier}.{element_field}"] = raw_val

                    for key, value in collection_info[3].items():
                        if key in data:
                            value_parts = value.split('.')
                            if len(value_parts) == i + 2 and value_parts[:i+1] == path_parts[:i+1]:
                                element_field = value_parts[-1]
                                raw_val = data[key]
                                if element_field == '_id' or element_field.endswith('_id'):
                                    level_conditions[f"{filter_identifier}.{element_field}"] = ObjectId(raw_val)
                                else:
                                    level_conditions[f"{filter_identifier}.{element_field}"] = raw_val

                    if level_conditions:
                        array_filters.append(level_conditions)

                update_path = '.'.join(filter_path_parts)
                update_fields = {}
                for key, val in data.items():
                    if key not in collection_info[2] and key not in collection_info[3]:
                        field_path = f"{update_path}.{key}"
                        if key.endswith('_id'):
                            update_fields[field_path] = ObjectId(val)
                        else:
                            update_fields[field_path] = val


                self.db[parent_collection].update_one(
                    primary_filters,
                    {"$set": update_fields},
                    array_filters=array_filters
                )
            else:
                update_fields = {}
                for key, val in data.items():
                    if key not in collection_info[2] and key not in collection_info[3]:
                        field_path = f"{embedded_path}.$.{key}"
                        if key.endswith('_id'):
                            update_fields[field_path] = ObjectId(val)
                        else:
                            update_fields[field_path] = val

                full_filter = primary_filters.copy()
                for key, value in collection_info[3].items():
                    if key in data:
                        element_field = value.split('.')[-1]
                        raw_val = data[key]
                        if element_field == '_id' or key.endswith('_id') or element_field.endswith('_id'):
                            full_filter[value] = ObjectId(raw_val)
                        else:
                            full_filter[value] = raw_val

                self.db[parent_collection].update_one(
                    full_filter,
                    {"$set": update_fields}
                )
        else:
            doc_id = ObjectId(data.get('id') or data.get('_id'))
            update_data = {k: v for k, v in data.items() if k not in ['id', '_id']}

            self.db[parent_collection].update_one(
                {"_id": doc_id},
                {"$set": update_data}
            )

    def __init__(self, mongo_uri, app=None):
        self.mongo = PyMongo(app, uri=mongo_uri)
        self.db = self.mongo.cx.get_default_database()

        logger.debug("Connected to MongoDB at %s", mongo_uri)

    def drop_all_collections(self):
        for collection_info in model_collection_mapping.values():
            parent_collection = collection_info[0]
            self.db[parent_collection].drop()
            logger.debug("Dropped collection %s", parent_collection)

    def initialize_database(self):
        pass

    def get_subclass(self, source_object, subclass):
        try:
            subclass.validate(source_object.raw_attributes)
            return subclass(source_object.raw_attributes)
        except ValueError:
            return None

    def get_raw_db(self):
        return self.db