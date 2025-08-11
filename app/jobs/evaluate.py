from ..extensions import db
from ..services.openai_wrap import gen_evaluation
from ..models.evaluation import Evaluation
from ..models.application import Application
from datetime import datetime


def evaluate_application(app_id: int):
    app = Application.query.get(app_id)
    transcript = app.latest_transcript_text()
    payload = {
        "rubric": ["コミュ力(5)", "技術(5)", "ロジカル(5)", "カルチャー(5)"],
        "transcript": transcript,
        "role": "新卒エンジニア一次面接官",
        "company_values": ["誠実", "挑戦", "チームワーク"],
    }
    res = gen_evaluation(payload)
    ev = Evaluation(org_id=app.org_id,
                    application_id=app.id,
                    rubric_json=res["rubric_scores"],
                    score_total=res["total"],
                    decision=res["decision"],
                    gpt_summary=res["summary"])
    db.session.add(ev)
    app.score_avg = res["total"]
    app.last_evaluated_at = datetime.utcnow()
    db.session.commit()
    return ev.id