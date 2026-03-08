import logging
from enum import Enum

import pymysql
import os

import time
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
    OWNER = 'owner'
    REFERENCE = 'reference'

# Mapping of model classes to their corresponding database table names.
model_table_mapping = {
    User: "users",
    Book: "books",
    Shelf: "shelves",
    Discussion: "discussions",
    Post: "posts",
    ShelfBook: "shelf_books",
    Comment: "comments",
    Highlight: "highlights",
    Follower: "follows",
    Follows: "follows",
}

# Mapping of model classes to their primary key attributes.
model_primary_keys_mapping = {
    User: ['id'],
    Book: ['id'],
    Shelf: ['shelf_no', 'user_id'],
    Discussion: ['id'],
    Post: ['id'],
    ShelfBook: ['shelf_no', 'user_id', 'book_id'],
    Comment: ['id'],
    Highlight: ['id'],
    Follower: ['follower_id', 'followee_id'],
    Follows: ['follower_id', 'followee_id'],
}

"""
Define the relationships between models.

Each entry maps a model class to a dictionary where:
- The keys are related model classes.
- The values are tuples containing:
    - RelationDirection (OWNER or REFERENCE),
        OWNER means the local model owns the related model and thus does not have a reference to it
        REFERENCE means the local model references the related model via foreign keys.
    - A dictionary mapping local attributes to foreign attributes for establishing the relationship.
        The structure is always - local key : foreign key
"""
model_relations = {
    User: {
        Shelf: (RelationDirection.OWNER, {'id': 'user_id'}),
        Highlight: (RelationDirection.OWNER, {'id': 'user_id'}),
        Comment: (RelationDirection.OWNER, {'id': 'user_id'}),
        Follows: (RelationDirection.OWNER, {'id': 'follower_id'}),
        Follower: (RelationDirection.OWNER, {'id': 'followee_id'}),
    },
    Follows: {
        User: (RelationDirection.REFERENCE, {'followee_id': 'id'}),
    },
    Follower: {
        User: (RelationDirection.REFERENCE, {'follower_id': 'id'}),
    },
    Shelf: {
        User: (RelationDirection.REFERENCE, {'user_id': 'id'}),
        ShelfBook: (RelationDirection.OWNER, {'shelf_no': 'shelf_no', 'user_id': 'user_id'}),
    },
    Comment: {
        Discussion: (RelationDirection.REFERENCE, {'discussion_id': 'id'}),
        User: (RelationDirection.REFERENCE, {'user_id': 'id'}),
    },
    Discussion: {
        Comment: (RelationDirection.OWNER, {'id': 'discussion_id'}),
        Highlight: (RelationDirection.REFERENCE, {'id': 'id'}),
    },
    Highlight: {
        User: (RelationDirection.REFERENCE, {'user_id': 'id'}),
        Book: (RelationDirection.REFERENCE, {'book_id': 'id'}),
        Post: (RelationDirection.OWNER, {'id': 'id'}),
        Discussion: (RelationDirection.OWNER, {'id': 'id'}),
    },
    Book: {
        Highlight: (RelationDirection.OWNER, {'id': 'book_id'}),
        ShelfBook: (RelationDirection.OWNER, {'id': 'book_id'}),
    },
    ShelfBook: {
        Shelf: (RelationDirection.REFERENCE, {'shelf_no': 'shelf_no', 'user_id': 'user_id'}),
        Book: (RelationDirection.REFERENCE, {'book_id': 'id'}),
    },
    Post: {
        Highlight: (RelationDirection.REFERENCE, {'id': 'id'}),
    }
}

class MySQLProvider(DBProvider):
    def __init__(self, db_configuration):
        logger.debug("Initializing MySQLProvider with configuration: %s", db_configuration)

        self.db_configuration = db_configuration
        self.mysql = None
        
        retries = 30
        while retries > 0:
            try:
                self.mysql = pymysql.connect(
                    host=db_configuration['MYSQL_HOST'],
                    port=db_configuration['MYSQL_PORT'],
                    user=db_configuration['MYSQL_USER'],
                    passwd=db_configuration['MYSQL_PASSWORD'],
                )
                break
            except pymysql.MySQLError as e:
                retries -= 1
                logger.warning(f"Failed to connect to MySQL: {e}. Retrying in 2 seconds... ({retries} retries left)")
                time.sleep(2)
        
        if self.mysql is None:
             raise Exception("Could not connect to MySQL after multiple retries.")

        self.mysql.autocommit(True)


    def initialize_database(self):
        cursor = self.mysql.cursor()

        logger.debug("Creating MySQL database if not exists...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.db_configuration['MYSQL_DB']}`")
        self.mysql.select_db(self.db_configuration['MYSQL_DB'])
        self.mysql.commit()

        cursor.close()

        logger.debug("DB selected: %s", self.db_configuration['MYSQL_DB'])

        cursor = self.mysql.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        cursor.close()


        if not tables:
            logger.debug("No tables found in database. Creating tables...")
            cursor.close()
            sql_file_path = os.path.join(os.path.dirname(__file__), 'db_create_tables.sql')
            self.execute_sql_file(sql_file_path)
        else:
            logger.debug("Database already initialized with tables.")


    def execute_sql_file(self, file_path):
        cursor = self.mysql.cursor()

        logger.debug("Executing SQL file %s", file_path)

        try:
            with open(file_path, 'r') as sql_file:
                sql_content = sql_file.read()

            statements = sql_content.split(';')

            for statement in statements:
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)

            self.mysql.commit()
            logger.info(f"Successfully executed SQL file: {file_path}")

        except Exception as e:
            self.mysql.rollback()
            logger.error(f"Error executing SQL file {file_path}: {e}")
            raise
        finally:
            cursor.close()


    def get_list(self, model_class, filters=None):
        table_name = model_table_mapping.get(model_class)
        if not table_name:
            raise ValueError(f"No table mapping found for model class {model_class}")

        cursor = self.mysql.cursor(pymysql.cursors.DictCursor)
        query = f"SELECT * FROM {table_name}"
        params = []
        if filters:
            filter_clauses = []
            for key, value in filters.items():
                filter_clauses.append(f"{key}=%s")
                params.append(value)
            query += " WHERE " + " AND ".join(filter_clauses)
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()

        return [model_class(data) for data in results]

    def insert(self, input_object):
        table_name = model_table_mapping.get(input_object.__class__)

        if not table_name:
            raise ValueError(f"No table mapping found for model class {input_object.__class__}")

        data = input_object.raw_attributes

        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        values = list(data.values())

        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        cursor = self.mysql.cursor()
        logger.debug("Inserting into table %s", table_name)
        logger.debug(query)
        logger.debug(values)
        cursor.execute(query, values)
        self.mysql.commit()
        cursor.close()

        return cursor.lastrowid


    def delete(self, input_object):
        table_name = model_table_mapping.get(input_object.__class__)

        if not table_name:
            raise ValueError(f"No table mapping found for model class {input_object.__class__}")

        data = input_object.raw_attributes

        non_none_items = [(col, val) for col, val in data.items() if val is not None]
        if not non_none_items:
            raise ValueError("No non-null attributes provided for delete")

        where_clause = ' AND '.join([f"{col}=%s" for col, _ in non_none_items])
        values = [val for _, val in non_none_items]

        query = f"DELETE FROM {table_name} WHERE {where_clause}"
        cursor = self.mysql.cursor()
        cursor.execute(query, values)
        self.mysql.commit()
        cursor.close()


    def get_related(self, input_object, related_class, skip_to=None):

        relation_properties = model_relations.get(input_object.__class__).get(related_class)

        logger.debug("input_object: %s", input_object)
        logger.debug("related_class: %s", related_class)

        result = []

        if relation_properties[0] == RelationDirection.OWNER:
            unique_filters = dict()

            for local, foreign in relation_properties[1].items():
                unique_filters[foreign] = input_object.raw_attributes[local]

            result = self.get_list(related_class, unique_filters)
        elif relation_properties[0] == RelationDirection.REFERENCE:
            unique_filters = dict()

            for local, foreign in relation_properties[1].items():
                unique_filters[foreign] = input_object.raw_attributes[local]

            result = self.get_list(related_class, unique_filters)

        if related_class.is_junction_table() and skip_to:
            final_results = []
            for rel in result:
                related_objs = self.get_related(rel, skip_to)
                final_results.extend(related_objs)
            return final_results

        return result


    def update(self, input_object):
        table_name = model_table_mapping.get(input_object.__class__)

        if not table_name:
            raise ValueError(f"No table mapping found for model class {input_object.__class__}")

        data = input_object.raw_attributes

        primary_keys = model_primary_keys_mapping.get(input_object.__class__)
        if not primary_keys:
            raise ValueError(f"No primary key mapping found for model class {input_object.__class__}")

        set_clause = ', '.join([f"{col}=%s" for col in data.keys() if col not in primary_keys])
        where_clause = ' AND '.join([f"{col}=%s" for col in primary_keys])

        set_values = [data[col] for col in data.keys() if col not in primary_keys]
        where_values = [data[col] for col in primary_keys]

        query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
        cursor = self.mysql.cursor()
        cursor.execute(query, set_values + where_values)
        self.mysql.commit()
        cursor.close()

    def get_subclass(self, source_object, subclass):
        subclass_list = self.get_related(source_object, subclass)
        return subclass_list[0] if subclass_list else None

    def drop_all_collections(self):
        # todo: handle deletion of uploaded images

        cursor = self.mysql.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        cursor.execute("SET FOREIGN_KEY_CHECKS=0")

        for (table_name,) in tables:
            drop_query = f"DROP TABLE IF EXISTS {table_name}"
            cursor.execute(drop_query)
            logger.debug(f"Dropped table: {table_name}")

        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        self.mysql.commit()
        cursor.close()

        self.initialize_database()

    def execute_query(self, query, args = None):
        cursor = self.mysql.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query, args)
        results = cursor.fetchall()
        cursor.close()
        return results