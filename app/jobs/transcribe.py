from ..extensions import db
from ..services.storage import download_bytes
from ..services.openai_wrap import transcribe_whisper, deepgram_raw_transcribe
from ..models.transcript import Transcript
from ..models.recording import Recording
from ..extensions import rq
from ..jobs.evaluate import evaluate_interview
from ..services.speaking_metrics import speaking_metrics_from_utterances
from flask import current_app
from ..services.postprocess import process_utterances


def _format_transcript_text(raw_text, utterances=None, lang='ja'):
    """Return a human-friendly transcript string.
    - If utterances provided, build speaker-labelled paragraphs.
    - Otherwise, insert newlines by sentence-ending punctuation (simple heuristic).
    """
    if utterances:
        lines = []
        for u in utterances:
            spk = u.get('speaker') if u.get('speaker') is not None else u.get('speaker_label')
            # normalize speaker label
            try:
                spk_label = f"話者{int(spk)}" if spk is not None else "話者0"
            except Exception:
                spk_label = str(spk) if spk is not None else "話者0"
            text = (u.get('text') or '').strip()
            if not text and raw_text:
                text = raw_text.strip()
            if text:
                lines.append(f"{spk_label}: {text}")
        return "\n\n".join(lines) if lines else (raw_text or '')

    # No utterances: do simple sentence-splitting heuristics
    if not raw_text:
        return ''
    s = raw_text.strip()
    if lang and lang.lower().startswith('ja'):
        # insert newline after Japanese sentence enders
        for sep in ['。', '！', '？']:
            s = s.replace(sep, sep + "\n\n")
        # collapse multiple newlines
        while '\n\n\n' in s:
            s = s.replace('\n\n\n', '\n\n')
        # if still no newlines, split roughly every 120 chars
        if '\n' not in s:
            parts = [s[i:i+120].strip() for i in range(0, len(s), 120)]
            s = '\n\n'.join(parts)
        return s
    else:
        # English/others: split on dot/question/exclamation followed by space
        import re
        s = re.sub(r'([\.\!\?])\s+', r"\1\n\n", s)
        if '\n' not in s:
            parts = [s[i:i+120].strip() for i in range(0, len(s), 120)]
            s = '\n\n'.join(parts)
        return s

def _run_transcribe(recording_id: int, lang: str = "ja"):
    rec = Recording.query.get(recording_id)
    audio = download_bytes(rec.storage_url)
    # extract filename from storage_url if file://
    filename = None
    if rec.storage_url and rec.storage_url.startswith('file://'):
        filename = rec.storage_url.replace('file://', '')
    # prefer the raw Deepgram response so we can compute detailed metrics
    try:
        dg_opts = current_app.config.get('DEEPGRAM_OPTIONS', {}) or {}
        current_app.logger.info('Deepgram options: %s', dg_opts)
    except Exception:
        dg_opts = {}
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

    # Create initial Transcript row in 'processing' state so UI can reflect work in progress.
    tr = Transcript(org_id=rec.org_id, recording_id=rec.id, text=text or '', lang=lang, status='processing')
    db.session.add(tr)
    db.session.commit()
    # attach raw utterances and derived metrics when available
    if utterances:
        # apply post-processing heuristics to improve merging/backchannels/switchbacks
        try:
            proc_utterances = process_utterances(utterances)
        except Exception:
            proc_utterances = utterances

        tr.utterances = proc_utterances
        try:
            metrics = speaking_metrics_from_utterances(proc_utterances)
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
            # Normalize metrics: ensure dict, parse nested JSON strings
            try:
                import json
                if isinstance(metrics, str):
                    try:
                        metrics = json.loads(metrics)
                    except Exception:
                        try:
                            metrics = eval(metrics)
                        except Exception:
                            metrics = {}
                # If speaking_metrics is a JSON string, parse it
                sm = metrics.get('speaking_metrics') if isinstance(metrics, dict) else None
                if isinstance(sm, str):
                    try:
                        metrics['speaking_metrics'] = json.loads(sm)
                    except Exception:
                        try:
                            metrics['speaking_metrics'] = eval(sm)
                        except Exception:
                            # leave as string if unparsable
                            pass
            except Exception:
                # if normalization fails, ensure metrics is a dict
                try:
                    metrics = dict(metrics) if metrics else {}
                except Exception:
                    metrics = {}
            tr.metrics = metrics
        except Exception:
            tr.metrics = None
        except Exception:
            tr.metrics = None
    else:
        tr.utterances = None
        tr.metrics = None
    # Format a readable transcript for UI: prefer utterances when available
    try:
        formatted = _format_transcript_text(text, utterances=utterances, lang=lang)
        tr.text = formatted or (text or '')
    except Exception:
        # fallback to raw text
        tr.text = text or ''

    try:
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
            current_app.logger.exception('Failed to update Interview.transcript_text')
        # enqueue evaluation job for the interview (if recording.interview_id present)
        try:
            if rec and getattr(rec, "interview_id", None):
                rq.enqueue(evaluate_interview, int(rec.interview_id))
        except Exception:
            current_app.logger.exception('Failed to enqueue evaluate_interview')
        # mark transcript as successful
        tr.status = 'ok'
        tr.error = None
        db.session.add(tr)
        db.session.commit()
    except Exception as e:
        # persist error state
        try:
            tr.status = 'error'
            tr.error = str(e)
            db.session.add(tr)
            db.session.commit()
        except Exception:
            current_app.logger.exception('Failed to persist transcript error state')
        # re-raise so RQ shows job failure in logs if desired
        raise
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