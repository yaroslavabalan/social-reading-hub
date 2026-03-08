from flask import Blueprint, render_template, session, current_app

from db.models.Book import Book
from db.models.Shelf import Shelf
from db.models.ShelfBook import ShelfBook
from db.models.User import User

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def welcome():
    return render_template("index.html")