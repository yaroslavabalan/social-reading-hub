import os

from bson import ObjectId
from flask import Blueprint, render_template, current_app, url_for, redirect
from werkzeug.exceptions import NotFound

import middleware
from db.MongoDBProvider import MongoDBProvider
from db.MySQLProvider import MySQLProvider
from db.models.Post import Post
from db.models.Highlight import Highlight

posts_bp = Blueprint('posts', __name__)

@posts_bp.route('/<string:post_id>')
@middleware.require_auth
def view(post_id):

    if isinstance(current_app.db, MySQLProvider):
        query = """
        SELECT h.*, p.description, p.background, u.name, b.title
        FROM highlights h
        JOIN posts p ON h.id = p.id
        JOIN users u ON h.user_id = u.id
        JOIN books b ON h.book_id = b.id
        WHERE h.id = %s
        """

        result = current_app.db.execute_query(query, [post_id])[0]

        post = Post(result)
        user = result['name']
        book = result['title']
    else:
        post_pipeline = [
            {'$match': {'_id': ObjectId(post_id), 'type': 'post'}},
            {'$lookup': {
                'from': 'users',
                'localField': 'user_id',
                'foreignField': '_id',
                'as': 'user_data'
            }},
            {'$lookup': {
                'from': 'books',
                'localField': 'book_id',
                'foreignField': '_id',
                'as': 'book_data'
            }},
            {'$project': {
                'post': '$$ROOT',
                'user': {'$arrayElemAt': ['$user_data.name', 0]},
                'book': {'$arrayElemAt': ['$book_data.title', 0]}
            }}
        ]

        result = list(current_app.db.get_raw_db().highlights.aggregate(post_pipeline))

        if result:
            post = MongoDBProvider.mongo_to_model(Post, result[0]['post'])
            user = result[0]['user'] or ""
            book = result[0]['book'] or ""
        else:
            raise NotFound()

    if not post:
        raise NotFound()

    return render_template("posts/view.html", post=post, user=user, book=book)

@posts_bp.route('/<string:post_id>/delete', methods=['POST'])
@middleware.require_auth
def delete(post_id):
    if isinstance(current_app.db, MySQLProvider):
        query = """
        SELECT h.*, p.description, p.background
        FROM highlights h
        JOIN posts p ON h.id = p.id
        WHERE h.id = %s
        """

        result = current_app.db.execute_query(query, [post_id])[0]

        post = Post(result)
    else:
        post = current_app.db.get_by_id(Post, post_id)

    if not post:
        raise NotFound()

    user = current_app.auth.get_current_user()

    if not post or post.raw_attributes['user_id'] != user.id:
        raise NotFound()

    if isinstance(current_app.db, MySQLProvider):
        query = """
        DELETE FROM posts WHERE id = %s;
        """

        current_app.db.execute_query(query, [post.id])

    else:
        highlight = Highlight({
            'id': post.id,
            'user_id': post.raw_attributes['user_id'],
            'book_id': post.raw_attributes['book_id'],
            'text': post.raw_attributes['text'],
            'color': post.raw_attributes['color'],
            'timestamp': post.raw_attributes['timestamp'],
            'description': None,
            'background': None,
            'type': None
        })

        current_app.db.update(highlight)

    if post.background and post.background not in ['bg1.jpg', 'bg2.jpg', 'bg3.jpg', 'bg4.jpg', 'bg5.jpg']:
        os.remove(os.path.join(current_app.HIGHLIGHTS_BG_FOLDER, post.background))

    return redirect(url_for('user.profile', user_id=user.id))