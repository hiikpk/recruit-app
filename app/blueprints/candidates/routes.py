from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from . import bp
from .forms import CandidateForm, ApplicationStageForm
from ...extensions import db
from ...models.candidate import Candidate
from ...models.evaluation import Evaluation
from ...models.application import Application
from ...models.interview import Interview
from datetime import datetime

@bp.get("")
@login_required
def list_candidates():
    q = request.args.get("q")
    query = Candidate.query.filter_by(org_id=current_user.org_id)
    if q:
        like = f"%{q}%"
        query = query.filter(Candidate.name.ilike(like))
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
            email=form.email.data,
            birthdate=form.birthdate.data,
            applied_at=form.applied_at.data,
            school=form.school.data,
            grad_year=form.grad_year.data,
            qualifications=form.qualifications.data,
            skills=form.skills.data,
            languages=form.languages.data,
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
    apps = Application.query.filter_by(org_id=c.org_id, candidate_id=c.id)\
                            .order_by(Application.id.desc()).all()
    if app_row:
        interviews = Interview.query.filter_by(org_id=c.org_id, application_id=app_row.id)\
                                    .order_by(Interview.scheduled_start.desc()).all()
        evaluations = Evaluation.query.filter_by(org_id=c.org_id, application_id=app_row.id)\
                                      .order_by(Evaluation.created_at.desc()).all()

    return render_template("candidates/detail.html",
                           c=c, app_row=app_row, form=form,
                           stage_form=stage_form,
                           interviews=interviews, evaluations=evaluations,
                           apps=apps)