import os
from flask import Flask, session

import logging

from auth import Auth
from db.MongoDBProvider import MongoDBProvider
from db.MySQLProvider import MySQLProvider
from db.models.Shelf import Shelf
from db.models.Book import Book
from db.models.ShelfBook import ShelfBook
from db.models.User import User
from routes.books import books_bp
from routes.debug import debug_bp
from routes.discussions import discussions_bp
from routes.highlights import highlights_bp
from routes.main import main_bp
from routes.manager import manager_bp
from middleware import setup_all_middleware
from dotenv import load_dotenv
from routes.usecase1 import usecase1_bp
from routes.usecase2 import usecase2_bp

from routes.posts import posts_bp
from routes.shelves import shelves_bp
from routes.user import user_bp



app = Flask(__name__)
setup_all_middleware(app)
env = load_dotenv()


app.secret_key = os.environ.get("SECRET_KEY")

# mysql config
app.db_configuration = {
    "MYSQL_HOST": os.environ.get("MYSQL_HOST", "127.0.0.1"),
    "MYSQL_PORT": int(os.environ.get("MYSQL_PORT", 3306)),
    "MYSQL_USER": os.environ.get("MYSQL_USER", "root"),
    "MYSQL_PASSWORD": os.environ.get("MYSQL_PASSWORD", ""),
    "MYSQL_DB": os.environ.get("MYSQL_DB", "social-reading-hub"),
}

# folders
app.SHELVES_BG_FOLDER = os.path.join(app.static_folder, "shelves_backgrounds")
app.HIGHLIGHTS_BG_FOLDER = os.path.join(app.static_folder, "highlights_backgrounds")

# mongo uri
app.mongo_uri = os.environ.get(
    "MONGO_URI", "mongodb://localhost:27017/imse-social-reading-hub"
)

# init db providers
try:
    mysql_db = MySQLProvider(app.db_configuration)
    mysql_db.initialize_database()
    app.mysql_db = mysql_db

    print("✅ MySQL database initialized successfully.")
except Exception as e:
    print(f"⚠ Warning: Could not initialize MySQL database: {e}")
    print("  The app will still run, but database features won't work.")
    app.mysql_db = None

try:
    app.mongo_db = MongoDBProvider(app.mongo_uri, app=app)

    print("✅ MongoDB database initialized successfully.")
except Exception as e:
    print(f"⚠ Warning: Could not initialize MongoDB: {e}")
    print("  The app will still run, but MongoDB features won't work.")
    app.mongo_db = None

# choose default db
if app.mysql_db is not None:
    app.db = app.mysql_db
elif app.mongo_db is not None:
    app.db = app.mongo_db
else:
    app.db = None

# auth
app.auth = Auth()

# blueprints
app.register_blueprint(main_bp)
# app.register_blueprint(debug_bp)
app.register_blueprint(manager_bp, url_prefix="/manager")
app.register_blueprint(shelves_bp, url_prefix="/shelves")
app.register_blueprint(books_bp, url_prefix="/books")
app.register_blueprint(user_bp, url_prefix="/user")
app.register_blueprint(highlights_bp, url_prefix="/highlights")
app.register_blueprint(discussions_bp, url_prefix="/discussions")
app.register_blueprint(posts_bp, url_prefix="/posts")
app.register_blueprint(usecase2_bp, url_prefix="/usecase2")
app.register_blueprint(usecase1_bp, url_prefix='/usecase1')


@app.context_processor
def inject_selected_user():
    """Inject current user into templates."""
    try:
        user = app.auth.get_current_user()
        user_details = None
        if user and app.db:
            user_details = user.to_dict()
            user_shelves = app.db.get_related(user, Shelf)
            user_details["shelves"] = {}
            for shelf in user_shelves:
                user_details["shelves"][shelf.shelf_no] = shelf.to_dict()
        return dict(loggedInUser=user_details)
    except Exception as e:
        logging.getLogger(__name__).error(f"Error injecting selected user: {e}")
        return dict(loggedInUser=None)


@app.context_processor
def determine_db_type():
    from db.MySQLProvider import MySQLProvider
    from db.MongoDBProvider import MongoDBProvider

    if isinstance(app.db, MySQLProvider):
        db_type = "mysql"
    elif isinstance(app.db, MongoDBProvider):
        db_type = "mongodb"
    else:
        db_type = "unknown"

    return dict(db_type=db_type)


@app.route("/shelves-backgrounds/<string:filename>")
def uploaded_file(filename):
    return app.send_static_file("shelves_backgrounds/" + filename)


@app.route("/book-source/<string:filename>")
def book_source(filename):
    return app.send_static_file("books/" + filename)


@app.route("/highlights-backgrounds/<string:filename>")
def highlight_background_file(filename):
    return app.send_static_file("highlights_backgrounds/" + filename)


@app.after_request
def add_security_headers(response):
    response.headers["Content-Security-Policy"] = "frame-ancestors *"
    response.headers.pop("X-Frame-Options", None)
    return response
