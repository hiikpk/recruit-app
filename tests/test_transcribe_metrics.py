import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app


def test_transcribe_normalizes_metrics(monkeypatch, tmp_path):
    app = create_app()
    with app.app_context():
        # monkeypatch download_bytes to return fake audio bytes
        from app.jobs.transcribe import _run_transcribe

        def fake_download(url):
            return b"RIFF....WAVE"  # dummy

        monkeypatch.setattr('app.services.storage.download_bytes', lambda u: fake_download(u))

        # monkeypatch deepgram to return a structure with utterances
        def fake_deepgram(audio_bytes=None, language=None, filename=None):
            return {
                'utterances': [
                    {'speaker': 0, 'start': 0.0, 'end': 1.0, 'transcript': 'こんにちは'},
                    {'speaker': 1, 'start': 1.2, 'end': 2.0, 'transcript': 'よろしくお願いします'}
                ],
                'results': {'channels': [{'alternatives': [{'transcript': 'こんにちは よろしくお願いします'}]}]}
            }

        monkeypatch.setattr('app.jobs.transcribe.deepgram_raw_transcribe', fake_deepgram)

        # find a recording and run
        from app.models.recording import Recording
        rec = Recording.query.order_by(Recording.id.desc()).first()
        assert rec is not None
        tid = _run_transcribe(rec.id, 'ja')
        from app.models.transcript import Transcript
        tr = Transcript.query.get(tid)
        assert tr is not None
        assert isinstance(tr.metrics, dict)
        # if speaking_metrics present it should be dict or parsed
        sm = tr.metrics.get('speakers') or tr.metrics.get('speaking_metrics')
        assert sm is not None
