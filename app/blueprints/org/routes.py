from flask import jsonify, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from . import bp
from ...models.setting import Setting
from ...extensions import db
from ...utils.decorators import admin_required
from flask import send_file
import json
from io import BytesIO
from ...models.user import User
from ...models.candidate import Candidate
from ...models.interview import Interview
from ...models.transcript import Transcript
from ...models.evaluation import Evaluation
import csv
from datetime import datetime, date
from io import BytesIO, StringIO
import json as _json


@bp.get("/me")
@login_required
def org_me():
    return jsonify({"org_id": current_user.org_id})


@bp.route('/settings', methods=['GET'])
@login_required
def org_settings():
    # Render the management cards page. Detailed setting pages are separate.
    return render_template('org/settings.html')


@bp.route('/heuristic', methods=['GET', 'POST'])
@login_required
@admin_required
def heuristic_settings():
    """Heuristic configuration editor (moved from /settings)."""
    org_id = current_user.org_id
    ctx = {
        'HEURISTIC_WEIGHT_AI': current_app.config.get('HEURISTIC_WEIGHT_AI', 0.6),
        'HEURISTIC_WEIGHT_H': current_app.config.get('HEURISTIC_WEIGHT_H', 0.4),
        'DG_WORD_GAP_THRESHOLD': current_app.config.get('DG_WORD_GAP_THRESHOLD', 0.35),
        'FILLER_TOKENS': current_app.config.get('FILLER_TOKENS', 'えー,あの,えっと,うーん,うー,あー,um,uh'),
    }
    try:
        rows = Setting.query.filter_by(org_id=org_id).all()
        for r in rows:
            if r.key in ctx and r.value is not None:
                if r.key in ('HEURISTIC_WEIGHT_AI', 'HEURISTIC_WEIGHT_H', 'DG_WORD_GAP_THRESHOLD'):
                    try:
                        ctx[r.key] = float(r.value)
                        current_app.config[r.key] = ctx[r.key]
                    except Exception:
                        ctx[r.key] = r.value
                else:
                    ctx[r.key] = r.value
                    current_app.config[r.key] = r.value
    except Exception:
        pass

    if request.method == 'POST':
        try:
            ai = float(request.form.get('HEURISTIC_WEIGHT_AI', ctx['HEURISTIC_WEIGHT_AI']))
            h = float(request.form.get('HEURISTIC_WEIGHT_H', ctx['HEURISTIC_WEIGHT_H']))
            gap = float(request.form.get('DG_WORD_GAP_THRESHOLD', ctx['DG_WORD_GAP_THRESHOLD']))
            fillers = request.form.get('FILLER_TOKENS', ctx['FILLER_TOKENS'])

            current_app.config['HEURISTIC_WEIGHT_AI'] = ai
            current_app.config['HEURISTIC_WEIGHT_H'] = h
            current_app.config['DG_WORD_GAP_THRESHOLD'] = gap
            current_app.config['FILLER_TOKENS'] = fillers

            for k, v in (('HEURISTIC_WEIGHT_AI', str(ai)), ('HEURISTIC_WEIGHT_H', str(h)), ('DG_WORD_GAP_THRESHOLD', str(gap)), ('FILLER_TOKENS', fillers)):
                s = Setting.query.filter_by(org_id=org_id, key=k).first()
                if s:
                    s.value = v
                else:
                    s = Setting(org_id=org_id, key=k, value=v)
                    db.session.add(s)
            db.session.commit()

            flash('設定を更新しました（保存済み）', 'success')
            return redirect(url_for('.heuristic_settings'))
        except Exception:
            flash('入力値に誤りがあります', 'danger')

    return render_template('org/heuristic.html', **ctx)


@bp.route('/export', methods=['GET','POST'])
@login_required
@admin_required
def export_data():
    # GET: render the selection form. POST: export selected tables as JSON
    from ...models.candidate_overall_evaluation import CandidateOverallEvaluation

    if request.method == 'GET':
        return render_template('org/export.html')

    selected = request.form.getlist('tables')
    if not selected:
        flash('少なくとも1つのテーブルを選択してください', 'warning')
        return redirect(url_for('.export_data'))

    payload = {}
    try:
        if 'users' in selected:
            payload['users'] = [ {c.name: getattr(u, c.name) for c in u.__table__.columns} for u in User.query.filter_by(org_id=current_user.org_id).all() ]
        if 'candidates' in selected:
            payload['candidates'] = [ {c.name: getattr(x, c.name) for c in x.__table__.columns} for x in Candidate.query.filter_by(org_id=current_user.org_id).all() ]
        if 'interviews' in selected:
            payload['interviews'] = [ {c.name: getattr(x, c.name) for c in x.__table__.columns} for x in Interview.query.filter_by(org_id=current_user.org_id).all() ]
        if 'transcripts' in selected:
            payload['transcripts'] = [ {c.name: getattr(x, c.name) for c in x.__table__.columns} for x in Transcript.query.filter_by(org_id=current_user.org_id).all() ]
        if 'evaluations' in selected:
            payload['evaluations'] = [ {c.name: getattr(x, c.name) for c in x.__table__.columns} for x in Evaluation.query.filter_by(org_id=current_user.org_id).all() ]
        if 'candidate_overall_evaluations' in selected:
            payload['candidate_overall_evaluations'] = [ {c.name: getattr(x, c.name) for c in x.__table__.columns} for x in CandidateOverallEvaluation.query.filter_by(org_id=current_user.org_id).all() ]
    except Exception as e:
        return (f"Export failed: {e}", 500)

    bio = BytesIO()
    bio.write(json.dumps(payload, default=str, ensure_ascii=False, indent=2).encode('utf-8'))
    bio.seek(0)
    return send_file(bio, as_attachment=True, download_name='export.json', mimetype='application/json')


@bp.route('/import', methods=['GET','POST'])
@login_required
@admin_required
def import_data():
    if request.method == 'GET':
        return render_template('org/import.html')
    f = request.files.get('file')
    if not f:
        flash('ファイルが選択されていません', 'warning')
        return redirect(url_for('.org_settings'))
    filename = getattr(f, 'filename', '') or ''
    try:
        # If CSV, parse rows
        if filename.lower().endswith('.csv') or f.mimetype in ('text/csv', 'application/csv'):
            stream = (line.decode('utf-8') for line in f.stream)
            reader = csv.DictReader(stream)
            created = 0
            for row in reader:
                # map row keys to Candidate columns
                cols = {c.name for c in Candidate.__table__.columns}
                data = {}
                for k, v in row.items():
                    if k not in cols or v is None or v == '':
                        continue
                    # simple type conversions
                    if k in ('grad_year',):
                        try:
                            data[k] = int(v)
                        except Exception:
                            continue
                    elif k in ('birthdate','applied_at','offer_date','acceptance_date','join_date','decline_date'):
                        try:
                            data[k] = datetime.strptime(v, '%Y-%m-%d').date()
                        except Exception:
                            try:
                                data[k] = datetime.strptime(v, '%Y/%m/%d').date()
                            except Exception:
                                continue
                    elif k in ('qualifications','languages','skills'):
                        try:
                            data[k] = _json.loads(v)
                        except Exception:
                            # allow simple comma-separated list for qualifications/skills
                            data[k] = [s.strip() for s in v.split(',') if s.strip()]
                    else:
                        data[k] = v
                if data:
                    c = Candidate(org_id=current_user.org_id, **data)
                    db.session.add(c)
                    created += 1
            db.session.commit()
            flash(f'CSVインポート完了: {created} 件作成しました', 'success')
        else:
            # fallback: try JSON import (legacy)
            payload = _json.load(f.stream)
            if 'candidates' in payload:
                for row in payload['candidates']:
                    Candidate(**{k: v for k, v in row.items() if k in [c.name for c in Candidate.__table__.columns]} )
            db.session.commit()
            flash('JSONインポート完了（簡易）', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'インポート失敗: {e}', 'danger')
    return redirect(url_for('.org_settings'))


@bp.get('/import/template')
@login_required
@admin_required
def import_template():
    # provide a CSV template for Candidate import
    headers = [c.name for c in Candidate.__table__.columns]
    # Use a text buffer then convert to bytes for send_file
    text_buf = StringIO()
    writer = csv.writer(text_buf)
    writer.writerow(headers)
    # add an example row for guidance (values are example only)
    writer.writerow(['山田太郎','やまだたろう','taro@example.com','090-0000-0000','1990-01-01','','','エンジニア','2020','現職','履歴の説明','["基本情報"]','[{"lang":"JP","level":"N1"}]','["Python"]','2025-01-01','applied','','2025-01-01','', ''])
    data = text_buf.getvalue().encode('utf-8')
    bio = BytesIO(data)
    bio.seek(0)
    return send_file(bio, as_attachment=True, download_name='candidates_import_template.csv', mimetype='text/csv')