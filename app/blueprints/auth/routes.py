from flask import current_app, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from . import bp
from ...extensions import db
from .forms import LoginForm, SignupForm
from ...models.organization import Organization
from ...models.user import User
from ...utils.decorators import admin_required

@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for("index"))
        flash("Invalid credentials", "danger")
    return render_template("login.html", form=form)

@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))

@bp.route("/signup", methods=["GET", "POST"])
def signup():
    """初回: 誰でも作成可。以降: admin のみ可。"""
    form = SignupForm()
    # 既にユーザーが存在するか
    user_exists = User.query.first() is not None
    if user_exists and (not current_user.is_authenticated or current_user.role != "admin"):
        # 管理者以外は作成不可
        from flask import abort
        return abort(403)

    if form.validate_on_submit():
        # 既存 org / user の重複チェックは最低限
        org = Organization.query.filter_by(name=form.org_name.data).first()
        if not org:
            org = Organization(name=form.org_name.data)
            db.session.add(org)
            db.session.flush()
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            from flask import flash
            flash("既に同じメールのユーザーが存在します", "danger")
        else:
            user = User(org_id=org.id, email=form.email.data, role="admin")
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            from flask import flash, redirect, url_for
            flash("管理者アカウントを作成しました。ログインしてください。", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/signup.html", form=form, user_exists=user_exists)

@bp.route("/users", methods=["GET"]) 
@admin_required
def users_index():
    users = User.query.all()
    return render_template("auth/users.html", users=users)