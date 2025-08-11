from functools import wraps
from flask import abort
from flask_login import current_user

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if getattr(current_user, "role", None) != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped