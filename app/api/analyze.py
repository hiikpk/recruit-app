# app/api/analyze.py
import os, json
from datetime import datetime, timezone
from flask import Blueprint, jsonify, current_app
from sqlalchemy import func
from app.extensions import db
from app.models import Interview
from app.services.speaking_metrics import speaking_metrics_from_utterances
import requests

bp = Blueprint("analyze", __name__)


def _openai_setup():
    key = os.getenv('OPENAI_API_KEY') or None
    return bool(key)

MODEL_MAP = {
    "map": "gpt-4.1-mini",    # 安価・JSON安定
    "reduce": "gpt-4.1",      # 品質
}

@bp.route("/api/interviews/<int:interview_id>/analyze", methods=["POST"])
def analyze_interview(interview_id):
    iv = Interview.query.get_or_404(interview_id)
    ai_segments = getattr(iv, 'ai_transcript_segments_json', None)
    ai_transcript = getattr(iv, 'ai_transcript', None)
    if not ai_segments and not ai_transcript:
        # fallback: try to load latest transcript from transcripts table
        q = db.text(
            """
            SELECT t.text FROM transcripts t
            JOIN recordings r ON r.id = t.recording_id
            WHERE r.interview_id = :int_id
            ORDER BY t.created_at DESC
            LIMIT 1
            """
        )
        res = db.session.execute(q, {"int_id": interview_id}).fetchone()
        if res:
            ai_transcript = res[0]
        else:
            return jsonify({"error": "transcript missing"}), 400

    utterances = []
    try:
        if ai_segments:
            utterances = json.loads(ai_segments or "[]")
    except Exception:
        utterances = []

    # 1) 話し方メトリクス
    metrics = speaking_metrics_from_utterances(utterances)
    metrics_json = json.dumps(metrics, ensure_ascii=False)

    # 2) 要約（Deepgram要約が無ければ GPT で生成）
    summary = getattr(iv, 'ai_summary', None)
    if not summary:
        # 2-1) まず短要約（200字）
        prompt_summary = (
            "以下は面接の発話抜粋です。日本語200字以内で要約してください。"
            "固有名詞は一般化して構いません。\n\n"
            + "\n".join(f"[{u.get('start',0):.0f}s][spk{u.get('speaker')}] {u.get('text','')}" for u in utterances[:200])
        )
        if _openai_setup():
            try:
                api_key = os.getenv('OPENAI_API_KEY')
                url = 'https://api.openai.com/v1/responses'
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                body = {'model': 'gpt-4o-mini', 'input': prompt_summary, 'max_output_tokens': 280}
                r = requests.post(url, headers=headers, json=body, timeout=20)
                r.raise_for_status()
                jr = r.json()
                summary = jr.get('output_text') or ''
                if not summary:
                    out = jr.get('output') or jr.get('results') or []
                    parts = []
                    for item in out:
                        if isinstance(item, dict):
                            for c in item.get('content', []):
                                if isinstance(c, dict) and 'text' in c:
                                    parts.append(c['text'])
                                elif isinstance(c, str):
                                    parts.append(c)
                        elif isinstance(item, str):
                            parts.append(item)
                    summary = '\n'.join(parts)
                summary = (summary or '').strip()
            except Exception:
                try:
                    current_app.logger.exception('OpenAI summary failed')
                except Exception:
                    pass

    # 3) 評価生成（スコアリング＋根拠）
    #    評価は JSON で返させる（後段の集計/表示が楽）
    eval_schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "InterviewEvaluation",
            "schema": {
                "type": "object",
                "properties": {
                    "ai_score": {"type":"number"},
                    "aspect_scores": {
                        "type":"object",
                        "properties":{
                            "communication":{"type":"number"},
                            "problem_solving":{"type":"number"},
                            "role_fit":{"type":"number"},
                            "culture_fit":{"type":"number"}
                        },
                        "required":["communication","problem_solving","role_fit","culture_fit"]
                    },
                    "top_evidence": {
                        "type":"array",
                        "items":{"type":"object","properties":{
                            "t":{"type":"string"}, "quote":{"type":"string"}, "aspect":{"type":"string"}
                        }, "required":["t","quote","aspect"]}
                    },
                    "risks":{"type":"array","items":{"type":"string"}},
                    "recommendation":{"type":"string","enum":["advance","reject","hold"]},
                    "summary_short":{"type":"string"}
                },
                "required":["ai_score","aspect_scores","top_evidence","recommendation","summary_short"],
                "additionalProperties": False
            },
            "strict": True
        }
    }

    # 短いプロンプトで“数値＋根拠”に集中
    prompt_eval = f"""
あなたは採用面接のアナリストです。日本語で出力してください。
入力は (1) 面接の要約 (2) 話し方メトリクス です。これらを根拠に、候補者の
communication / problem_solving / role_fit / culture_fit を0–100で採点し、
上位3–5件の根拠（発話の短い引用＋時刻MM:SS＋該当アスペクト）を示し、
総合スコア(ai_score)と推奨(recommendation)を出してください。
根拠が足りない項目は推測せず、保守的に評価してください。

(1) 要約:
{summary}

(2) 話し方メトリクス(JSON):
{metrics_json}
""".strip()

    resp2 = None
    if _openai_setup():
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            url = 'https://api.openai.com/v1/responses'
            headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
            body = {'model': 'gpt-4.1', 'input': prompt_eval, 'max_output_tokens': 800}
            r = requests.post(url, headers=headers, json=body, timeout=30)
            r.raise_for_status()
            jr = r.json()
            class _R: pass
            resp2 = _R()
            resp2.output_text = jr.get('output_text') or ''
            if not resp2.output_text:
                out = jr.get('output') or jr.get('results') or []
                parts = []
                for item in out:
                    if isinstance(item, dict):
                        for c in item.get('content', []):
                            if isinstance(c, dict) and 'text' in c:
                                parts.append(c['text'])
                            elif isinstance(c, str):
                                parts.append(c)
                    elif isinstance(item, str):
                        parts.append(item)
                resp2.output_text = '\n'.join(parts)
        except Exception:
            try:
                current_app.logger.exception('OpenAI eval failed')
            except Exception:
                pass
            resp2 = None

    eval_obj = None
    try:
        if resp2 and getattr(resp2, 'output_text', None):
            eval_obj = json.loads(resp2.output_text)
        else:
            eval_obj = {"summary_short": summary or '', "ai_score": None, "aspect_scores": {}, "top_evidence": [], "risks": [], "recommendation": "hold"}
    except Exception:
        # フォールバック：テキストを丸ごと保存
        try:
            # try to extract JSON block if the model returned text with commentary
            import re
            if resp2 and getattr(resp2, 'output_text', None):
                m = re.search(r"\{[\s\S]*\}", resp2.output_text)
                if m:
                    eval_obj = json.loads(m.group(0))
                else:
                    eval_obj = {"summary_short": summary or '', "ai_score": None, "aspect_scores": {}, "top_evidence": [], "risks": [], "recommendation": "hold"}
            else:
                eval_obj = {"summary_short": summary or '', "ai_score": None, "aspect_scores": {}, "top_evidence": [], "risks": [], "recommendation": "hold"}
        except Exception:
            eval_obj = {"summary_short": summary or '', "ai_score": None, "aspect_scores": {}, "top_evidence": [], "risks": [], "recommendation": "hold"}

    # 4) 保存
    # save fields only if model has those attributes (to support older schemas)
    if hasattr(iv, 'ai_summary'):
        setattr(iv, 'ai_summary', summary)
    if hasattr(iv, 'ai_metrics_json'):
        setattr(iv, 'ai_metrics_json', json.dumps(metrics, ensure_ascii=False))
    if hasattr(iv, 'ai_eval_json'):
        setattr(iv, 'ai_eval_json', json.dumps(eval_obj, ensure_ascii=False))
    if hasattr(iv, 'ai_score'):
        setattr(iv, 'ai_score', eval_obj.get('ai_score'))
    if hasattr(iv, 'ai_eval_updated_at'):
        setattr(iv, 'ai_eval_updated_at', datetime.now(timezone.utc))
    db.session.commit()

    # Also create a row in interview_evaluations table using gen_evaluation for backward compatibility
    try:
        from app.services.openai_wrap import gen_evaluation
        from app.models.evaluation import Evaluation

        payload = {
            "rubric": ["communication","problem_solving","role_fit","culture_fit"],
            "transcript": iv.ai_transcript or iv.ai_summary or "",
        }
        gen_res = gen_evaluation(payload)
        ev = Evaluation(
            org_id=iv.org_id,
            interview_id=interview_id,
            overall_score=gen_res.get('total'),
            gpt_summary=gen_res.get('summary'),
            raw_metrics=gen_res.get('rubric_scores'),
        )
        db.session.add(ev)
        db.session.commit()
    except Exception:
        try:
            current_app.logger.exception('creating interview_evaluation failed')
        except Exception:
            pass

    return jsonify({
        "interview_id": interview_id,
        "ai_score": iv.ai_score,
        "recommendation": eval_obj.get("recommendation"),
        "summary_short": eval_obj.get("summary_short", summary[:200]),
        "aspect_scores": eval_obj.get("aspect_scores"),
        "top_evidence": eval_obj.get("top_evidence"),
        "metrics": metrics,
    })