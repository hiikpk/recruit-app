# app/api/dg_transcribe.py
import os, uuid, json
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from ..extensions import db
from ..models.interview import Interview
from ..services.openai_wrap import transcribe_whisper

bp = Blueprint("dg_transcribe", __name__)

ALLOWED = {"mp3","mp4","m4a","wav","webm","ogg","flac"}
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..","..","instance","uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def allowed(name): return "." in name and name.rsplit(".",1)[1].lower() in ALLOWED


@bp.route("/api/interviews/<int:interview_id>/audio/deepgram", methods=["POST"])
def transcribe_deepgram(interview_id):
    iv = Interview.query.get_or_404(interview_id)

    if "file" not in request.files:
        return jsonify({"error":"file is required"}), 400
    f = request.files["file"]
    if f.filename == "" or not allowed(f.filename):
        return jsonify({"error":"unsupported or empty file"}), 400

    safe = secure_filename(f.filename)
    ext = safe.rsplit(".",1)[1].lower()
    fname = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_DIR, fname)
    f.save(path)

    # read bytes and call shared transcribe function (which now uses Deepgram via requests)
    with open(path, 'rb') as fh:
        audio_bytes = fh.read()

    transcript = transcribe_whisper(audio_bytes, language='ja')

    # minimal save
    iv.ai_transcript = transcript
    iv.ai_stt_model = "deepgram:via-transcribe_whisper"
    iv.ai_transcribed_at = datetime.now(timezone.utc)
    db.session.add(iv)
    db.session.commit()

    return jsonify({
        "interview_id": interview_id,
        "transcript_len": len(transcript or ""),
        "preview": (transcript or "")[:1000],
    }), 201