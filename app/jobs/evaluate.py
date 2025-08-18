from ..extensions import db
from ..services.openai_wrap import gen_evaluation
from ..models.evaluation import Evaluation
from ..models.application import Application
from ..models.interview import Interview
from datetime import datetime
from flask import current_app


def compute_heuristic_scores(metrics, rubric):
    """Compute simple heuristic scores (0-5) from speaking metrics.

    Returns a dict keyed by rubric labels. If a rubric cannot be estimated,
    value may be None.
    """
    if not metrics:
        return {r: None for r in rubric}

    # pick the speaker with largest speaking ratio as candidate
    spk_metrics = None
    try:
        spks = metrics.get('speakers') or {}
        if spks:
            # pick max ratio
            best = max(spks.items(), key=lambda kv: kv[1].get('ratio', 0))
            spk_metrics = best[1]
    except Exception:
        spk_metrics = None

    total_time = metrics.get('total_time_sec') or 0
    avg_silence = metrics.get('avg_silence_sec') or 0
    interruptions = metrics.get('interruptions') or 0
    filler_rate = metrics.get('filler_rate') or 0.0

    # derive primitive scores
    speaking_ratio = spk_metrics.get('ratio') if spk_metrics else 0
    cpm = spk_metrics.get('cpm') if spk_metrics else 0
    avg_turn = spk_metrics.get('avg_turn_sec') if spk_metrics else None

    # map primitives to 0-5
    speaking_ratio_score = max(0.0, min(5.0, speaking_ratio * 5.0))
    cpm_score = max(0.0, min(5.0, (cpm / 150.0)))  # rough scaling: 150cpm -> 1
    silence_penalty = avg_silence * 0.5
    interruption_penalty = interruptions * 0.5
    filler_penalty = filler_rate * 5.0

    # compute composite speaking score
    raw_speaking = (speaking_ratio_score * 0.6 + cpm_score * 0.4) - (silence_penalty + interruption_penalty + filler_penalty)
    speaking_score = max(0.0, min(5.0, raw_speaking))

    # logical: longer turns with reasonable cpm suggest logical flow
    logical_score = None
    if avg_turn is not None and avg_turn > 0:
        logical_score = max(0.0, min(5.0, 5.0 - abs(avg_turn - 3.0)))
    else:
        logical_score = max(0.0, min(5.0, 3.0 - filler_penalty))

    # volume / honesty / proactive are noisy; derive mild heuristics
    volume_score = max(0.0, min(5.0, 4.0 - (filler_penalty * 0.5)))
    honesty_score = max(0.0, min(5.0, 4.0 - (interruptions * 0.2)))
    proactive_score = max(0.0, min(5.0, speaking_ratio_score - filler_penalty))

    # map results to rubric labels
    out = {}
    for r in rubric:
        key = r.lower()
        if 'speaking' in key or 'コミュ' in r or 'コミュ力' in r:
            out[r] = round(speaking_score, 2)
        elif 'logical' in key or 'ロジ' in r:
            out[r] = round(logical_score, 2)
        elif 'volume' in key or '音量' in r:
            out[r] = round(volume_score, 2)
        elif 'honesty' in key or '誠実' in r:
            out[r] = round(honesty_score, 2)
        elif 'proactive' in key or '積極' in r:
            out[r] = round(proactive_score, 2)
        elif '技術' in r or 'technical' in key:
            # cannot infer technical skill from speech metrics
            out[r] = None
        else:
            out[r] = None
    return out


def _run_evaluate_application(app_id: int):
    app_row = Application.query.get(app_id)
    if not app_row:
        return None
    # try to find latest transcript text and metrics for this candidate's latest interview
    transcript = app_row.latest_transcript_text()
    metrics = None
    try:
        interview = Interview.query.filter_by(candidate_id=app_row.candidate_id).order_by(Interview.created_at.desc()).first()
        if interview:
            q = db.text(
                """
                SELECT t.text, t.metrics FROM transcripts t
                JOIN recordings r ON r.id = t.recording_id
                WHERE r.interview_id = :int_id
                ORDER BY t.created_at DESC
                LIMIT 1
                """
            )
            res = db.session.execute(q, {"int_id": interview.id}).fetchone()
            if res:
                transcript = res[0] or transcript
                metrics = res[1]
    except Exception:
        metrics = None

    payload = {
        "rubric": ["コミュ力(5)", "技術(5)", "ロジカル(5)", "カルチャー(5)"],
        "transcript": transcript,
        "metrics": metrics,
        "role": "新卒エンジニア一次面接官",
        "company_values": ["誠実", "挑戦", "チームワーク"],
    }
    res = gen_evaluation(payload)
    # compute heuristic scores and merge with AI scores
    heuristic = compute_heuristic_scores(metrics, payload.get('rubric', []))
    ai_scores = res.get('rubric_scores') or {}
    merged = {}
    WEIGHT_AI = float(current_app.config.get('HEURISTIC_WEIGHT_AI', 0.6))
    WEIGHT_H = float(current_app.config.get('HEURISTIC_WEIGHT_H', 0.4))
    for r in payload.get('rubric', []):
        ai_v = ai_scores.get(r) if r in ai_scores else None
        h_v = heuristic.get(r) if r in heuristic else None
        if ai_v is not None and h_v is not None:
            merged[r] = round(ai_v * WEIGHT_AI + h_v * WEIGHT_H, 2)
        elif ai_v is not None:
            merged[r] = ai_v
        elif h_v is not None:
            merged[r] = h_v
        else:
            merged[r] = None
    interview = Interview.query.filter_by(candidate_id=app_row.candidate_id).order_by(Interview.created_at.desc()).first()
    interview_id = interview.id if interview else None
    ev = Evaluation(org_id=app_row.org_id,
                    interview_id=interview_id,
                    overall_score=res.get("total"),
                    gpt_summary=res.get("summary"),
                    raw_metrics=res.get("rubric_scores"))
    # attach heuristic/merged into raw_metrics
    try:
        if metrics:
            rm = ev.raw_metrics or {}
            rm['speaking_metrics'] = metrics
            rm['heuristic_scores'] = heuristic
            rm['merged_scores'] = merged
            ev.raw_metrics = rm
    except Exception:
        pass
    # merge transcript metrics into raw_metrics for storage
    try:
        if metrics:
            rm = ev.raw_metrics or {}
            rm['speaking_metrics'] = metrics
            ev.raw_metrics = rm
    except Exception:
        pass
    db.session.add(ev)
    app_row.score_avg = res.get("total")
    app_row.last_evaluated_at = datetime.utcnow()
    db.session.commit()
    return ev.id


def _run_evaluate_interview(interview_id: int):
    interview = Interview.query.get(interview_id)
    if not interview:
        return None

    # find latest transcript text for this interview
    q = db.text(
        """
        SELECT t.text, t.metrics FROM transcripts t
        JOIN recordings r ON r.id = t.recording_id
        WHERE r.interview_id = :int_id
        ORDER BY t.created_at DESC
        LIMIT 1
        """
    )
    res = db.session.execute(q, {"int_id": interview_id}).fetchone()
    transcript = res[0] if res else ""
    metrics = res[1] if res and len(res) > 1 else None

    payload = {
        "rubric": ["speaking", "logical", "volume", "honesty", "proactive"],
        "transcript": transcript,
    "role": "interviewer",
    "metrics": metrics,
        "company_values": [],
    }
    gen_res = gen_evaluation(payload)
    # compute heuristic scores and merge with AI scores
    heuristic = compute_heuristic_scores(metrics, payload.get('rubric', []))
    ai_scores = gen_res.get('rubric_scores') or {}
    merged = {}
    WEIGHT_AI = 0.6
    WEIGHT_H = 0.4
    for r in payload.get('rubric', []):
        ai_v = ai_scores.get(r) if r in ai_scores else None
        h_v = heuristic.get(r) if r in heuristic else None
        if ai_v is not None and h_v is not None:
            merged[r] = round(ai_v * WEIGHT_AI + h_v * WEIGHT_H, 2)
        elif ai_v is not None:
            merged[r] = ai_v
        elif h_v is not None:
            merged[r] = h_v
        else:
            merged[r] = None

    # create Evaluation row compatible with current model
    ev = Evaluation(
        org_id=interview.org_id,
        interview_id=interview_id,
        overall_score=gen_res.get("total"),
        gpt_summary=gen_res.get("summary"),
        raw_metrics=gen_res.get("rubric_scores"),
    )
    # populate individual numeric columns if raw_metrics contains them
    try:
        # prefer merged values, fall back to AI raw
        ev.speaking = merged.get('speaking') if 'speaking' in merged else (gen_res.get('rubric_scores') or {}).get('speaking')
        ev.logical = merged.get('logical') if 'logical' in merged else (gen_res.get('rubric_scores') or {}).get('logical')
        ev.volume = merged.get('volume') if 'volume' in merged else (gen_res.get('rubric_scores') or {}).get('volume')
        ev.honesty = merged.get('honesty') if 'honesty' in merged else (gen_res.get('rubric_scores') or {}).get('honesty')
        ev.proactive = merged.get('proactive') if 'proactive' in merged else (gen_res.get('rubric_scores') or {}).get('proactive')
    except Exception:
        pass
    # store transcript metrics into raw_metrics for later analysis
    try:
        if metrics:
            rm = ev.raw_metrics or {}
            rm['speaking_metrics'] = metrics
            rm['heuristic_scores'] = heuristic
            rm['merged_scores'] = merged
            ev.raw_metrics = rm
    except Exception:
        pass
    db.session.add(ev)
    # optionally update interview.ai_score
    try:
        interview.ai_score = gen_res.get("total")
    except Exception:
        pass
    db.session.commit()
    return ev.id


def evaluate_application(app_id: int):
    """Entrypoint that ensures execution inside a Flask app context for workers."""
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            return _run_evaluate_application(app_id)
    except Exception:
        return _run_evaluate_application(app_id)


def evaluate_interview(interview_id: int):
    """Entrypoint that ensures execution inside a Flask app context for workers."""
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            return _run_evaluate_interview(interview_id)
    except Exception:
        return _run_evaluate_interview(interview_id)