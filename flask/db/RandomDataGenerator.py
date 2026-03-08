import logging
import random
from datetime import datetime

from bson import ObjectId
from flask import url_for
from pymongo import UpdateOne

from db.MongoDBProvider import MongoDBProvider
from db.MySQLProvider import MySQLProvider
from db.models import Book, Shelf, Post, Discussion
from db.models.Comment import Comment
from db.models.Follows import Follows
from db.models.Highlight import Highlight
from db.models.ShelfBook import ShelfBook
from db.models.User import User
from db.models.Follower import Follower
from faker import Faker

logger = logging.getLogger(__name__)

class RandomDataGenerator:
    def __init__(self, db, db_size = 100):
        self.db = db
        self.db_size = db_size

    def generate(self):
        self.db.drop_all_collections()
        faker = Faker()

        generated_emails = []
        generated_usernames = []

        for i in range(self.db_size // 5):
            email = faker.email()
            username = faker.user_name()

            while email in generated_emails or username in generated_usernames:
                email = faker.email()
                username = faker.user_name()

            generated_emails.append(email)
            generated_usernames.append(username)

            new_user = User({
                'name': username,
                'email': email,
                'reading_speed': faker.random_int(min=100, max=400)
            })
            self.db.insert(new_user)

        users = self.db.get_list(User)

        for i in range(self.db_size // 5):
            follower = random.choice(users)
            followee = random.choice(users)

            if follower.raw_attributes['id'] != followee.raw_attributes['id']:
                if isinstance(self.db, MongoDBProvider):
                    self.db.get_raw_db().users.bulk_write([
                        UpdateOne(
                            {"_id": follower.id},
                            {"$addToSet": {"following": ObjectId(followee.id)}}
                        ),
                        UpdateOne(
                            {"_id": followee.id},
                            {"$addToSet": {"followers": ObjectId(follower.id)}}
                        )
                    ])
                else:
                    query = """
                            INSERT INTO follows (follower_id, followee_id)
                            VALUES (%s, %s)
                            ON DUPLICATE KEY UPDATE follower_id=follower_id \
                            """

                    try:
                        self.db.execute_query(query, [
                            follower.id,
                            followee.id
                        ])
                    except Exception:
                        raise

        for user in users:
            for i in range(random.randint(1, 4)):
                shelf = Shelf({
                    'user_id': user.id,
                    'shelf_no': i,
                    'color': faker.hex_color(),
                })

                self.db.insert(shelf)

        self.db.insert(Book({
            'title': 'Frankenstein; Or, The Modern Prometheus',
            'author': 'Shelley, Mary Wollstonecraft, 1797-1851',
            'year': 1993,
            'cover_url': 'https://www.gutenberg.org/cache/epub/84/pg84.cover.medium.jpg',
            'source': url_for('book_source', filename='Frankenstein.html'),
            'genre': 'Horror',
            'project_gutenberg_no': 84
        }))

        self.db.insert(Book({
            'title': 'The Complete Works of William Shakespeare',
            'author': 'Shakespeare, William, 1564-1616',
            'year': 1994,
            'cover_url': 'https://www.gutenberg.org/cache/epub/100/pg100.cover.medium.jpg',
            'source': url_for('book_source', filename='Shakespear.html'),
            'genre': 'Drama',
            'project_gutenberg_no': 100
        }))

        self.db.insert(Book({
            'title': 'The Bible, King James version, Book 40: Matthew by Anonymous',
            'author': 'Anonymous',
            'year': 2005,
            'cover_url': 'https://www.gutenberg.org/cache/epub/8040/pg8040.cover.medium.jpg',
            'source': url_for('book_source', filename='Matthew.html'),
            'genre': 'Religion',
            'project_gutenberg_no': 8040
        }))

        self.db.insert(Book({
            'title': 'Romeo and Juliet',
            'author': 'Shakespeare, William, 1564-1616',
            'year': 1998,
            'cover_url': 'https://www.gutenberg.org/cache/epub/1513/pg1513.cover.medium.jpg',
            'source': url_for('book_source', filename='RomeoJuliet.html'),
            'genre': 'Drama',
            'project_gutenberg_no': 1513
        }))

        self.db.insert(Book({
            'title': 'Pride and Prejudice',
            'author': 'Austen, Jane, 1775-1817',
            'year': 1998,
            'cover_url': 'https://www.gutenberg.org/cache/epub/1342/pg1342.cover.medium.jpg',
            'source': url_for('book_source', filename='PridePrejudice.html'),
            'genre': 'Fiction',
            'project_gutenberg_no': 1342
        }))

        self.db.insert(Book({
            'title': 'The Great Gatsby',
            'author': 'Fitzgerald, F. Scott (Francis Scott), 1896-1940',
            'year': 2021,
            'cover_url': 'https://www.gutenberg.org/cache/epub/64317/pg64317.cover.medium.jpg',
            'source': url_for('book_source', filename='Gatsby.html'),
            'genre': 'Fiction',
            'project_gutenberg_no': 64317
        }))

        self.db.insert(Book({
            'title': 'Ulysses',
            'author': 'Joyce, James, 1882-1941',
            'year': 2003,
            'cover_url': 'https://www.gutenberg.org/cache/epub/4300/pg4300.cover.medium.jpg',
            'source': url_for('book_source', filename='Ulysses.html'),
            'genre': 'Fiction',
            'project_gutenberg_no': 4300
        }))

        self.db.insert(Book({
            'title': 'Science in the Kitchen',
            'author': 'Kellogg, E. E. (Ella Ervilla), 1853-1920',
            'year': 2004,
            'cover_url': 'https://www.gutenberg.org/cache/epub/12238/pg12238.cover.medium.jpg',
            'source': url_for('book_source', filename='KitchenScience.html'),
            'genre': 'Cooking',
            'project_gutenberg_no': 12238
        }))

        self.db.insert(Book({
            'title': 'Crime and Punishment',
            'author': 'Dostoyevsky, Fyodor, 1821-1881',
            'year': 2006,
            'cover_url': 'https://www.gutenberg.org/cache/epub/2554/pg2554.cover.medium.jpg',
            'source': url_for('book_source', filename='CrimePunishment.html'),
            'genre': 'Detective',
            'project_gutenberg_no': 2554
        }))

        books = self.db.get_list(Book)
        shelves = self.db.get_list(Shelf)

        for book in books:
            k = random.randint(1, len(shelves))
            chosen_shelves = random.sample(shelves, k)
            for shelf in chosen_shelves:
                shelfbook_properties = {
                    'book_id': book.id,
                    'shelf_no': shelf.raw_attributes['shelf_no'],
                    'user_id': shelf.raw_attributes['user_id'],
                    'progress': random.randint(0, 100),
                }

                if isinstance(self.db, MongoDBProvider):
                    shelfbook_properties['title'] = book.raw_attributes['title']
                    shelfbook_properties['author'] = book.raw_attributes['author']
                    shelfbook_properties['cover_url'] = book.raw_attributes['cover_url']

                self.db.insert(ShelfBook(shelfbook_properties))

        for i in range(self.db_size):
            user = random.choice(users)

            j = random.randint(1, 3)
            if j == 1:
                highlight = Highlight({
                    'user_id': user.id,
                    'book_id': random.choice(books).id,
                    'text': faker.sentence(nb_words=10),
                    'color': faker.hex_color(),
                    'timestamp': str(datetime.now()),
                })
                self.db.insert(highlight)
            elif j == 2:
                post_configuration = {
                    'user_id': user.id,
                    'book_id': random.choice(books).id,
                    'text': faker.sentence(nb_words=10),
                    'color': faker.hex_color(),
                    'description': faker.sentence(nb_words=6),
                    'background': 'bg' + str(random.randint(1,5)) + '.jpg',
                    'timestamp': str(datetime.now()),
                }

                if isinstance(self.db, MySQLProvider):
                    highlight_id = self.db.insert(Highlight({
                        'user_id': user.id,
                        'book_id': post_configuration['book_id'],
                        'text': post_configuration['text'],
                        'color': post_configuration['color'],
                        'timestamp': post_configuration['timestamp'],
                    }))

                    post_configuration['id'] = highlight_id
                    post = Post({
                        'id': post_configuration['id'],
                        'description': post_configuration['description'],
                        'background': post_configuration['background'],
                    })
                    self.db.insert(post)
                else:
                    post_configuration['type'] = 'post'
                    post = Post(post_configuration)
                    self.db.insert(post)
            else:
                discussion_configuration = {
                    'user_id': user.id,
                    'book_id': random.choice(books).id,
                    'text': faker.sentence(nb_words=10),
                    'color': faker.hex_color(),
                    'visibility': random.choice(['public', 'hidden']),
                    'locked': random.choice([True, False]),
                    'type': 'discussion',
                    'timestamp': str(datetime.now()),
                }

                if isinstance(self.db, MySQLProvider):
                    highlight_id = self.db.insert(Highlight({
                        'user_id': user.id,
                        'book_id': discussion_configuration['book_id'],
                        'text': discussion_configuration['text'],
                        'color': discussion_configuration['color'],
                        'timestamp': discussion_configuration['timestamp'],
                    }))

                    discussion_configuration['id'] = highlight_id
                    discussion = Discussion({
                        'id': discussion_configuration['id'],
                        'visibility': discussion_configuration['visibility'],
                        'locked': discussion_configuration['locked'],
                    })
                    self.db.insert(discussion)
                else:
                    discussion = Discussion(discussion_configuration)
                    self.db.insert(discussion)

        discussions = self.db.get_list(Discussion)
        for i in range(random.randint(0, self.db_size * 10)):
            commenter = random.choice(users)
            discussion = random.choice(discussions)

            comment = {
                'discussion_id': discussion.id,
                'user_id': commenter.id,
                'content': faker.sentence(nb_words=12),
                'timestamp': str(datetime.now()),
            }

            if isinstance(self.db, MongoDBProvider):
                comment['id'] = ObjectId()
                comment['name'] = commenter.raw_attributes['name']
                comment['email'] = commenter.raw_attributes['email']

            self.db.insert(Comment(comment))
