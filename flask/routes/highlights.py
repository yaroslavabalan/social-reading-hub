import os
from datetime import datetime

from bson import ObjectId
from flask import Blueprint, render_template, current_app, redirect, url_for, request, session
from werkzeug.utils import secure_filename

import middleware
from db.MongoDBProvider import MongoDBProvider
from db.MySQLProvider import MySQLProvider
from db.models import Book, Post, Discussion
from db.models.Highlight import Highlight

import logging

from routes.shelves import allowed_file

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

highlights_bp = Blueprint('highlights', __name__)

@highlights_bp.route('/create-highlight/<string:book_id>', methods=['GET'])
@middleware.require_auth
def create_highlight(book_id):

    user = current_app.auth.get_current_user()
    book = current_app.db.get_by_id(Book, book_id)

    text = request.args.get('text', '')
    if not text:
        raise ValueError('Text for highlight is required')

    return render_template("highlights/create_highlight.html",
                           book=book.to_dict(),
                            text=text.strip()
                           )

@highlights_bp.route('/insert-highlight/<string:book_id>', methods=['POST'])
@middleware.require_auth
def insert_highlight(book_id):
    user = current_app.auth.get_current_user()

    quote = request.form.get('quote', '').strip()
    color = request.form.get('color', '').strip()
    type = request.form.get('type', 'highlight').strip()
    current_timestamp = str(datetime.now())

    new_highlight = {
        'user_id': user.id,
        'book_id': book_id,
        'text': quote,
        'color': color,
        'timestamp': current_timestamp,
    }

    if type == 'highlight':

        if isinstance(current_app.db, MongoDBProvider):
            new_highlight['type'] = 'highlight'

        current_app.db.insert(Highlight(new_highlight))
    elif type == 'post':
        comment = request.form.get('comment', '').strip()
        file = request.files.get('background', None)
        filename = ""
        if 'background' in request.files and file.filename != '':
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.HIGHLIGHTS_BG_FOLDER, filename))

        new_post = {
            'description': comment,
            'background': filename,
        }

        if isinstance(current_app.db, MySQLProvider):
            id = current_app.db.insert(Highlight(new_highlight))
            new_post['id'] = id
            current_app.db.insert(Post(new_post))
        else:
            new_highlight['description'] = comment
            new_highlight['background'] = filename
            new_highlight['type'] = 'post'

            current_app.db.insert(Post(new_highlight))

    elif type == 'discussion':
        visibility = request.form.get('visibility', '')
        locked = request.form.get('locked', '0') == '1'

        new_discussion = {
            'visibility': visibility,
            'locked': locked,
        }

        if isinstance(current_app.db, MySQLProvider):
            id = current_app.db.insert(Highlight(new_highlight))
            new_discussion['id'] = id
            current_app.db.insert(Discussion(new_discussion))
        else:
            new_highlight['visibility'] = visibility
            new_highlight['locked'] = locked
            new_highlight['type'] = 'discussion'

            current_app.db.insert(Discussion(new_highlight))

    return redirect(url_for('shelves.list'))

@highlights_bp.route('/list', methods=['GET'])
@middleware.require_auth
def list():
    user = current_app.auth.get_current_user()
    highlights = current_app.db.get_related(user, Highlight)

    return render_template("highlights/list.html",
                           highlights=highlights
                           )

@highlights_bp.route('/delete-highlight', methods=['POST'])
@middleware.require_auth
def delete_highlight():
    user = current_app.auth.get_current_user()
    highlight_id = request.form.get('highlight_id', '').strip()

    if isinstance(current_app.db, MySQLProvider):
        query = """
        DELETE FROM highlights
        WHERE user_id = %s AND id = %s
        """
        current_app.db.execute_query(query, [user.id, highlight_id])
    else:
        current_app.db.get_raw_db().highlights.delete_one({
            "_id": ObjectId(highlight_id),
            "user_id": user.id
        })

    return redirect(url_for('highlights.list'))