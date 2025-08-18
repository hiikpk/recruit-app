from flask import render_template, request, send_file, redirect, url_for, current_app, flash
from flask_login import login_required, current_user
from . import bp
from .forms import InterviewForm
from ...extensions import db, rq
from ...models.interview import Interview
from ...models.recording import Recording
from ...models.candidate import Candidate
from ...models.evaluation import Evaluation
from ...services.ics import build_ics
from ...services.storage import save_file
from ...jobs.transcribe import transcribe_recording
from io import BytesIO
from uuid import uuid4
from datetime import timedelta

@bp.get("")
@login_required
def list_interviews():
    query = Interview.query.filter_by(org_id=current_user.org_id).order_by(Interview.scheduled_at.desc())
    # 直近順
    items = query.all()
    # Candidate をまとめて取得（テンプレートで表示）
    cand_ids = list({i.candidate_id for i in items or []}) if items else []
    cand_map = {c.id: c for c in Candidate.query.filter(Candidate.id.in_(cand_ids)).all()} if cand_ids else {}
    return render_template("interviews/list.html", items=items, cand_map=cand_map)

@bp.route("/create", methods=["GET","POST"])
@login_required
def create_interview():
    form = InterviewForm()
    # Pre-fill candidate_id if provided via query string (backward compat via application_id)
    if request.method == 'GET':
        # app_id = request.args.get('application_id')
        cand_id = request.args.get('candidate_id')
        if cand_id:
            form.candidate_id.data = str(cand_id)
        # elif app_id:
        #     app_row = Application.query.filter_by(id=int(app_id), org_id=current_user.org_id).first()
        #     if app_row:
        #         form.candidate_id.data = str(app_row.candidate_id)
    if form.validate_on_submit():
        # Resolve candidate_id from the form
        cand_id_val = int(form.candidate_id.data)
        i = Interview(
            org_id=current_user.org_id,
            candidate_id=cand_id_val,
            scheduled_at=form.scheduled_at.data,
        )
        # Optional evaluation fields
        i.step = form.step.data or None
        i.status = form.status.data or None
        i.result = form.result.data or None
        i.comment = form.comment.data or None
        i.interviewer = form.interviewer.data or None
        # allow initial transcript text on create
        i.transcript_text = form.transcript_text.data or None
        db.session.add(i)
        db.session.commit()
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

@bp.route("/<int:interview_id>", methods=["GET","POST"])
@login_required
def detail(interview_id):
    i = Interview.query.filter_by(id=interview_id, org_id=current_user.org_id).first_or_404()
    form = InterviewForm(obj=i)
    # Pre-fill candidate_id for validation/read-only display
    try:
        form.candidate_id.data = str(i.candidate_id)
    except Exception:
        pass

    if form.validate_on_submit():
        # Update interview fields from form
        i.scheduled_at = form.scheduled_at.data or i.scheduled_at
        i.step = form.step.data or None
        i.status = form.status.data or None
        i.result = form.result.data or None
        i.comment = form.comment.data or None
        i.interviewer = form.interviewer.data or None
        i.location = form.location.data or None
        i.meeting_url = form.meeting_url.data or None
        # save edited transcript if provided
        try:
            i.transcript_text = form.transcript_text.data or i.transcript_text
        except Exception:
            pass
        db.session.commit()
        flash("選考情報を更新しました", "success")
        return redirect(url_for('interviews.detail', interview_id=i.id))

    # Load evaluations for this interview (latest first)
    evaluations = Evaluation.query.filter_by(org_id=current_user.org_id, interview_id=i.id).order_by(Evaluation.created_at.desc()).all()
    # Load latest transcript metrics for this interview (if any)
    metrics = None
    try:
        from ...extensions import db
        q = db.text(
            """
            SELECT t.metrics FROM transcripts t
            JOIN recordings r ON r.id = t.recording_id
            WHERE r.interview_id = :int_id
            ORDER BY t.created_at DESC
            LIMIT 1
            """
        )
        res = db.session.execute(q, {"int_id": i.id}).fetchone()
        metrics = res[0] if res and len(res) > 0 else None
    except Exception:
        metrics = None

    # Load latest transcript text for this interview (if any)
    transcript_text = None
    try:
        q2 = db.text(
            """
            SELECT t.text FROM transcripts t
            JOIN recordings r ON r.id = t.recording_id
            WHERE r.interview_id = :int_id
            ORDER BY t.created_at DESC
            LIMIT 1
            """
        )
        res2 = db.session.execute(q2, {"int_id": i.id}).fetchone()
        transcript_text = res2[0] if res2 and len(res2) > 0 else None
        if transcript_text:
            # attach to the interview object for template convenience
            try:
                i.transcript_text = transcript_text
            except Exception:
                pass
        # ensure the form textarea shows the latest transcript when editing
        try:
            form.transcript_text.data = transcript_text or getattr(i, 'transcript_text', None)
        except Exception:
            pass
    except Exception:
        transcript_text = None

    return render_template("interviews/detail.html", interview=i, form=form, evaluations=evaluations, metrics=metrics, transcript_text=transcript_text)

@bp.get("/<int:interview_id>/ics")
@login_required
def download_ics(interview_id):
    i = Interview.query.filter_by(id=interview_id, org_id=current_user.org_id).first_or_404()
    ics = build_ics(current_app.config['UID_DOMAIN'],
                    title=f"Interview #{i.id}",
                    start=i.scheduled_at,
                    end=(i.scheduled_at + timedelta(hours=1)),
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