import os

from flask import Blueprint, render_template, session, current_app, redirect, url_for, request, flash
from werkzeug.exceptions import NotFound
from werkzeug.utils import secure_filename

import middleware
from db.MongoDBProvider import MongoDBProvider
from db.MySQLProvider import MySQLProvider
from db.factories.ShelfFactory import ShelfFactory
from db.models.Shelf import Shelf

shelves_bp = Blueprint('shelves', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

@shelves_bp.route('/')
@middleware.require_auth
def list():
    # mongodb: 1 query to get user, shelves are embedded inside user
    # mysql: 1 query to get user, 1 query to get shelves

    user = current_app.auth.get_current_user()
    shelves = current_app.db.get_related(user, Shelf)
    shelves_dict = []
    for shelf in shelves:
        shelf_dict = shelf.to_dict()
        shelves_dict.append(shelf_dict)

    return render_template("shelves/list.html", shelves=shelves_dict)

@shelves_bp.route('/<int:shelf_no>')
@middleware.require_auth
def shelf(shelf_no):
    # mongodb: 1 query to get user, 1 to get shelf with books (book details are embedded inside shelf because books don't change)
    # mysql: 1 query to get user, 1 to get shelf, 1 to get books
    user = current_app.auth.get_current_user()

    if isinstance(current_app.db, MySQLProvider):
        shelf_query = f"""
        SELECT shelf_no, background_url, color FROM shelves
        WHERE shelf_no = {shelf_no} AND user_id = {user.id};
        """

        shelf_result = current_app.db.execute_query(shelf_query)
        if not shelf_result:
            raise NotFound()
        shelf = Shelf({
            'shelf_no': shelf_result[0]['shelf_no'],
            'background_url': shelf_result[0]['background_url'],
            'color': shelf_result[0]['color'],
        })

        query = f"""
        SELECT sb.book_id, sb.progress, b.title, b.id, b.author, b.cover_url
        FROM shelf_books sb
        JOIN books b ON sb.book_id = b.id
        JOIN shelves s ON sb.shelf_no = s.shelf_no AND sb.user_id = {user.id}
        WHERE s.shelf_no = {shelf_no} AND s.user_id = {user.id};
        """

        results = current_app.db.execute_query(query)
    else:
        # book: title, id, author, cover_url
        shelf = current_app.db.get_raw_db()['users'].find_one(
            {'_id': user.id, 'shelves.shelf_no': shelf_no},
            {'shelves.$': 1}
        )

        if shelf is None:
            raise NotFound()

        shelf = shelf['shelves'][0]

        results = []
        for book in shelf.get('books', []):
            book_info = {
                'book_id': book['book_id'],
                'progress': book['progress'],
                'title': book.get('title', ''),
                'author': book.get('author', ''),
                'cover_url': book.get('cover_url', ''),
            }
            results.append(book_info)

        shelf = Shelf(shelf)

    return render_template("shelves/shelf.html", shelf=shelf, books=results)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@shelves_bp.route('/create-shelf', methods=['POST'])
@middleware.require_auth
def create_shelf():
    # mongodb: 1 query to get user, 1 to insert shelf (shelves are embedded inside user)
    # mysql: 1 query to get user, 1 query to get shelves, 1 to insert shelf

    user = current_app.auth.get_current_user()

    existing_shelves = current_app.db.get_related(user, Shelf)

    file = request.files.get('backgroundImage', None)
    filename = ""
    if 'backgroundImage' in request.files and file.filename != '':
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.SHELVES_BG_FOLDER, filename))

    shelf = ShelfFactory.create_shelf(
        current_app.db,
        shelf_no=max((s.shelf_no for s in existing_shelves), default=0) + 1,
        background_url=filename,
        color=request.form.get('color', '#FFFFFF'),
        user_id=user.id
    )

    current_app.db.insert(shelf)

    return redirect(url_for('shelves.list'))

@shelves_bp.route('/<int:shelf_no>/delete', methods=['POST'])
@middleware.require_auth
def delete(shelf_no):
    # mongodb: 1 query to get user, 1 to delete the shelf (shelves are embedded inside user)
    # mysql: 1 query to get user, 1 to delete shelf
    user = current_app.auth.get_current_user()

    if isinstance(current_app.db, MongoDBProvider):
        shelf = current_app.db.get_raw_db()['users'].find_one(
            {'_id': user.id, 'shelves.shelf_no': shelf_no},
            {'shelves.$': 1}
        )['shelves'][0]
        if not shelf:
            raise NotFound()
        shelf = Shelf(shelf)
    else:
        shelf_query = f"""
        SELECT shelf_no, background_url, color FROM shelves
        WHERE shelf_no = {shelf_no} AND user_id = {user.id};
        """

        shelf_result = current_app.db.execute_query(shelf_query)
        if not shelf_result:
            raise NotFound()
        shelf = Shelf({
            'shelf_no': shelf_result[0]['shelf_no'],
            'background_url': shelf_result[0]['background_url'],
            'color': shelf_result[0]['color'],
            'user_id': user.id,
        })

    if shelf.background_url:
        os.remove(os.path.join(current_app.SHELVES_BG_FOLDER, shelf.background_url))

    current_app.db.delete(shelf)

    return redirect(url_for('shelves.list'))