import random

from flask import Blueprint, render_template, jsonify, current_app, redirect, url_for, request, session

import middleware
from db.models import Book
from db.models.Highlight import Highlight
from db.models.Shelf import Shelf
from db.models.ShelfBook import ShelfBook
from db.models.User import User

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/debug-many-to-many-manual')
def many_to_many_manual():
    user = current_app.db.get_by_id(User, 4)

    shelves = current_app.db.get_related(user, Shelf)
    result = []

    for shelf in shelves:
        shelf_dict = shelf.to_dict()
        shelf_books = current_app.db.get_related(shelf, ShelfBook)
        shelf_books_list = []

        for shelf_book in shelf_books:
            book = current_app.db.get_related(shelf_book, Book)[0]
            shelf_books_list.append({
                'shelf_book': shelf_book.to_dict(),
                'book': book.to_dict()
            })

        shelf_dict['shelf_book'] = shelf_books_list
        result.append(shelf_dict)

    user_dict = user.to_dict()
    user_dict['shelves'] = [ shelf.to_dict() for shelf in shelves]
    return jsonify({"message": "test123", "result": result, "user": user_dict})

@debug_bp.route('/debug-many-to-many-skip')
def many_to_many_skip():
    user = current_app.db.get_by_id(User, 4)

    shelves = current_app.db.get_related(user, Shelf)
    result = []

    for shelf in shelves:
        shelf_dict = shelf.to_dict()
        shelf_books = current_app.db.get_related(shelf, ShelfBook, skip_to=Book)

        shelf_dict['books'] = [book.to_dict() for book in shelf_books]
        result.append(shelf_dict)

    user_dict = user.to_dict()
    user_dict['shelves'] = [ shelf.to_dict() for shelf in shelves]
    return jsonify({"message": "test123", "result": result, "user": user_dict})

@debug_bp.route('/debug-get-list-shelves')
def get_list_shelves():
    shelves = current_app.db.get_list(User)

    return jsonify({"message": "test123", "shelves": [shelf.to_dict() for shelf in shelves]})

@debug_bp.route('/current-user-details')
@middleware.require_auth
def current_user_details():
    user = current_app.auth.get_current_user()

    return jsonify({"message": "test123", "user": user.to_dict()})

@debug_bp.route('/current-user-shelves')
@middleware.require_auth
def current_user_shelves():
    user = current_app.auth.get_current_user()
    shelves = current_app.db.get_related(user, Shelf)

    return jsonify({"message": "test123", "shelves": [shelf.to_dict() for shelf in shelves]})

@debug_bp.route('/debug-shelf')
@middleware.require_auth
def debug_shelf():
    user = current_app.auth.get_current_user()
    shelf = current_app.db.get(Shelf, {'user_id': user.id, 'shelf_no': 1})

    if not shelf:
        return jsonify({"message": "Shelf not found"}), 404

    shelf_dict = shelf.to_dict()

    books = current_app.db.get_related(shelf, ShelfBook, skip_to=Book)
    books_dict = []
    for book in books:
        book_dict = book.to_dict()
        progress_entry = current_app.db.get(ShelfBook, {'user_id': user.id, 'shelf_no': shelf.shelf_no, 'book_id': book.id})
        if progress_entry:
            book_dict['progress'] = progress_entry.progress
        books_dict.append(book_dict)

    shelf_user = current_app.db.get_related(shelf, User)

    return jsonify({"message": "test123", "shelf": shelf_dict, "books": books_dict, "shelf_user": [ user.to_dict() for user in shelf_user]})

@debug_bp.route('/update-shelf')
@middleware.require_auth
def update_shelf():
    user = current_app.auth.get_current_user()
    shelf = current_app.db.get(Shelf, {'user_id': user.id, 'shelf_no': 1})

    if not shelf:
        return jsonify({"message": "Shelf not found"}), 404

    shelf.background_url = "https://example.com/new_background.jpg?updated"
    shelf.color = "#{:06x}".format(random.randint(0, 0xFFFFFF))

    current_app.db.update(shelf)

    shelf = current_app.db.get(Shelf, {'user_id': user.id, 'shelf_no': 1})

    return jsonify({"message": "Shelf updated", "shelf": shelf.to_dict()})

@debug_bp.route('/init-books')
@middleware.require_auth
def init_books():
    user = current_app.auth.get_current_user()
    shelf = current_app.db.get(Shelf, {'user_id': user.id, 'shelf_no': 1})

    if not shelf:
        return jsonify({"message": "Shelf not found"}), 404

    for i in range(5):
        book_properties = {
            'title': f"Debug Book {i+1}",
            'isbn': f"1010101010",
            'cover_url': f"https://example.com/debug_book_{i+1}.jpg",
            'year': 2024,
            'genre': "Debug",
            'source': "Debug Source"
        }

        new_book = Book(book_properties)
        current_app.db.insert(new_book)

        inserted_book = current_app.db.get_list(Book, book_properties)[0]
        new_shelf_book = ShelfBook({
            'user_id': user.id,
            'shelf_no': shelf.shelf_no,
            'book_id': inserted_book.id,
            'progress': 0
        })
        current_app.db.insert(new_shelf_book)

    return jsonify({"message": "Initialized 5 debug books in shelf 1"})