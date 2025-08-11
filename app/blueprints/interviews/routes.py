from flask import render_template, request, send_file, redirect, url_for, current_app, flash
from flask_login import login_required, current_user
from . import bp
from .forms import InterviewForm
from ...extensions import db, rq
from ...models.interview import Interview
from ...models.recording import Recording
from ...models.application import Application
from ...models.candidate import Candidate
from ...services.ics import build_ics
from ...services.storage import save_file
from ...jobs.transcribe import transcribe_recording
from io import BytesIO
from uuid import uuid4
from datetime import timedelta

@bp.get("")
@login_required
def list_interviews():
    query = Interview.query.filter_by(org_id=current_user.org_id).order_by(Interview.scheduled_start.desc())
    # 直近順
    items = query.all()
    # Application/Candidate をまとめて取得（簡易: テンプレートで参照）
    app_map = {a.id: a for a in Application.query.filter(Application.id.in_([i.application_id for i in items or []])).all()}
    cand_ids = list({a.candidate_id for a in app_map.values()}) if app_map else []
    cand_map = {c.id: c for c in Candidate.query.filter(Candidate.id.in_(cand_ids)).all()} if cand_ids else {}
    return render_template("interviews/list.html", items=items, app_map=app_map, cand_map=cand_map)

@bp.route("/create", methods=["GET","POST"])
@login_required
def create_interview():
    form = InterviewForm()
    # Pre-fill candidate_id if provided via query string (backward compat via application_id)
    if request.method == 'GET':
        app_id = request.args.get('application_id')
        cand_id = request.args.get('candidate_id')
        if cand_id:
            form.candidate_id.data = str(cand_id)
        elif app_id:
            app_row = Application.query.filter_by(id=int(app_id), org_id=current_user.org_id).first()
            if app_row:
                form.candidate_id.data = str(app_row.candidate_id)
    if form.validate_on_submit():
        # Resolve candidate_id: prefer explicit, else derive from application
        # Candidate is required now
        cand_id_val = int(form.candidate_id.data)
        # Ensure an Application exists for this candidate in this org (use latest or create one)
        app_row = Application.query.filter_by(org_id=current_user.org_id, candidate_id=cand_id_val)\
                                   .order_by(Application.id.desc()).first()
        if not app_row:
            app_row = Application(org_id=current_user.org_id, candidate_id=cand_id_val)
            db.session.add(app_row); db.session.commit()
        i = Interview(
            org_id=current_user.org_id,
            application_id=app_row.id,
            scheduled_start=form.scheduled_start.data,
            location=form.location.data,
            meeting_url=form.meeting_url.data,
            ics_token=str(uuid4())
        )
        # Optional evaluation fields
        i.step = form.step.data or None
        i.rank = form.rank.data or None
        i.decision = form.decision.data or None
        i.comment = form.comment.data or None
        i.interviewer = form.interviewer.data or None
        db.session.add(i); db.session.commit()
        # If a file was uploaded, save recording and redirect to analyze endpoint
        f = None
        try:
            f = request.files.get(form.file.name)
        except Exception:
            f = None
        if f and getattr(f, 'filename', ''):
            url = save_file(f, prefix=f"org{current_user.org_id}/interview{i.id}")
            rec = Recording(org_id=current_user.org_id, interview_id=i.id, storage_url=url)
            db.session.add(rec); db.session.commit()
            return redirect(url_for("interviews.analyze_recording", interview_id=i.id, recording_id=rec.id))
        # No file uploaded: go back to list
        return redirect(url_for("interviews.list_interviews"))
    return render_template("interviews/detail.html", form=form, interview=None)

@bp.get("/<int:interview_id>")
@login_required
def detail(interview_id):
    i = Interview.query.filter_by(id=interview_id, org_id=current_user.org_id).first_or_404()
    return render_template("interviews/detail.html", interview=i, form=None)

@bp.get("/<int:interview_id>/ics")
@login_required
def download_ics(interview_id):
    i = Interview.query.filter_by(id=interview_id, org_id=current_user.org_id).first_or_404()
    ics = build_ics(current_app.config['UID_DOMAIN'],
                    title=f"Interview #{i.id}",
                    start=i.scheduled_start,
                    end=(i.scheduled_start + timedelta(hours=1)),
                    location=i.location or "",
                    description=i.meeting_url or "")
    return send_file(BytesIO(ics.encode('utf-8')), as_attachment=True,
                     download_name=f"interview_{i.id}.ics", mimetype="text/calendar")

@bp.post("/<int:interview_id>/upload")
@login_required
def upload_recording(interview_id):
    i = Interview.query.filter_by(id=interview_id, org_id=current_user.org_id).first_or_404()
    f = request.files['file']
    url = save_file(f, prefix=f"org{current_user.org_id}/interview{i.id}")
    rec = Recording(org_id=current_user.org_id, interview_id=i.id, storage_url=url)
    db.session.add(rec); db.session.commit()
    # 非同期で文字起こし
    rq.enqueue(transcribe_recording, rec.id, "ja")
    return redirect(url_for("interviews.detail", interview_id=i.id))

@bp.get("/<int:interview_id>/analyze")
@login_required
def analyze_recording(interview_id):
    i = Interview.query.filter_by(id=interview_id, org_id=current_user.org_id).first_or_404()
    # recording_id is optional; if not provided, use the latest recording for this interview
    rec_id = request.args.get('recording_id', type=int)
    rec = None
    if rec_id:
        rec = Recording.query.filter_by(id=rec_id, org_id=current_user.org_id, interview_id=i.id).first()
    if not rec:
        rec = Recording.query.filter_by(org_id=current_user.org_id, interview_id=i.id).order_by(Recording.id.desc()).first()
    if not rec:
        flash("録音ファイルが見つかりませんでした", "warning")
        return redirect(url_for("interviews.list_interviews"))
    rq.enqueue(transcribe_recording, rec.id, "ja")
    flash("録音の解析を開始しました", "success")
    return redirect(url_for("interviews.list_interviews"))