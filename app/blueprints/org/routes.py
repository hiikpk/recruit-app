from flask import jsonify
from flask_login import login_required, current_user
from . import bp

@bp.get("/me")
@login_required
def org_me():
    return jsonify({"org_id": current_user.org_id})