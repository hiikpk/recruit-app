from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from . import bp
from .forms import CandidateForm, ApplicationStageForm
from ...extensions import db
from ...models.candidate import Candidate
from ...models.evaluation import Evaluation
from ...models.application import Application
from ...models.interview import Interview
from ...models.candidate_overall_evaluation import CandidateOverallEvaluation
from datetime import datetime

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

    items = query.order_by(Candidate.id.desc()).all()
    return render_template("candidates/list.html", items=items)

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
            grad_year=form.grad_year.data,
            current_job=form.current_job.data,
            resume_file_id=form.resume_file_id.data,
            qualifications=form.qualifications.data,
            skills=form.skills.data,
            languages=form.languages.data,
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
    # application_idが指定されていればその応募を表示。なければ最新1件（MVP）。
    app_id = request.args.get("application_id", type=int)
    if app_id:
        # 指定の応募が見つからない場合は最新の応募にフォールバック
        app_row = Application.query.filter_by(id=app_id, org_id=c.org_id, candidate_id=c.id).first()
        if not app_row:
            app_row = Application.query.filter_by(org_id=c.org_id, candidate_id=c.id)\
                                       .order_by(Application.id.desc()).first()
    else:
        app_row = Application.query.filter_by(org_id=c.org_id, candidate_id=c.id)\
                                   .order_by(Application.id.desc()).first()

    form = CandidateForm(obj=c)
    stage_form = None
    if app_row:
        stage_form = ApplicationStageForm(stage=app_row.stage, status=app_row.status)

    if form.validate_on_submit() and request.form.get("form_name") == "profile":
        form.populate_obj(c)
        if not c.applied_at:
            c.applied_at = datetime.utcnow()
        db.session.commit()
        flash("基本情報を更新しました", "success")
        return redirect(url_for("candidates.detail", candidate_id=c.id))

    if stage_form and stage_form.validate_on_submit() and request.form.get("form_name") == "stage":
        app_row.stage = stage_form.stage.data
        app_row.status = stage_form.status.data
        db.session.commit()
        flash("選考ステータスを更新しました", "success")
        return redirect(url_for("candidates.detail", candidate_id=c.id))

    interviews = []
    evaluations = []
    # 全応募（ヘッダーの切り替え用）
    apps = (Application.query.filter_by(org_id=c.org_id, candidate_id=c.id)
            .order_by(Application.id.desc()).all())
    # Fetch interviews for this candidate directly (no application linkage)
    interviews = Interview.query.filter_by(org_id=c.org_id, candidate_id=c.id).order_by(Interview.scheduled_at.desc()).all()
    # Evaluations are per-interview; fetch all evaluations for interviews belonging to this candidate
    interview_ids = [i.id for i in interviews] if interviews else []
    evaluations = Evaluation.query.filter(Evaluation.interview_id.in_(interview_ids)).order_by(Evaluation.created_at.desc()).all() if interview_ids else []

    # latest overall evaluation for this candidate (if any)
    overall = CandidateOverallEvaluation.query.filter_by(candidate_id=c.id, org_id=c.org_id).order_by(CandidateOverallEvaluation.created_at.desc()).first()

    return render_template("candidates/detail.html",
                           c=c, app_row=app_row, form=form,
                           stage_form=stage_form,
                           interviews=interviews, evaluations=evaluations,
                           apps=apps, overall=overall)


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