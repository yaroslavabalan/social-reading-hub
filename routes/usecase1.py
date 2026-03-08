import os
import logging
import random

from db.MySQLProvider import MySQLProvider
from db.MongoDBProvider import MongoDBProvider

from flask import Blueprint, render_template, current_app, redirect, url_for
from werkzeug.exceptions import NotFound, Forbidden

import middleware
from db.MySQLProvider import MySQLProvider

logger = logging.getLogger(__name__)

usecase1_bp = Blueprint('usecase1', __name__)

@usecase1_bp.route('/', methods=['GET'])
@middleware.require_auth
def index():
    """
    Use case 1 report:
    "Posts by Book" -> for each book show how many posts exist.
    Mongo: aggregate highlights where type='post', group by book_id, lookup books
    """
    message = []
    data = []

    if isinstance(current_app.db, MySQLProvider):
        sql_file_path = os.path.join(
            os.path.dirname(__file__), "..", "db", "usecase1", "query_statement.sql"
        )

        try:
            with open(sql_file_path, "r") as f:
                query = f.read().strip()

            results = current_app.db.execute_query(query)
            data = results if results else []

        except Exception as e:
            logger.error(f"Error executing usecase1 SQL query: {e}")
            message = [{"error": f"Failed to execute query: {str(e)}"}]

    
    elif isinstance(current_app.db, MongoDBProvider):
        try:
            db = current_app.db.get_raw_db()
            pipeline = [
            {"$lookup": {
                "from": "highlights",
                "let": {"bookId": "$_id"},
                "pipeline": [
                {"$match": {
                    "$expr": {"$and": [
                    {"$eq": ["$book_id", "$$bookId"]},
                    {"$eq": ["$type", "post"]}
                    ]}
                }}
                ],
                "as": "posts"
            }},
            {"$project": {
                "_id": 0,
                "book_id": {"$toString": "$_id"},
                "book_title": "$title",
                "post_count": {"$size": "$posts"}
            }},
            {"$sort": {"post_count": -1, "book_title": 1}}
        ]


            results = list(db.books.aggregate(pipeline))
            data = results if results else []

        except Exception as e:
            logger.error(f"Error executing usecase2 MongoDB query: {e}")
            message = [{"error": f"Failed to execute query: {str(e)}"}]

    return render_template("usecase1/index.html",
                           message=message,
                           data=data
                           )


@usecase1_bp.route('/simulate', methods=['POST'])
@middleware.require_auth
def simulate():
    """
   Convert one of current user's Highlights into a Post (IS-A).
    - find a highlight of current user that is NOT in posts
    - insert into posts with same id
    """

    # --------- MONGO SIMULATE ---------
    if isinstance(current_app.db, MongoDBProvider):
        user = current_app.auth.get_current_user()
        if not user:
            raise Forbidden()

        try:
            db = current_app.db.get_raw_db()

            picked = db.highlights.find_one(
                {"user_id": user.id, "type": {"$ne": "post"}},
                sort=[("_id", -1)]
            )

            if not picked:
                logger.info("No convertible highlights found for this user (Mongo).")
                return redirect(url_for('usecase1.index'))

            res = db.highlights.update_one(
                {"_id": picked["_id"]},
                {"$set": {
                    "type": "post",
                    "description": "Shared from highlight",
                    "background": None
                }}
            )

            logger.info(
                "Converted highlight %s to post (Mongo). matched=%s modified=%s",
                picked["_id"], res.matched_count, res.modified_count
            )

        except Exception as e:
            logger.error(f"Failed to insert post (Mongo): {e}")

        return redirect(url_for('usecase1.index'))
    # --------- SQL ---------


    if not isinstance(current_app.db, MySQLProvider):
        return redirect(url_for('usecase1.index'))

    user = current_app.auth.get_current_user()
    if not user:
        raise Forbidden()

    # find one highlight of this user that is not already a post
    pick_sql = """
        SELECT h.id
        FROM highlights h
        LEFT JOIN posts p ON p.id = h.id
        WHERE h.user_id = %s
          AND p.id IS NULL
        ORDER BY h.id DESC
        LIMIT 1;
    """
    rows = current_app.db.execute_query(pick_sql, [user.id])

    if not rows:
        logger.info("No convertible highlights found for this user.")
        return redirect(url_for('usecase1.index'))

    highlight_id = rows[0]['id']

    #create Post with same id as highlight 

    insert_sql = """
        INSERT INTO posts (id, description, background)
        VALUES (%s, %s, %s);
    """
    try:
        current_app.db.execute_query(insert_sql, [highlight_id, "Shared from simulate share the post", None])
        logger.info(f"Created Post from Highlight id={highlight_id}")
    except Exception as e:
        logger.error(f"Failed to insert post: {e}")

    return redirect(url_for('usecase1.index'))


@usecase1_bp.route('/share/<int:highlight_id>', methods=['POST'])
@middleware.require_auth
def share_as_post(highlight_id):
    """
    Real usecase endpoint: user clicks "Share as Post" on their highlight
    """
    if not isinstance(current_app.db, MySQLProvider):
        return redirect(url_for('usecase1.index'))

    user = current_app.auth.get_current_user()
    if not user:
        raise Forbidden()

    # verify ownership
    own_sql = "SELECT id FROM highlights WHERE id=%s AND user_id=%s LIMIT 1;"
    own = current_app.db.execute_query(own_sql, [highlight_id, user.id])
    if not own:
        raise NotFound("Highlight not found for this user")

    # prevent duplicates
    exists_sql = "SELECT id FROM posts WHERE id=%s LIMIT 1;"
    exists = current_app.db.execute_query(exists_sql, [highlight_id])
    if exists:
        return redirect(url_for('usecase1.index'))

    insert_sql = """
        INSERT INTO posts (id, description, background)
        VALUES (%s, %s, %s);
    """
    current_app.db.execute_query(insert_sql, [highlight_id, "Shared from simulate share the post", None])

    return redirect(url_for('usecase1.index'))
