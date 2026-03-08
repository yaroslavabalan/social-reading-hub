from bson import ObjectId
from flask import Blueprint, render_template, session, current_app, redirect, url_for
from pymongo import UpdateOne
from werkzeug.exceptions import NotFound

import middleware
from db.MongoDBProvider import MongoDBProvider
from db.models.Follows import Follows
from db.models.User import User

user_bp = Blueprint('user', __name__)

@user_bp.route('/')
@user_bp.route('/<string:user_id>')
@middleware.require_auth
def profile(user_id=None):
    current_user = current_app.auth.get_current_user()
    if user_id is None:
        user_id = session.get('selected_user')

    user = current_app.db.get_by_id(User, user_id)
    if not user:
        raise NotFound()

    posts_data = []
    discussions_data = []

    if isinstance(current_app.db, MongoDBProvider):
        followers_count = len(user.raw_attributes.get('followers', []))
        follows_count = len(user.raw_attributes.get('following', []))
        is_following = user.id in current_user.raw_attributes.get('following', [])
        exclude_ids = current_user.raw_attributes.get('following', []) + [current_user.id, user.id]

        raw_suggestions = current_app.db.get_raw_db().users.find(
            {"_id": {"$nin": exclude_ids}}
        ).limit(5)
        suggestions_data = [u for u in raw_suggestions]

        for suggestion in suggestions_data:
            suggestion['id'] = str(suggestion['_id'])
            del suggestion['_id']

    else:
        followers_count_query = "SELECT COUNT(*) as count FROM follows WHERE followee_id = %s"
        followers_result = current_app.db.execute_query(followers_count_query, [user.id])
        followers_count = followers_result[0]['count'] if followers_result else 0

        follows_count_query = "SELECT COUNT(*) as count FROM follows WHERE follower_id = %s"
        follows_result = current_app.db.execute_query(follows_count_query, [user.id])
        follows_count = follows_result[0]['count'] if follows_result else 0

        follow_check = """
                       SELECT 1
                       FROM follows
                       WHERE follower_id = %s
                         AND followee_id = %s
                       """
        is_following = bool(current_app.db.execute_query(follow_check, [
            current_user.id, user.id
        ]))

        suggestion_sql = """
                         SELECT u.*
                         FROM users u
                         WHERE u.id != %s
                           AND u.id NOT IN (SELECT followee_id FROM follows WHERE follower_id = %s)
                         LIMIT 5
                         """
        suggestions_data = current_app.db.execute_query(suggestion_sql, [current_user.id, current_user.id])

    if isinstance(current_app.db, MongoDBProvider):
        raw_highlights = list(current_app.db.get_raw_db().highlights.find(
            {"user_id": user.id}
        ))
    else:
        query = """
                SELECT h.*,
                       p.description as post_desc,
                       p.background  as post_bg,
                       d.visibility  as disc_vis,
                       d.locked      as disc_locked,
                       CASE
                           WHEN p.id IS NOT NULL THEN 'post'
                           WHEN d.id IS NOT NULL THEN 'discussion'
                           ELSE 'highlight'
                           END       as type
                FROM highlights h
                         LEFT JOIN posts p ON h.id = p.id
                         LEFT JOIN discussions d ON h.id = d.id
                WHERE h.user_id = %s \
                """
        raw_highlights = current_app.db.execute_query(query, [user.id])

    for item in raw_highlights:
        item_type = item.get('type')

        if item_type == 'post':
            post_obj = {
                **item,
                'id': item.get('id') or item.get('_id'),
                'description': item.get('description') or item.get('post_desc'),
                'background': item.get('background') or item.get('post_bg')
            }
            posts_data.append(post_obj)

        elif item_type == 'discussion':
            vis = item.get('visibility') or item.get('disc_vis')

            can_see = True
            if vis == 'hidden':
                if str(user.id) != str(current_user.id):
                    can_see = False

            if can_see:
                disc_obj = {
                    **item,
                    'id': item.get('id') or item.get('_id'),
                    'visibility': vis,
                    'locked': item.get('locked') or item.get('disc_locked')
                }

                discussions_data.append(disc_obj)

    return render_template("user/profile.html",
                           user=user.raw_attributes,
                           suggestions=suggestions_data,
                           is_following=is_following,
                           discussions=discussions_data,
                           posts=posts_data,
                           followers=followers_count,
                           follows=follows_count
                           )

@user_bp.route('/follow/<string:user_id>')
@middleware.require_auth
def follow_user(user_id):
    current_user = current_app.auth.get_current_user()

    if str(user_id) == str(current_user.id):
        return redirect(url_for('user.profile', user_id=user_id))

    if isinstance(current_app.db, MongoDBProvider):
        db = current_app.db.get_raw_db()

        db.users.bulk_write([
            UpdateOne(
                {"_id": ObjectId(current_user.id)},
                {"$addToSet": {"following": ObjectId(user_id)}}
            ),
            UpdateOne(
                {"_id": ObjectId(user_id)},
                {"$addToSet": {"followers": ObjectId(current_user.id)}}
            )
        ])

    else:
        query = """
                INSERT INTO follows (follower_id, followee_id)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE follower_id=follower_id \
                """

        try:
            current_app.db.execute_query(query, [
                current_user.id,
                user_id
            ])
        except Exception:
            pass

    return redirect(url_for('user.profile', user_id=user_id))

@user_bp.route('/unfollow/<string:user_id>')
@middleware.require_auth
def unfollow_user(user_id):
    current_user = current_app.auth.get_current_user()
    if user_id != current_user.id:

        if isinstance(current_app.db, MongoDBProvider):
            current_app.db.get_raw_db().users.bulk_write([
                UpdateOne(
                    {"_id": ObjectId(current_user.id)},
                    {"$pull": {"following": ObjectId(user_id)}}
                ),
                UpdateOne(
                    {"_id": ObjectId(user_id)},
                    {"$pull": {"followers": ObjectId(current_user.id)}}
                )
            ])
        else:
            current_app.db.delete(Follows({'follower_id': current_user.id, 'followee_id': user_id}))

    return redirect(url_for('user.profile', user_id=user_id))