"""
app/decorators.py

Simple role guards layered on top of Flask-Login's @login_required.
Kept as plain decorators rather than a permissions framework since the
platform only has three flat roles (student/lecturer/admin) -- introducing
a full RBAC system here would be over-engineering for the actual requirement.
"""

from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped
    return decorator
