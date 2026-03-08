from flask import request, g, redirect, session
from functools import wraps
import time
import logging

import app
from auth import Auth

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def setup_request_middleware(app):
    @app.before_request
    def log_request():
        logger.debug(f"Incoming request: {request.method} {request.path}")
        g.start_time = time.time()

def setup_response_middleware(app):
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    @app.after_request
    def log_response(response):
        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time
            logger.debug(f"Response: {response.status_code} - {elapsed:.3f}s")
        return response

def setup_error_middleware(app):
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Resource not found"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}")
        return {"error": "Internal server error"}, 500

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not Auth().is_logged_in():
            return redirect('/manager/view-users')
        return f(*args, **kwargs)
    return decorated_function

def setup_all_middleware(app):
    setup_request_middleware(app)
    setup_response_middleware(app)
    setup_error_middleware(app)

    logger.info("All middleware initialized")

