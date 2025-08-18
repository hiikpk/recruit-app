from ..extensions import db
from ..services.storage import download_bytes
from ..services.openai_wrap import transcribe_whisper, deepgram_raw_transcribe
from ..models.transcript import Transcript
from ..models.recording import Recording
from ..extensions import rq
from ..jobs.evaluate import evaluate_interview
from ..services.speaking_metrics import speaking_metrics_from_utterances
from flask import current_app

def _run_transcribe(recording_id: int, lang: str = "ja"):
    rec = Recording.query.get(recording_id)
    audio = download_bytes(rec.storage_url)
    # extract filename from storage_url if file://
    filename = None
    if rec.storage_url and rec.storage_url.startswith('file://'):
        filename = rec.storage_url.replace('file://', '')
    # prefer the raw Deepgram response so we can compute detailed metrics
    raw = deepgram_raw_transcribe(audio_bytes=audio, language=lang, filename=filename)
    # best-effort extract text
    text = None
    try:
        text = raw.get('results', {}).get('channels', [])[0].get('alternatives', [])[0].get('transcript')
    except Exception:
        text = None
    if not text:
        text = transcribe_whisper(audio_bytes=audio, language=lang, filename=filename)

    # extract utterances if present (Deepgram 'utterances' array) or build from alternatives
    utterances = None
    try:
        utt = raw.get('utterances')
        if utt:
            # normalize fields: speaker, start, end, transcript/text
            utterances = []
            for u in utt:
                utterances.append({
                    'speaker': u.get('speaker') or u.get('speaker_label'),
                    'start': u.get('start'),
                    'end': u.get('end'),
                    'text': u.get('transcript') or u.get('text') or ''
                })
        else:
            # fallback: try to build utterances from word-level results
            try:
                words = raw.get('results', {}).get('channels', [])[0].get('alternatives', [])[0].get('words')
                if words:
                    utterances = []
                    # group contiguous words by speaker and small gaps into utterances
                    current = None
                    GAP_THRESH = current_app.config.get('DG_WORD_GAP_THRESHOLD', 0.35)
                    for w in words:
                        spk = w.get('speaker') if w.get('speaker') is not None else 0
                        start = w.get('start')
                        end = w.get('end')
                        text = w.get('punctuated_word') or w.get('word') or ''
                        if current is None:
                            current = {'speaker': spk, 'start': start, 'end': end, 'text': text}
                        else:
                            # if speaker changed or gap is large, finalize current
                            gap = start - current['end'] if start and current.get('end') else 0
                            if spk != current['speaker'] or (gap is not None and gap > GAP_THRESH):
                                utterances.append(current)
                                current = {'speaker': spk, 'start': start, 'end': end, 'text': text}
                            else:
                                # extend current utterance
                                current['end'] = end
                                if current['text']:
                                    current['text'] += ' ' + text
                                else:
                                    current['text'] = text
                    if current:
                        utterances.append(current)
            except Exception:
                utterances = None
    except Exception:
        utterances = None

    tr = Transcript(org_id=rec.org_id, recording_id=rec.id, text=text or '', lang=lang)
    # attach raw utterances and derived metrics when available
    if utterances:
        tr.utterances = utterances
        try:
            metrics = speaking_metrics_from_utterances(utterances)
            # compute filler rate using word-level fallback when possible
            filler_tokens = current_app.config.get('FILLER_TOKENS', 'えー,あの,えっと,うーん,うー,あー,um,uh').split(',')
            total_words = 0
            filler_count = 0
            try:
                words = raw.get('results', {}).get('channels', [])[0].get('alternatives', [])[0].get('words')
                if words:
                    for w in words:
                        token = (w.get('punctuated_word') or w.get('word') or '').lower()
                        if token:
                            total_words += 1
                            for f in filler_tokens:
                                if f in token:
                                    filler_count += 1
            except Exception:
                # fallback to counting in utterance text
                total_words = sum(len(u.get('text','').split()) for u in utterances) or 1
                for u in utterances:
                    t = u.get('text','').lower()
                    for f in filler_tokens:
                        filler_count += t.count(f)
            metrics['filler_rate'] = (filler_count / total_words) if total_words else 0.0
            tr.metrics = metrics
        except Exception:
            tr.metrics = None
    else:
        tr.utterances = None
        tr.metrics = None
    db.session.add(tr)
    db.session.commit()
    # also persist full transcript text to Interview for quick access
    try:
        if rec and getattr(rec, 'interview_id', None):
            from ..models.interview import Interview
            interview = Interview.query.get(int(rec.interview_id))
            if interview:
                interview.transcript_text = tr.text
                db.session.add(interview)
                db.session.commit()
    except Exception:
        # do not fail the job if interview update fails
        pass
    # enqueue evaluation job for the interview (if recording.interview_id present)
    try:
        if rec and getattr(rec, "interview_id", None):
            rq.enqueue(evaluate_interview, int(rec.interview_id))
    except Exception:
        # don't fail the transcribe job if enqueue fails
        pass
    return tr.id


def transcribe_recording(recording_id: int, lang: str = "ja"):
    """Public job entrypoint: ensures execution inside Flask app context
    so RQ workers can call this function without requiring the caller to
    set up the app context.
    """
    # lazy import to avoid circular imports at module import time
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            return _run_transcribe(recording_id, lang)
    except Exception:
        # If app creation fails for some reason, try to run directly
        return _run_transcribe(recording_id, lang)