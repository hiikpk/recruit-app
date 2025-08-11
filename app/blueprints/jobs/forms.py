from flask import request, jsonify
from flask_login import login_required, current_user
from ...extensions import rq
from ...jobs.evaluate import evaluate_application
from ...jobs.notify import notify_decision
from . import bp

@bp.post("/evaluate")
@login_required
def kick_evaluate():
    app_id = int(request.json["application_id"])
    job = rq.enqueue(evaluate_application, app_id)
    return jsonify({"job_id": job.id})

@bp.post("/notify")
@login_required
def kick_notify():
    data = request.json
    job = rq.enqueue(notify_decision, current_user.org_id, int(data["application_id"]), data["to"], data["subject"], data["html"])
    return jsonify({"job_id": job.id})