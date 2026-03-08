from datetime import datetime

from bson import ObjectId
from flask import Blueprint, render_template, current_app, url_for, redirect, request
from werkzeug.exceptions import NotFound, Forbidden

import middleware
from db.MongoDBProvider import MongoDBProvider
from db.MySQLProvider import MySQLProvider
from db.models import Discussion
from db.models.Comment import Comment
from db.models.Highlight import Highlight
discussions_bp = Blueprint('discussions', __name__)

@discussions_bp.route('/<string:discussion_id>')
@middleware.require_auth
def discussion(discussion_id):
    user = current_app.auth.get_current_user()
    discussion_data = None
    comments_data = []

    if isinstance(current_app.db, MongoDBProvider):
        discussion_pipeline = [
            {'$match': {'_id': ObjectId(discussion_id), 'type': 'discussion'}},
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
                'discussion': '$$ROOT',
                'user': {'$arrayElemAt': ['$user_data.name', 0]},
                'book': {'$arrayElemAt': ['$book_data.title', 0]}
            }}
        ]

        result = current_app.db.get_raw_db().highlights.aggregate(discussion_pipeline)
        if not result:
            raise NotFound()

        result = list(result)[0]
        discussion_data = result['discussion']
        user_name = result.get('user', '')
        book = result.get('book', '')

        if discussion_data:
            discussion_data['id'] = str(discussion_data['_id'])
            comments_data = discussion_data.get('comments', [])
            comments_data.sort(key=lambda x: x.get('timestamp', ''))

    else:
        query = """
                SELECT h.*, d.locked, d.visibility, u.name, b.title
                FROM highlights h
                         JOIN discussions d ON h.id = d.id
                         JOIN users u ON h.user_id = u.id
                         JOIN books b ON h.book_id = b.id
                WHERE h.id = %s
                """
        result = current_app.db.execute_query(query, [discussion_id])
        if not result:
            raise NotFound()

        discussion_data = result[0]
        book = discussion_data.get('title', '')
        user_name = discussion_data.get('name', '')

        if discussion_data:
            comment_query = """
                            SELECT c.*, u.name, u.email
                            FROM comments c
                                     JOIN users u ON c.user_id = u.id
                            WHERE c.discussion_id = %s
                            ORDER BY c.timestamp
                            """
            comments_data = current_app.db.execute_query(comment_query, [discussion_id])

    if not discussion_data:
        raise NotFound()

    is_owner = str(discussion_data.get('user_id')) == str(user.id)
    if discussion_data.get('visibility') == 'hidden' and not is_owner:
        raise NotFound()

    return render_template(
        "discussions/discussion.html",
        discussion=discussion_data,
        comments=comments_data,
        user = user_name,
        book=book,
    )

@discussions_bp.route('/<string:discussion_id>/add-comment', methods=['POST'])
@middleware.require_auth
def post_comment(discussion_id):
    if isinstance(current_app.db, MySQLProvider):
        query = """
        SELECT h.*, d.locked, d.visibility
        FROM highlights h
        JOIN discussions d ON h.id = d.id
        WHERE h.id = %s
        """

        discussion = current_app.db.execute_query(query, [discussion_id])
        discussion = Discussion(discussion[0]) if len(discussion) > 0 else None
    else:
        discussion = current_app.db.get_by_id(Discussion, discussion_id)

    if not discussion:
        raise NotFound()

    if discussion.locked:
        raise Forbidden()

    user = current_app.auth.get_current_user()
    content = request.form.get('content', '').strip()

    comment_parameters = {
        'discussion_id': discussion.id,
        'user_id': user.id,
        'content': content,
        'timestamp': str(datetime.now()),
    }

    if isinstance(current_app.db, MongoDBProvider):
        comment_parameters['name'] = user.name
        comment_parameters['email'] = user.email
        comment_parameters['id'] = ObjectId()

    current_app.db.insert(Comment(comment_parameters))

    return redirect(url_for('discussions.discussion', discussion_id=discussion.id))

@discussions_bp.route('/<string:discussion_id>/lock', methods=['POST'])
@middleware.require_auth
def lock_discussion(discussion_id):
    if isinstance(current_app.db, MySQLProvider):
        query = """
        SELECT h.*, d.locked, d.visibility
        FROM highlights h
        JOIN discussions d ON h.id = d.id
        WHERE h.id = %s
        """

        discussion = current_app.db.execute_query(query, [discussion_id])
        discussion = Discussion(discussion[0]) if len(discussion) > 0 else None
    else:
        discussion = current_app.db.get_by_id(Discussion, discussion_id)

    user = current_app.auth.get_current_user()

    if not discussion or discussion.raw_attributes['user_id'] != user.id:
        raise NotFound()

    current_app.db.update(Discussion({
        'id': discussion.id,
        'locked': True,
        'visibility': discussion.visibility
    }))

    return redirect(url_for('discussions.discussion', discussion_id=discussion.id))

@discussions_bp.route('/<string:discussion_id>/unlock', methods=['POST'])
@middleware.require_auth
def unlock_discussion(discussion_id):
    if isinstance(current_app.db, MySQLProvider):
        query = """
        SELECT h.*, d.locked, d.visibility
        FROM highlights h
        JOIN discussions d ON h.id = d.id
        WHERE h.id = %s
        """

        discussion = current_app.db.execute_query(query, [discussion_id])
        discussion = Discussion(discussion[0]) if len(discussion) > 0 else None
    else:
        discussion = current_app.db.get_by_id(Discussion, discussion_id)

    user = current_app.auth.get_current_user()

    if not discussion or discussion.raw_attributes['user_id'] != user.id:
        raise NotFound()

    current_app.db.update(Discussion({
        'id': discussion.id,
        'locked': False,
        'visibility': discussion.visibility
    }))

    return redirect(url_for('discussions.discussion', discussion_id=discussion.id))

@discussions_bp.route('/<string:discussion_id>/make-public', methods=['POST'])
@middleware.require_auth
def make_public(discussion_id):
    if isinstance(current_app.db, MySQLProvider):
        query = """
        SELECT h.*, d.locked, d.visibility
        FROM highlights h
        JOIN discussions d ON h.id = d.id
        WHERE h.id = %s
        """

        discussion = current_app.db.execute_query(query, [discussion_id])
        discussion = Discussion(discussion[0]) if len(discussion) > 0 else None
    else:
        discussion = current_app.db.get_by_id(Discussion, discussion_id)

    user = current_app.auth.get_current_user()

    if not discussion or discussion.raw_attributes['user_id'] != user.id:
        raise NotFound()

    current_app.db.update(Discussion({
        'id': discussion.id,
        'locked': discussion.locked,
        'visibility': 'public'
    }))

    return redirect(url_for('discussions.discussion', discussion_id=discussion.id))

@discussions_bp.route('/<string:discussion_id>/make-hidden', methods=['POST'])
@middleware.require_auth
def make_hidden(discussion_id):
    if isinstance(current_app.db, MySQLProvider):
        query = """
        SELECT h.*, d.locked, d.visibility
        FROM highlights h
        JOIN discussions d ON h.id = d.id
        WHERE h.id = %s
        """

        discussion = current_app.db.execute_query(query, [discussion_id])
        discussion = Discussion(discussion[0]) if len(discussion) > 0 else None
    else:
        discussion = current_app.db.get_by_id(Discussion, discussion_id)

    user = current_app.auth.get_current_user()

    if not discussion or discussion.raw_attributes['user_id'] != user.id:
        raise NotFound()

    current_app.db.update(Discussion({
        'id': discussion.id,
        'locked': discussion.locked,
        'visibility': 'hidden'
    }))

    return redirect(url_for('discussions.discussion', discussion_id=discussion.id))

@discussions_bp.route('/<string:discussion_id>/delete', methods=['POST'])
@middleware.require_auth
def delete(discussion_id):
    if isinstance(current_app.db, MySQLProvider):
        query = """
        SELECT h.*, d.locked, d.visibility
        FROM highlights h
        JOIN discussions d ON h.id = d.id
        WHERE h.id = %s
        """

        discussion = current_app.db.execute_query(query, [discussion_id])
        discussion = Discussion(discussion[0]) if len(discussion) > 0 else None
    else:
        discussion = current_app.db.get_by_id(Discussion, discussion_id)

    user = current_app.auth.get_current_user()

    if not discussion or discussion.raw_attributes['user_id'] != user.id:
        raise NotFound()

    if isinstance(current_app.db, MySQLProvider):
        current_app.db.delete(Discussion({
            'id': discussion.id,
            'locked': discussion.locked,
            'visibility': discussion.visibility
        }))
    else:
        highlight_properties = Highlight({
            'id': discussion.id,
            'user_id': discussion.raw_attributes['user_id'],
            'book_id': discussion.raw_attributes['book_id'],
            'text': discussion.raw_attributes['text'],
            'color': discussion.raw_attributes['color'],
            'timestamp': discussion.raw_attributes['timestamp'],
        }).raw_attributes
        discussion_only_properties = {
            'type': None,
            'locked': None,
            'visibility': None,
            'comments': None
        }
        highlight_properties.update(discussion_only_properties)
        current_app.db.update(Highlight(highlight_properties))

    return redirect(url_for('user.profile', user_id=user.id))