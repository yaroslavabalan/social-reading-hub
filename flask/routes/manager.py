from flask import Blueprint, render_template, current_app, redirect, url_for, request, session

from db.DBMigrator import DBMigrator
from db.RandomDataGenerator import RandomDataGenerator
from db.models.User import User

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

manager_bp = Blueprint('manager', __name__)

@manager_bp.route('/view-users', methods=['GET'])
def view_users():
    logger.debug("Selected user: %s", session.get('selected_user', None))
    users = current_app.db.get_list(User)

    return render_template("manager/view_users.html",
                           users=users,
                           )

@manager_bp.route('/select-user', methods=['POST'])
def select_user():
    user_id = request.form.get('user_id')
    selected_user = current_app.db.get_by_id(User, user_id)

    if selected_user:
        session['selected_user'] = user_id

    return redirect(url_for('manager.view_users'))


@manager_bp.route('/add-user', methods=['POST'])
def add_user():
    name = request.form.get('name')
    email = request.form.get('email')
    reading_speed = request.form.get('reading_speed', 0)

    new_user = User({
        'name': name,
        'email': email,
        'reading_speed': reading_speed
    })

    current_app.db.insert(new_user)

    return redirect(url_for('manager.view_users'))


@manager_bp.route("/remove-user", methods=['POST'])
def remove_user():
    user_id = request.form.get('user_id')

    user = current_app.db.get_by_id(User, user_id)
    if user:
        current_app.db.delete(user)

    return redirect(url_for('manager.view_users'))

@manager_bp.route("/log-out", methods=['POST'])
def log_out():
    session.pop('selected_user', None)
    return redirect(url_for('main.welcome'))

@manager_bp.route("/switch-db", methods=['POST'])
def switch_db():
    new_db = request.form.get('db_type')

    try:
        if new_db == 'mysql':
            current_app.db = current_app.mysql_db
        elif new_db == 'mongodb':
            current_app.db = current_app.mongo_db
        else:
            raise ValueError("Unsupported database type")

        current_app.auth.logout()
        logger.debug("Switched database to %s", new_db)
    except Exception as e:
        logger.error("Failed to switch database: %s", e)

    return redirect(url_for('manager.view_users'))

@manager_bp.route("/migrate-db", methods=['POST'])
def migrate_db():
    try:
        db_migrator = DBMigrator(current_app.mysql_db, current_app.mongo_db)
        db_migrator.migrate()

        logger.debug("Migrated database to MongoDB")
    except Exception as e:
        raise e

    return redirect(url_for('manager.view_users'))

@manager_bp.route("/seed-db", methods=['POST'])
def seed_db():
    try:
        size = request.args.get("size", 100)

        random_gen = RandomDataGenerator(current_app.db, int(size))
        random_gen.generate()

        logger.debug("Generated random data to current db")
    except Exception as e:
        raise e

    return redirect(url_for('manager.view_users'))

@manager_bp.route("/drop-db", methods=['POST'])
def drop_db():
    current_app.db.drop_all_collections()

    return redirect(url_for('manager.view_users'))