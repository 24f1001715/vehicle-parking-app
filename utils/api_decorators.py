from functools import wraps
from flask import session, jsonify, request

def api_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required. Please login as admin.'}), 403
        return f(*args, **kwargs)
    return decorated_function

def api_user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'user':
            return jsonify({'success': False, 'message': 'User authentication required. Please login.'}), 401
        return f(*args, **kwargs)
    return decorated_function

def api_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        role = session.get('role')
        if role not in ('admin', 'user'):
            return jsonify({'success': False, 'message': 'Authentication required. Please login.'}), 401
        return f(*args, **kwargs)
    return decorated_function
