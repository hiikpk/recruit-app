from flask import Flask
from flask_migrate import Migrate
from .extensions import db, login_manager, rq

migrate = Migrate()  # 追加

def create_app():
    """Minimal app factory for import-safety.

    Keep handlers small and avoid heavy DB code so imports succeed while we
    repair and test the full dashboard implementation.
    """
    app = Flask(__name__)
    app.config.from_object('config.Config')

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    rq.init_app(app)

    # minimal user loader (lazy import)
    @login_manager.user_loader
    def load_user(user_id):
        try:
            from .models.user import User
            return User.query.get(int(user_id))
        except Exception:
            return None

    # register existing blueprints individually so one bad blueprint
    # doesn't prevent others from loading
    try:
        from .blueprints.auth import bp as auth_bp
        app.register_blueprint(auth_bp, url_prefix="/auth")
    except Exception:
        pass

    try:
        from .blueprints.candidates import bp as candidates_bp
        app.register_blueprint(candidates_bp, url_prefix="/candidates")
    except Exception:
        pass

    try:
        from .blueprints.interviews import bp as interviews_bp
        app.register_blueprint(interviews_bp, url_prefix="/interviews")
    except Exception:
        pass

    try:
        from .blueprints.org import bp as org_bp
        app.register_blueprint(org_bp, url_prefix="/org")
    except Exception:
        pass

    try:
        # jobs blueprint may be missing routes.py in some states; import safely
        from .blueprints.jobs import bp as jobs_bp
        app.register_blueprint(jobs_bp, url_prefix="/jobs")
    except Exception:
        pass

    @app.get('/')
    def index():
        from flask_login import current_user
        from flask import redirect, url_for, render_template, request
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        # provide safe defaults for template variables (stats, series)
        stats = {'candidates': 0, 'interviews': 0}
        series = {'labels': [], 'applicants': [], 'hires_months': [], 'hires': []}

        try:
            # attempt to fetch lightweight stats if DB available
            from .models.candidate import Candidate
            from .models.application import Application
            from .models.interview import Interview
            from .models.evaluation import Evaluation
            from sqlalchemy import func, cast, Date
            from datetime import date, datetime, timedelta

            org_id = current_user.org_id
            stats = {
                'candidates': Candidate.query.filter_by(org_id=org_id).count(),
                'applications': Application.query.filter_by(org_id=org_id).count(),
                'interviews': Interview.query.filter_by(org_id=org_id).count(),
                'evaluations': Evaluation.query.filter_by(org_id=org_id).count(),
            }

            # build simple last-30-days applicants series from Candidate.applied_at
            try:
                end_date = date.today()
                start_date = end_date - timedelta(days=29)
                # Use candidates.applied_at since some records may not have Application rows
                daily_q = (
                    Candidate.query.with_entities(func.date(Candidate.applied_at).label('d'), func.count(Candidate.id).label('cnt'))
                    .filter(Candidate.org_id == org_id)
                    .filter(Candidate.applied_at != None)
                    .filter(func.date(Candidate.applied_at) >= start_date.isoformat())
                    .filter(func.date(Candidate.applied_at) <= end_date.isoformat())
                    .group_by('d')
                    .order_by('d')
                ).all()
                daily_map = {r.d: r.cnt for r in daily_q}
                cur = start_date
                labels = []
                applicants = []
                while cur <= end_date:
                    labels.append(f"{cur.month}/{cur.day}")
                    # daily_map keys are ISO date strings like '2025-08-16'
                    applicants.append(daily_map.get(cur.isoformat(), 0))
                    cur = cur + timedelta(days=1)
                series['labels'] = labels
                series['applicants'] = applicants
            except Exception:
                pass
        except Exception:
            # DB may not be available during stabilization; keep defaults
            pass

        # ensure series keys exist
        series.setdefault('labels', [])
        series.setdefault('applicants', [])

        # Robust aggregation: prefer Candidate.applied_at, but also include Application.created_at
        try:
            # build last-30-days map using both sources
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            # candidate-based counts
            cand_q = (
                Candidate.query.with_entities(func.date(Candidate.applied_at).label('d'), func.count(Candidate.id).label('cnt'))
                .filter(Candidate.org_id == org_id)
                .filter(Candidate.applied_at != None)
                .filter(func.date(Candidate.applied_at) >= start_date.isoformat())
                .filter(func.date(Candidate.applied_at) <= end_date.isoformat())
                .group_by('d')
            ).all()

            # application-based counts for candidates without applied_at
            app_q = (
                Application.query.with_entities(func.date(Application.created_at).label('d'), func.count(Application.id).label('cnt'))
                .filter(Application.org_id == org_id)
                .filter(func.date(Application.created_at) >= start_date.isoformat())
                .filter(func.date(Application.created_at) <= end_date.isoformat())
                .group_by('d')
            ).all()

            daily_map = {}
            for r in cand_q:
                daily_map[str(r.d)] = daily_map.get(str(r.d), 0) + int(r.cnt)
            for r in app_q:
                daily_map[str(r.d)] = daily_map.get(str(r.d), 0) + int(r.cnt)

            cur = start_date
            labels = []
            applicants = []
            while cur <= end_date:
                labels.append(f"{cur.month}/{cur.day}")
                applicants.append(daily_map.get(cur.isoformat(), 0))
                cur = cur + timedelta(days=1)
            series['labels'] = labels
            series['applicants'] = applicants
        except Exception:
            # if anything fails, keep defaults previously set
            pass

        return render_template('home.html', stats=stats, series=series)

    @app.get('/dashboard-2')
    def dashboard_2():
        # full aggregation: parse filters, compute yields and pie charts
        from flask_login import current_user
        from flask import redirect, url_for, render_template, request
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        from .models.candidate import Candidate
        from .models.interview import Interview
        from sqlalchemy import func
        from datetime import date, datetime, timedelta

        org_id = current_user.org_id

        # parse date range (apply to candidate.applied_at)
        try:
            start_str = request.args.get('start')
            end_str = request.args.get('end')
            if start_str:
                start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            else:
                start_date = date.today() - timedelta(days=29)
            if end_str:
                end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
            else:
                end_date = date.today()
        except Exception:
            start_date = date.today() - timedelta(days=29)
            end_date = date.today()

        # options for selects
        channel_q = (
            Candidate.query.with_entities(func.coalesce(Candidate.channel, 'Unknown').label('k'), func.count(Candidate.id).label('cnt'))
            .filter(Candidate.org_id == org_id)
            .group_by('k')
            .order_by(func.count(Candidate.id).desc())
            .limit(100)
        ).all()
        channels = [r.k for r in channel_q]

        pos_q = (
            Candidate.query.with_entities(func.coalesce(Candidate.applying_position, 'Unknown').label('k'), func.count(Candidate.id).label('cnt'))
            .filter(Candidate.org_id == org_id)
            .group_by('k')
            .order_by(func.count(Candidate.id).desc())
            .limit(100)
        ).all()
        positions = [r.k for r in pos_q]

        # compute decades & genders
        today = date.today()
        cand_all = Candidate.query.filter_by(org_id=org_id).all()
        decade_map = {}
        gender_counts = {'男性': 0, '女性': 0, '不明': 0}
        for c in cand_all:
            if not c.birthdate:
                dkey = '不明'
            else:
                age = today.year - c.birthdate.year
                dkey = f"{(age//10)*10}代"
            decade_map[dkey] = decade_map.get(dkey, 0) + 1
            g = getattr(c, 'gender', None)
            if g:
                if g in ('male', '男性'):
                    gender_counts['男性'] += 1
                elif g in ('female', '女性'):
                    gender_counts['女性'] += 1
                else:
                    gender_counts['不明'] += 1
            else:
                gender_counts['不明'] += 1

        decades = list(decade_map.keys())
        genders = list(gender_counts.keys())

        # selected values (single-select in current template)
        sel_channel = request.args.get('channel') or ''
        sel_position = request.args.get('position') or ''
        sel_decade = request.args.get('decade') or ''
        sel_gender = request.args.get('gender') or ''

        # filter candidates according to selections
        filtered = []
        for c in cand_all:
            if c.applied_at and (c.applied_at < start_date or c.applied_at > end_date):
                continue
            if sel_channel and (c.channel != sel_channel):
                continue
            if sel_position and (c.applying_position != sel_position):
                continue
            if sel_decade:
                if not c.birthdate:
                    if sel_decade != '不明':
                        continue
                else:
                    age = today.year - c.birthdate.year
                    key = f"{(age//10)*10}代"
                    if key != sel_decade:
                        continue
            if sel_gender:
                g = getattr(c, 'gender', None)
                if g in ('male', '男性'):
                    kg = '男性'
                elif g in ('female', '女性'):
                    kg = '女性'
                else:
                    kg = '不明'
                if kg != sel_gender:
                    continue
            filtered.append(c)

        filtered_ids = [c.id for c in filtered]

        # yields
        if filtered_ids:
            total_applications = len(filtered_ids)
            doc_pass_q = Interview.query.filter(Interview.org_id == org_id, Interview.candidate_id.in_(filtered_ids), Interview.step == 'document', func.coalesce(Interview.result, '') == 'pass').count()
            first_pass_q = Interview.query.filter(Interview.org_id == org_id, Interview.candidate_id.in_(filtered_ids), Interview.step == 'first', func.coalesce(Interview.result, '') == 'pass').count()
            second_pass_q = Interview.query.filter(Interview.org_id == org_id, Interview.candidate_id.in_(filtered_ids), Interview.step == 'second', func.coalesce(Interview.result, '') == 'pass').count()
            offer_q = Interview.query.filter(Interview.org_id == org_id, Interview.candidate_id.in_(filtered_ids), func.coalesce(Interview.result, '') == 'offer').count()
            accepted_q = Candidate.query.filter(Candidate.org_id == org_id, Candidate.id.in_(filtered_ids), Candidate.acceptance_date != None).count()
        else:
            total_applications = 0
            doc_pass_q = first_pass_q = second_pass_q = offer_q = accepted_q = 0

        yield_labels = ['応募数', '書類合格', '一次合格', '二次合格', '内定', '内定承諾']
        yield_values = [total_applications, doc_pass_q, first_pass_q, second_pass_q, offer_q, accepted_q]

        def top_group(field, source_list):
            m = {}
            for c in source_list:
                key = getattr(c, field) or 'Unknown'
                m[key] = m.get(key, 0) + 1
            items = sorted(m.items(), key=lambda x: x[1], reverse=True)
            labels = [x[0] for x in items]
            vals = [x[1] for x in items]
            return labels, vals

        pie_source = filtered if filtered else cand_all
        channels_labels, channels_vals = top_group('channel', pie_source)
        positions_labels, positions_vals = top_group('applying_position', pie_source)
        decades_labels = list(decade_map.keys())
        decades_vals = [decade_map[k] for k in decades_labels]
        genders_labels = list(gender_counts.keys())
        genders_vals = [gender_counts[k] for k in genders_labels]

        charts = {
            'yield': {'labels': yield_labels, 'values': yield_values},
            'channels': {'labels': channels_labels, 'values': channels_vals},
            'positions': {'labels': positions_labels, 'values': positions_vals},
            'decades': {'labels': decades_labels, 'values': decades_vals},
            'genders': {'labels': genders_labels, 'values': genders_vals},
        }

        options = {'channels': channels, 'positions': positions, 'decades': decades, 'genders': genders}
        selected = {'channels': [sel_channel] if sel_channel else [], 'positions': [sel_position] if sel_position else [], 'decades': [sel_decade] if sel_decade else [], 'genders': [sel_gender] if sel_gender else [], 'start': start_date.isoformat(), 'end': end_date.isoformat()}

        return render_template('dashboard_2.html', charts=charts, options=options, selected=selected)

    return app
