from bson.errors import InvalidId
from flask import current_app, session

from db.models.User import User


class Auth:
    def is_logged_in(self):
        return 'selected_user' in session and self.get_current_user() is not None

    def get_current_user(self):
        try:
            user = current_app.db.get_by_id(User, session.get('selected_user')) if 'selected_user' in session else None
            return user
        except InvalidId:
            session.pop('selected_user', None)
            return None

    def logout(self):
        if 'selected_user' in session:
            session.pop('selected_user', None)