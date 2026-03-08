from bson import ObjectId
from flask import Blueprint, render_template, session, current_app, url_for, redirect, request
from werkzeug.exceptions import NotFound, BadRequest

import middleware
from db.MongoDBProvider import MongoDBProvider
from db.MySQLProvider import MySQLProvider
from db.factories.ShelfBookFactory import ShelfBookFactory
from db.factories.ShelfFactory import ShelfFactory
from db.models import User
from db.models.Book import Book
from db.models.Shelf import Shelf

books_bp = Blueprint('books', __name__)

@books_bp.route('/<int:shelf_no>/read/<string:book_id>')
@middleware.require_auth
def read_book(shelf_no, book_id):
    user = current_app.auth.get_current_user()

    if isinstance(current_app.db, MySQLProvider):
        query = f"""
        SELECT sb.progress, sb.shelf_no, b.*
        FROM shelf_books sb
        JOIN books b ON sb.book_id = b.id
        JOIN shelves s ON sb.shelf_no = s.shelf_no AND sb.user_id = {user.id}
        WHERE s.shelf_no = {shelf_no} AND s.user_id = {user.id} AND b.id = '{book_id}';
        """

        result = current_app.db.execute_query(query)
        if not result:
            raise NotFound()

        book_data = result[0]
        book = Book({
            'id': book_data['id'],
            'title': book_data['title'],
            'author': book_data['author'],
            'genre': book_data['genre'],
            'cover_url': book_data['cover_url'],
            'source': book_data['source'],
            'year': book_data['year'],
        })
        progress = book_data['progress']
    else:
        pipeline = [
            {'$match': {'_id': user.id}},
            {'$unwind': '$shelves'},
            {'$match': {'shelves.shelf_no': shelf_no}},
            {'$unwind': '$shelves.books'},
            {'$match': {'shelves.books.book_id': ObjectId(book_id)}},
            {'$lookup': {
                'from': 'books',
                'localField': 'shelves.books.book_id',
                'foreignField': '_id',
                'as': 'book_details'
            }},
            {'$unwind': '$book_details'},
            {'$project': {
                'progress': '$shelves.books.progress',
                'shelf_no': '$shelves.shelf_no',
                'book': '$book_details'
            }}
        ]

        result = list(current_app.db.get_raw_db()['users'].aggregate(pipeline))
        if not result:
            raise NotFound()

        data = result[0]
        book = MongoDBProvider.mongo_to_model(Book, data['book'])
        progress = data['progress']

    return render_template("books/read.html", book=book.to_dict(), shelf_no=shelf_no, progress=progress)

@books_bp.route('/')
@books_bp.route('/<int:shelf_no>')
@middleware.require_auth
def browse(shelf_no=None):
    books = current_app.db.get_list(Book)
    books_dict = []
    for book in books:
        book_dict = book.to_dict()
        books_dict.append(book_dict)

    user = current_app.auth.get_current_user()

    shelf = None
    if shelf_no is None:
        for book_dict in books_dict:
            book_dict['owned'] = False
        return render_template("books/browse.html", books=books_dict, shelf=shelf)

    if isinstance(current_app.db, MongoDBProvider):
        pipeline = [
            {'$match': {'_id': user.id}},
            {'$unwind': '$shelves'},
            {'$match': {'shelves.shelf_no': shelf_no}},
            {'$project': {
                'shelf': '$shelves',
                'book_ids': {
                    '$ifNull': [
                        {'$map': {'input': '$shelves.books', 'as': 'b', 'in': '$$b.book_id'}},
                        []
                    ]
                },
                'owned_books': {
                    '$setUnion': [
                        {'$ifNull': [
                            {'$map': {'input': '$shelves.books', 'as': 'b', 'in': '$$b.book_id'}},
                            []
                        ]},
                        []
                    ]
                }
            }}
        ]

        result = list(current_app.db.get_raw_db()['users'].aggregate(pipeline))
        if not result:
            raise NotFound()

        shelf = MongoDBProvider.mongo_to_model(Shelf, result[0]['shelf'])
        owned_book_ids = {str(_id) for _id in result[0]['owned_books']}

        for book_dict in books_dict:
            book_dict['owned'] = str(book_dict['id']) in str(owned_book_ids)
    else:
        query = f"""
        SELECT sb.shelf_no, sb.book_id, s.*
        FROM shelf_books sb
        JOIN shelves s ON sb.shelf_no = s.shelf_no AND sb.user_id = {user.id}
        WHERE s.user_id = {user.id} AND sb.shelf_no = {shelf_no};
        """

        results = current_app.db.execute_query(query)
        if not results:
            shelf = current_app.db.get(Shelf, {'shelf_no': shelf_no, 'user_id': user.id})
        else:
            shelf = ShelfFactory.create_shelf(
                db=current_app.db,
                shelf_no=shelf_no,
                background_url=results[0]['background_url'],
                color=results[0]['color'],
                user_id=user.id
                )

        owned_book_ids = {row['book_id'] for row in results}
        for book_dict in books_dict:
            book_dict['owned'] = book_dict['id'] in owned_book_ids

    return render_template("books/browse.html", books=books_dict, shelf=shelf)

@books_bp.route('/<int:shelf_no>/add/<string:book_id>', methods=['POST'])
@middleware.require_auth
def add_to_shelf(shelf_no, book_id):
    user = current_app.auth.get_current_user()
    book = current_app.db.get_by_id(Book, book_id)
    if not book:
        raise NotFound("Book not found")

    if isinstance(current_app.db, MongoDBProvider):
        db = current_app.db.get_raw_db()

        # checks for duplicates and inserts only if not present
        db.users.update_one(
            {
                "_id": user.id,
                "shelves.shelf_no": shelf_no,
                "shelves.books.book_id": {"$ne": ObjectId(book_id)}
            },
            {
                "$push": {
                    "shelves.$.books": {
                        "book_id": ObjectId(book_id),
                        "progress": 0,
                        "title": book.title,
                        "author": book.author,
                        "cover_url": book.cover_url
                    }
                }
            }
        )

    else:
        query = f"""
        SELECT sb.shelf_no, sb.book_id, s.*
        FROM shelf_books sb
        JOIN shelves s ON sb.shelf_no = s.shelf_no AND sb.user_id = {user.id}
        WHERE s.user_id = {user.id} AND sb.shelf_no = {shelf_no} AND sb.book_id = {book_id};
        """

        found = current_app.db.execute_query(query)
        if not found:
            shelfbook = ShelfBookFactory.create_shelf(
                db=current_app.db,
                shelf_no=shelf_no,
                book_id=book_id,
                user_id=user.id
            )

            current_app.db.insert(shelfbook)

    return redirect(url_for('shelves.shelf', shelf_no=shelf_no))

@books_bp.route('/<int:shelf_no>/remove/<string:book_id>', methods=['POST'])
@middleware.require_auth
def remove_from_shelf(shelf_no, book_id):
    user = current_app.auth.get_current_user()

    if isinstance(current_app.db, MongoDBProvider):
        db = current_app.db.get_raw_db()

        db.users.update_one(
            {
                "_id": user.id,
                "shelves.shelf_no": shelf_no
            },
            {
                "$pull": {
                    "shelves.$.books": {
                        "book_id": ObjectId(book_id)
                    }
                }
            }
        )

    else:
        query = f"""
                DELETE
                FROM shelf_books
                WHERE user_id = {user.id}
                  AND shelf_no = {shelf_no}
                  AND book_id = {book_id}
                """

        current_app.db.execute_query(query)

    return redirect(url_for('shelves.shelf', shelf_no=shelf_no))

@books_bp.route('/<int:shelf_no>/update-progress/<string:book_id>', methods=['POST'])
@middleware.require_auth
def update_progress(shelf_no, book_id):
    try:
        new_progress = float(request.json.get('progress'))
        new_reading_speed = float(request.json.get('reading_speed'))
    except ValueError:
        raise BadRequest("Invalid progress or reading speed value")

    if new_progress < 0 or new_progress > 100:
        raise BadRequest("Progress must be between 0 and 100")

    response, status_code = usecase_update_progress(shelf_no, book_id, new_reading_speed, new_progress)
    return response, status_code

@books_bp.route('/details/<string:book_id>')
@middleware.require_auth
def details(book_id):
    book = current_app.db.get_by_id(Book, book_id)
    if not book:
        raise NotFound()

    return render_template("books/details.html", book=book.to_dict())

def usecase_update_progress(shelf_no, book_id, new_reading_speed, new_progress, user_id = None):
    if user_id is None:
        user = current_app.auth.get_current_user()
    else:
        user = current_app.db.get_by_id(User, user_id)
        if not user:
            raise NotFound("User not found")

    if isinstance(current_app.db, MongoDBProvider):
        db = current_app.db.get_raw_db()

        current_book_pipeline = [
            {'$match': {'_id': user.id}},
            {'$unwind': '$shelves'},
            {'$match': {'shelves.shelf_no': shelf_no}},
            {'$unwind': '$shelves.books'},
            {'$match': {'shelves.books.book_id': ObjectId(book_id)}},
            {'$project': {'current_progress': '$shelves.books.progress'}}
        ]

        current_book_result = list(db.users.aggregate(current_book_pipeline))
        current_book_progress = float(current_book_result[0]['current_progress']) if current_book_result else 0.0

        progress_difference = new_progress - current_book_progress

        all_books_pipeline = [
            {'$match': {'_id': user.id}},
            {'$unwind': '$shelves'},
            {'$unwind': '$shelves.books'},
            {'$group': {
                '_id': '$_id',
                'total_progress_all_books': {'$sum': '$shelves.books.progress'}
            }}
        ]

        all_books_result = list(db.users.aggregate(all_books_pipeline))
        total_progress_all_books = float(all_books_result[0]['total_progress_all_books']) if all_books_result else 0.0

        # r = (p_beta * r_n + r_o * sum(p_b for all b in B)) / (p_beta + sum(p_b for all b in B))
        old_reading_speed = float(user.reading_speed) if user.reading_speed else 0.0
        updated_reading_speed = (progress_difference * new_reading_speed + old_reading_speed * total_progress_all_books) / (progress_difference + total_progress_all_books) if (progress_difference + total_progress_all_books) > 0 else new_reading_speed

        db.users.update_one(
            {
                "_id": user.id,
                "shelves.shelf_no": shelf_no,
                "shelves.books.book_id": ObjectId(book_id)
            },
            {
                "$set": {
                    "shelves.$[shelf].books.$[book].progress": new_progress
                }
            },
            array_filters=[
                {"shelf.shelf_no": shelf_no},
                {"book.book_id": ObjectId(book_id)}
            ]
        )

        db.users.update_one(
            {"_id": user.id},
            {"$set": {"reading_speed": updated_reading_speed}}
        )

    else:
        current_progress_query = f"""
        SELECT sb.progress as current_progress
        FROM shelf_books sb
        JOIN shelves s ON sb.shelf_no = s.shelf_no AND sb.user_id = s.user_id
        WHERE sb.user_id = {user.id} AND sb.shelf_no = {shelf_no} AND sb.book_id = '{book_id}';
        """

        current_result = current_app.db.execute_query(current_progress_query)
        current_book_progress = float(current_result[0]['current_progress']) if current_result else 0.0

        progress_difference = new_progress - current_book_progress

        total_progress_query = f"""
        SELECT COALESCE(SUM(sb.progress), 0) as total_progress_all_books
        FROM shelf_books sb
        JOIN shelves s ON sb.shelf_no = s.shelf_no AND sb.user_id = s.user_id
        WHERE sb.user_id = {user.id};
        """

        total_result = current_app.db.execute_query(total_progress_query)
        total_progress_all_books = float(total_result[0]['total_progress_all_books']) if total_result else 0.0

        # r = (p_beta * r_n + r_o * sum(p_b for all b in B)) / (p_beta + sum(p_b for all b in B))
        old_reading_speed = float(user.reading_speed) if user.reading_speed else 0.0
        updated_reading_speed = (progress_difference * new_reading_speed + old_reading_speed * total_progress_all_books) / (progress_difference + total_progress_all_books) if (progress_difference + total_progress_all_books) > 0 else new_reading_speed

        progress_query = f"""
        UPDATE shelf_books sb
        JOIN shelves s ON sb.shelf_no = s.shelf_no AND sb.user_id = s.user_id
        SET sb.progress = {new_progress}
        WHERE sb.user_id = {user.id}
          AND sb.shelf_no = {shelf_no}
          AND sb.book_id = '{book_id}'
          AND s.user_id = {user.id};
        """

        current_app.db.execute_query(progress_query)

        user_update_query = f"""
        UPDATE users
        SET reading_speed = {updated_reading_speed}
        WHERE id = {user.id};
        """

        current_app.db.execute_query(user_update_query)

    return {"message": "Reading speed updated", "new_reading_speed": updated_reading_speed, "old_reading_speed": old_reading_speed}, 200