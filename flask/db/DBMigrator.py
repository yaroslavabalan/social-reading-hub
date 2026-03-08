import logging
from decimal import Decimal

from bson import ObjectId
from flask import current_app
from pymongo import UpdateOne

from db.DBProvider import DBProvider
from db.MongoDBProvider import MongoDBProvider
from db.models.Follower import Follower
from db.models.Shelf import Shelf
from db.models.Book import Book
from db.models.Post import Post
from db.models.ShelfBook import ShelfBook
from db.models.Comment import Comment
from db.models.Discussion import Discussion
from db.models.Highlight import Highlight
from db.models.User import User

logger = logging.getLogger(__name__)

class DBMigrator:
    def __init__(self, mysql, mongodb):
        if not isinstance(mongodb, MongoDBProvider) or not isinstance(mysql, DBProvider):
            raise ValueError("Invalid database providers supplied to DBMigrator")

        self.mysql = mysql
        self.mongodb = mongodb

        self.mongodb.drop_all_collections()

    def migrate(self):
        book_mapping = {}
        user_mapping = {}

        books = self.mysql.get_list(Book)
        for book in books:
            book_mapping[book.id] = ObjectId()
            book.id = book_mapping[book.id]
            self.mongodb.insert(book)

        users = self.mysql.get_list(User)
        for user in users:
            old_user_id = user.id
            new_user_id = ObjectId()
            user_mapping[old_user_id] = new_user_id

            shelves = self.mysql.get_related(user, Shelf)

            user.id = new_user_id
            self.mongodb.insert(user)

            for shelf in shelves:
                shelf_books = self.mysql.get_related(shelf, ShelfBook)
                shelf.raw_attributes['user_id'] = user_mapping.get(shelf.raw_attributes['user_id'], new_user_id)
                self.mongodb.insert(shelf)
                for shelf_book in shelf_books:
                    shelf_book.raw_attributes['user_id'] = user_mapping.get(shelf_book.raw_attributes['user_id'],
                                                                            new_user_id)
                    shelf_book.shelf_no = shelf.shelf_no
                    old_book_id = shelf_book.raw_attributes['book_id']
                    shelf_book.raw_attributes['book_id'] = book_mapping[old_book_id]

                    book = self.mysql.get_by_id(Book, old_book_id)
                    if book:
                        shelf_book.raw_attributes['title'] = book.raw_attributes.get('title', '')
                        shelf_book.raw_attributes['author'] = book.raw_attributes.get('author', '')
                        shelf_book.raw_attributes['cover_url'] = book.raw_attributes.get('cover_url', '')

                    if 'progress' in shelf_book.raw_attributes and isinstance(shelf_book.raw_attributes['progress'],
                                                                              Decimal):
                        shelf_book.raw_attributes['progress'] = float(shelf_book.raw_attributes['progress'])

                    self.mongodb.insert(shelf_book)

        followings = self.mysql.get_list(Follower)
        for follow in followings:
            follower_id_old = follow.raw_attributes.get('follower_id')
            followee_id_old = follow.raw_attributes.get('followee_id')

            mapped_follower_id = user_mapping.get(follower_id_old)
            mapped_followee_id = user_mapping.get(followee_id_old)

            self.mongodb.get_raw_db().users.bulk_write([
                UpdateOne(
                    {"_id": mapped_follower_id},
                    {"$addToSet": {"following": mapped_followee_id}}
                ),
                UpdateOne(
                    {"_id": mapped_followee_id},
                    {"$addToSet": {"followers": mapped_follower_id}}
                )
            ])

        highlight_mapping = {}

        highlights = self.mysql.get_list(Highlight)
        for highlight in highlights:
            highlight_raw = highlight.raw_attributes.copy()
            highlight_raw['user_id'] = user_mapping[highlight_raw['user_id']]
            highlight_raw['book_id'] = book_mapping[highlight_raw['book_id']]

            post = self.mysql.get_related(highlight, Post)
            discussion = self.mysql.get_related(highlight, Discussion)

            highlight_mapping[highlight_raw['id']] = ObjectId()
            highlight_raw['id'] = highlight_mapping[highlight_raw['id']]

            if len(self.mysql.get_related(highlight, Post)) > 0:
                highlight_raw['type'] = 'post'
                highlight_raw['description'] = post[0].description
                highlight_raw['background'] = post[0].background
            elif len(self.mysql.get_related(highlight, Discussion)) > 0:
                highlight_raw['type'] = 'discussion'
                highlight_raw['visibility'] = discussion[0].visibility
                highlight_raw['locked'] = discussion[0].locked if discussion[0].locked else False

            new_highlight = Highlight(highlight_raw)
            self.mongodb.insert(new_highlight)

        comments = self.mysql.get_list(Comment)
        for comment in comments:
            comment_attributes = comment.raw_attributes.copy()
            old_user_id = comment_attributes['user_id']
            comment_attributes['user_id'] = user_mapping.get(old_user_id)
            comment_attributes['discussion_id'] = highlight_mapping.get(comment_attributes['discussion_id'])
            comment_attributes['id'] = ObjectId()

            user = self.mysql.get_by_id(User, old_user_id)
            if user:
                comment_attributes['name'] = user.raw_attributes.get('name', '')
                comment_attributes['email'] = user.raw_attributes.get('email', '')

            self.mongodb.insert(Comment(comment_attributes))

        current_app.db = self.mongodb
        logger.debug("Migration successful")