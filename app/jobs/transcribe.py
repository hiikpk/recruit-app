from ..extensions import db
from ..services.storage import download_bytes
from ..services.openai_wrap import transcribe_whisper
from ..models.transcript import Transcript
from ..models.recording import Recording


def transcribe_recording(recording_id: int, lang: str = "ja"):
    rec = Recording.query.get(recording_id)
    audio = download_bytes(rec.storage_url)
    text = transcribe_whisper(audio_bytes=audio, language=lang)
    tr = Transcript(org_id=rec.org_id, recording_id=rec.id, text=text, lang=lang)
    db.session.add(tr); db.session.commit()
    return tr.id