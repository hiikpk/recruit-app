from flask import Flask
from .extensions import db, login_manager
from .extensions import rq


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # init extensions
    db.init_app(app)
    login_manager.init_app(app)
    rq.init_app(app)

    # import models and blueprints lazily to avoid circular imports
    from . import models  # ensure all models are registered
    from .models.user import User
    from .blueprints.auth import bp as auth_bp
    from .blueprints.candidates import bp as candidates_bp
    from .blueprints.interviews import bp as interviews_bp
    from .blueprints.org import bp as org_bp

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(candidates_bp, url_prefix="/candidates")
    app.register_blueprint(interviews_bp, url_prefix="/interviews")
    app.register_blueprint(org_bp, url_prefix="/org")

    with app.app_context():
        db.create_all()

    # @app.get("/")
    # def index():
    #     from flask_login import current_user
    #     if not current_user.is_authenticated:
    #         from flask import redirect, url_for
    #         return redirect(url_for("auth.login"))
    #     return "OK: Logged in as %s" % current_user.email

    @app.get("/")
    def index():
        from flask_login import current_user
        from flask import redirect, url_for, render_template
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        # 集計（件数）
        from .models.candidate import Candidate
        from .models.application import Application
        from .models.interview import Interview
        from .models.evaluation import Evaluation
        org_id = current_user.org_id
        stats = {
            "candidates": Candidate.query.filter_by(org_id=org_id).count(),
            "applications": Application.query.filter_by(org_id=org_id).count(),
            "interviews": Interview.query.filter_by(org_id=org_id).count(),
            "evaluations": Evaluation.query.filter_by(org_id=org_id).count(),
        }
        # ===== サンプルの時系列データ（週次×12） =====
        from datetime import date, timedelta
        base = date.today()
        labels = []
        applicants = []
        passes = []
        # 12週分（古い→新しい順）
        for w in range(11, -1, -1):
            d = base - timedelta(weeks=w)
            # Cross-platform format (Windows doesn't support %-m/%-d)
            labels.append(f"{d.month}/{d.day}")
            # 仮のデータ（あとでDB集計に置換）
            applicants.append(8 + ((11 - w) * 2) % 7)  # 変化が見える程度の疑似値
            passes.append(max(0, applicants[-1] - (3 + ((w * 2) % 5))))
        series = {"labels": labels, "applicants": applicants, "passes": passes}
        return render_template("home.html", stats=stats, series=series)
    
    return app