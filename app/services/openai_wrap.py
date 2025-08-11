from openai import OpenAI
from flask import current_app
client = None

def _client():
    global client
    if client is None:
        client = OpenAI(api_key=current_app.config['OPENAI_API_KEY'])
    return client

# ダミー実装（実運用は音声bytesをfile-likeで渡す）
def transcribe_whisper(audio_bytes: bytes, language: str = "ja") -> str:
    # 実際のAPI呼び出しは、環境・モデル名に合わせて実装
    # ここではMVP用の代替（今は固定文）
    return "(ダミー) これはWhisperで文字起こししたテキストです。"

# 評価生成（rubric_scores/total/decision/summaryのJSONを返す想定）
def gen_evaluation(payload: dict) -> dict:
    transcript = payload.get("transcript", "")
    rubric = payload.get("rubric", [])
    # 実際はchat.completions等でJSON出力を厳格化
    # MVPはダミーで返す
    scores = {k: 4 for k in rubric}
    total = sum(scores.values())
    return {
        "rubric_scores": scores,
        "total": total,
        "decision": "pass" if total >= len(rubric)*3.5 else "hold",
        "summary": f"(ダミー) 要約: 候補者はポテンシャルあり。Transcript抜粋: {transcript[:60]}..."
    }