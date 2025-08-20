from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from . import bp
from .forms import CandidateForm
from ...extensions import db
from ...models.candidate import Candidate
from ...models.evaluation import Evaluation
from ...models.interview import Interview
from ...models.candidate_overall_evaluation import CandidateOverallEvaluation
from datetime import datetime
from ...models.file import Files
from ...services.storage import save_file
from ...services.storage import download_bytes
from ...services.preview import render_preview
from flask import send_file
from sqlalchemy.orm import defer
import io
import mimetypes
from urllib.parse import urlencode
import json


# Helpers: coerce empty strings to None for integers and parse JSON-like inputs
def _coerce_int(val):
    if val is None or val == "":
        return None
    try:
        return int(val)
    except Exception:
        return None


def _coerce_json_field(val):
    # Accept dict/list as-is, coerce empty string to None, try to parse JSON for strings
    if val is None or val == "":
        return None
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except Exception:
            return None
    return None


@bp.get("")
@login_required
def list_candidates():
    q = request.args.get("q")
    applied_at = request.args.get("applied_at")
    status = request.args.get("status")
    channel = request.args.get("channel")
    applying_position = request.args.get("applying_position")
    nationality = request.args.get("nationality")

    query = Candidate.query.filter_by(org_id=current_user.org_id)
    if q:
        like = f"%{q}%"
        query = query.filter(Candidate.name.ilike(like))
    if applied_at:
        # filter by date (date-only)
        query = query.filter(Candidate.applied_at.cast(db.Date) == applied_at)
    if status:
        query = query.filter(Candidate.status == status)
    if channel:
        like = f"%{channel}%"
        query = query.filter(Candidate.channel.ilike(like))
    if applying_position:
        like = f"%{applying_position}%"
        query = query.filter(Candidate.applying_position.ilike(like))
    if nationality:
        like = f"%{nationality}%"
        query = query.filter(Candidate.nationality.ilike(like))

    # pagination
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=20, type=int)
    items_pagination = query.order_by(Candidate.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    # new applications cards (latest applied)
    new_apps = Candidate.query.filter_by(org_id=current_user.org_id, status='applied').order_by(Candidate.applied_at.desc()).limit(5).all()
    def make_page_url(target_page: int):
        params = request.args.to_dict()
        params['page'] = target_page
        params['per_page'] = items_pagination.per_page
        return request.path + '?' + urlencode(params)

    return render_template("candidates/list.html", items=items_pagination.items, pagination=items_pagination, new_apps=new_apps, make_page_url=make_page_url)

@bp.route("/create", methods=["GET", "POST"])
@login_required
def create_candidate():
    form = CandidateForm()
    if form.validate_on_submit():
        c = Candidate(
            org_id=current_user.org_id,
            name=form.name.data,
            name_yomi=form.name_yomi.data,
            applying_position=form.applying_position.data,
            nationality=form.nationality.data,
            email=form.email.data,
            phonenumber=form.phonenumber.data,
            birthdate=form.birthdate.data or None,
            memo=form.memo.data,
            school=form.school.data,
            grad_year=_coerce_int(form.grad_year.data),
            current_job=form.current_job.data,
            resume_file_id=_coerce_int(form.resume_file_id.data),
            qualifications=_coerce_json_field(form.qualifications.data),
            skills=_coerce_json_field(form.skills.data),
            languages=_coerce_json_field(form.languages.data),
            applied_at=form.applied_at.data or None,
            status=form.status.data or "applied",
            channel=form.channel.data,
            channel_detail=form.channel_detail.data,
        )
        db.session.add(c)
        db.session.commit()
        flash("候補者を作成しました", "success")
        return redirect(url_for("candidates.detail", candidate_id=c.id))
    return render_template("candidates/create.html", form=form)

@bp.route("/<int:candidate_id>", methods=["GET", "POST"])
@login_required
def detail(candidate_id):
    c = Candidate.query.filter_by(id=candidate_id, org_id=current_user.org_id).first_or_404()
    # applications テーブルは廃止。参照を停止する。
    app_row = None
    stage_form = None

    form = CandidateForm(obj=c)

    if form.validate_on_submit() and request.form.get("form_name") == "profile":
        form.populate_obj(c)
        # sanitize coerced attributes that may be empty strings from forms
        c.grad_year = _coerce_int(c.grad_year)
        c.resume_file_id = _coerce_int(c.resume_file_id)
        c.qualifications = _coerce_json_field(c.qualifications)
        c.languages = _coerce_json_field(c.languages)
        c.skills = _coerce_json_field(c.skills)
        if not c.applied_at:
            c.applied_at = datetime.utcnow()
        db.session.commit()
        flash("基本情報を更新しました", "success")
        return redirect(url_for("candidates.detail", candidate_id=c.id))


    interviews = (
        Interview.query
        .filter_by(org_id=c.org_id, candidate_id=c.id)
        .options(defer(Interview.scheduled_at))
        .order_by(Interview.created_at.desc())
        .all()
    )
    # scheduled_at はDBに存在しないため、テンプレート互換用に created_at を仮で入れる
    for _iv in interviews:
        try:
            if getattr(_iv, 'scheduled_at', None) is None:
                setattr(_iv, 'scheduled_at', _iv.created_at)
        except Exception:
            pass
    evaluations = []
    # Evaluations are per-interview; fetch all evaluations for interviews belonging to this candidate
    interview_ids = [i.id for i in interviews] if interviews else []
    evaluations = Evaluation.query.filter(Evaluation.interview_id.in_(interview_ids)).order_by(Evaluation.created_at.desc()).all() if interview_ids else []

    # latest overall evaluation for this candidate (if any)
    overall = CandidateOverallEvaluation.query.filter_by(candidate_id=c.id, org_id=c.org_id).order_by(CandidateOverallEvaluation.created_at.desc()).first()

    # files for this candidate
    files = Files.query.filter_by(candidate_id=c.id).order_by(Files.created_at.desc()).all()

    return render_template("candidates/detail.html",
                           c=c, app_row=app_row, form=form,
                           stage_form=stage_form,
                           interviews=interviews, evaluations=evaluations,
                           apps=[],
                           overall=overall, files=files)


@bp.post('/<int:candidate_id>/upload_resume')
@login_required
def upload_resume(candidate_id):
    c = Candidate.query.filter_by(id=candidate_id, org_id=current_user.org_id).first_or_404()
    files = request.files.getlist('resume')
    if not files:
        flash('ファイルが選択されていません', 'warning')
        return redirect(url_for('candidates.detail', candidate_id=c.id))

    created_ids = []
    for f in files:
        if not f or getattr(f, 'filename', '') == '':
            continue
        url = save_file(f, prefix=f"org{current_user.org_id}/candidate{c.id}")
        meta = {'filename': getattr(f, 'filename', ''), 'size': None, 'content_type': getattr(f, 'mimetype', '')}
        file_row = Files(org_id=current_user.org_id, kind='resume', storage_url=url, file_metadata=meta, candidate_id=c.id)
        db.session.add(file_row)
        db.session.flush()
        created_ids.append(file_row.id)

    db.session.commit()

    # If candidate has no resume_file_id set, set it to the first uploaded file
    if created_ids and not c.resume_file_id:
        c.resume_file_id = created_ids[0]
        db.session.add(c)
        db.session.commit()

    flash('履歴書をアップロードしました', 'success')
    return redirect(url_for('candidates.detail', candidate_id=c.id))


@bp.get('/<int:candidate_id>/files')
@login_required
def list_files(candidate_id):
    c = Candidate.query.filter_by(id=candidate_id, org_id=current_user.org_id).first_or_404()
    files = Files.query.filter_by(candidate_id=c.id).order_by(Files.created_at.desc()).all()
    return render_template('candidates/files.html', c=c, files=files)


@bp.get('/<int:candidate_id>/files/<int:file_id>/download')
@login_required
def download_file(candidate_id, file_id):
    f = Files.query.filter_by(id=file_id, candidate_id=candidate_id, org_id=current_user.org_id).first_or_404()
    data = download_bytes(f.storage_url)
    filename = f.filename or f"file_{f.id}"
    return send_file(io.BytesIO(data), as_attachment=True, download_name=filename, mimetype=f.file_metadata.get('content_type') if f.file_metadata else 'application/octet-stream')


@bp.get('/<int:candidate_id>/files/<int:file_id>/view')
@login_required
def view_file(candidate_id, file_id):
    f = Files.query.filter_by(id=file_id, candidate_id=candidate_id, org_id=current_user.org_id).first_or_404()
    # try preview extraction for office files
    try:
        preview = render_preview(f)
        if preview:
            mimetype, data_bytes, filename = preview
            return send_file(io.BytesIO(data_bytes), as_attachment=False, download_name=filename, mimetype=mimetype)
    except Exception:
        # fall back to raw bytes
        pass

    # default: return raw bytes (PDF/text/etc.)
    data = download_bytes(f.storage_url)
    mimetype = f.file_metadata.get('content_type') if f.file_metadata else mimetypes.guess_type(f.filename or '')[0] or 'application/octet-stream'
    return send_file(io.BytesIO(data), as_attachment=False, download_name=f.filename or f"file_{f.id}", mimetype=mimetype)


@bp.get('/<int:candidate_id>/evaluation')
@login_required
def overall_evaluation(candidate_id):
    # Show latest overall evaluation for this candidate
    overall = None
    try:
        # allow forcing a recompute via ?recompute=1
        recompute = request.args.get('recompute')
        overall = CandidateOverallEvaluation.query.filter_by(candidate_id=candidate_id, org_id=current_user.org_id).order_by(CandidateOverallEvaluation.created_at.desc()).first()

        if recompute or not overall:
            # gather evaluations for this candidate (via interviews)
            interviews = Interview.query.filter_by(candidate_id=candidate_id, org_id=current_user.org_id).all()
            interview_ids = [i.id for i in interviews] if interviews else []
            evaluations = []
            if interview_ids:
                evaluations = Evaluation.query.filter(Evaluation.org_id==current_user.org_id, Evaluation.interview_id.in_(interview_ids)).order_by(Evaluation.created_at.desc()).all()

            if evaluations:
                # compute averages for known numeric fields
                metrics_keys = ['overall_score', 'speaking', 'logical', 'volume', 'honesty', 'proactive']
                sums = {k: 0.0 for k in metrics_keys}
                counts = {k: 0 for k in metrics_keys}
                for ev in evaluations:
                    for k in metrics_keys:
                        v = getattr(ev, k, None)
                        try:
                            if v is not None:
                                sums[k] += float(v)
                                counts[k] += 1
                        except Exception:
                            pass
                avgs = {}
                for k in metrics_keys:
                    avgs[k] = (sums[k] / counts[k]) if counts[k] > 0 else None

                # create aggregated gpt_summary by joining recent summaries
                summaries = [ev.gpt_summary for ev in evaluations if ev.gpt_summary]
                gpt_summary = '\n---\n'.join(summaries[:5]) if summaries else None

                # aggregated_from ids
                agg_ids = [ev.id for ev in evaluations]

                # determine version
                latest_version = 0
                prev = CandidateOverallEvaluation.query.filter_by(candidate_id=candidate_id, org_id=current_user.org_id).order_by(CandidateOverallEvaluation.created_at.desc()).first()
                if prev and prev.version:
                    latest_version = int(prev.version)
                version = latest_version + 1

                # create and persist
                new_overall = CandidateOverallEvaluation(
                    org_id=current_user.org_id,
                    candidate_id=candidate_id,
                    version=version,
                    aggregated_from=agg_ids,
                    overall_score=avgs.get('overall_score'),
                    speaking=avgs.get('speaking'),
                    logical=avgs.get('logical'),
                    volume=avgs.get('volume'),
                    honesty=avgs.get('honesty'),
                    proactive=avgs.get('proactive'),
                    gpt_summary=gpt_summary,
                )
                db.session.add(new_overall)
                db.session.commit()
                overall = new_overall
    except Exception:
        overall = None
    return render_template('candidates/evaluation.html', overall=overall)