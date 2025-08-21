"""Lightweight wrappers for Deepgram transcription and OpenAI evaluation.

We avoid depending on the installed `openai` Python SDK because version
mismatches in the environment caused runtime errors. Instead we call the
OpenAI Responses HTTP API directly with `requests` and provide robust
fallbacks.
"""

from flask import current_app
try:
    import requests
except Exception:
    # allow the app to start even if requests is not installed in the environment.
    requests = None
import json
import mimetypes
import re
from typing import Dict, Any


def transcribe_whisper(audio_bytes: bytes, language: str = "ja", filename: str = None) -> str:
    """Transcribe audio bytes using Deepgram REST API.

    Returns a transcript string on success or a short dummy string on failure.
    """
    dg_key = current_app.config.get('DEEPGRAM_API_KEY')
    if not dg_key:
        return "(ダミー) これはDeepgramで文字起こししたテキストです。"

    # if requests is not available, avoid import-time failure and return dummy
    if requests is None:
        try:
            current_app.logger.warning('requests not installed; skipping Deepgram call, returning dummy transcript')
        except Exception:
            pass
        return "(ダミー) これはDeepgramで文字起こししたテキストです。"

    try:
        url = 'https://api.deepgram.com/v1/listen?punctuate=true'
        if language:
            url += f"&language={language}"

        content_type = 'audio/wav'
        if filename:
            guessed = mimetypes.guess_type(filename)[0]
            if guessed:
                content_type = guessed

        headers = {
            'Authorization': f'Token {dg_key}',
            'Content-Type': content_type,
        }

        r = requests.post(url, headers=headers, data=audio_bytes, timeout=60)
        r.raise_for_status()
        jr = r.json()

        # Deepgram typical shape: {results: {channels: [{alternatives:[{transcript:...}]}]}}
        try:
            transcript = jr.get('results', {}).get('channels', [])[0].get('alternatives', [])[0].get('transcript')
        except Exception:
            transcript = None

        if not transcript:
            # try common other locations
            transcript = jr.get('transcript') or jr.get('utterances') and ' '.join([u.get('transcript','') for u in jr.get('utterances', [])])

        return transcript or "(ダミー) これはDeepgramで文字起こししたテキストです。"
    except Exception:
        try:
            current_app.logger.exception('Deepgram transcription failed')
        except Exception:
            pass
        return "(ダミー) これはDeepgramで文字起こししたテキストです。"


def deepgram_raw_transcribe(audio_bytes: bytes, language: str = "ja", filename: str = None) -> dict:
    """Return the full Deepgram JSON response (best-effort)."""
    dg_key = current_app.config.get('DEEPGRAM_API_KEY')
    if not dg_key:
        return {}

    if requests is None:
        try:
            current_app.logger.warning('requests not installed; deepgram_raw_transcribe returning empty dict')
        except Exception:
            pass
        return {}

    try:
        # build query from config options for flexibility
        opts = current_app.config.get('DEEPGRAM_OPTIONS', {}) or {}
        params = []
        # default: request punctuation
        if opts.get('punctuate', True):
            params.append('punctuate=true')
        # diarization / utterances / multichannel
        if opts.get('diarize') or opts.get('diarization'):
            params.append('diarize=true')
        if opts.get('utterances'):
            params.append('utterances=true')
        if opts.get('multichannel'):
            params.append('multichannel=true')
        # utt_split is sometimes supported as a float threshold
        if 'utt_split' in opts:
            try:
                params.append(f"utt_split={float(opts.get('utt_split'))}")
            except Exception:
                pass
        if language:
            params.append(f"language={language}")
        url = 'https://api.deepgram.com/v1/listen' + ('?' + '&'.join(params) if params else '')

        content_type = 'audio/wav'
        if filename:
            guessed = mimetypes.guess_type(filename)[0]
            if guessed:
                content_type = guessed

        headers = {
            'Authorization': f'Token {dg_key}',
            'Content-Type': content_type,
        }

        r = requests.post(url, headers=headers, data=audio_bytes, timeout=60)
        r.raise_for_status()
        jr = r.json()
        return jr
    except Exception:
        try:
            current_app.logger.exception('Deepgram raw transcription failed')
        except Exception:
            pass
        return {}


def gen_evaluation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a structured evaluation JSON from a transcript using OpenAI Responses API.

    payload expects keys: rubric (list), transcript (str), role (str), company_values (list)
    """
    rubric = payload.get('rubric', [])
    transcript = payload.get('transcript', '') or ''

    api_key = current_app.config.get('OPENAI_API_KEY')
    if not api_key:
        # fallback dummy
        scores = {r: 4 for r in rubric}
        total = sum(scores.values())
        return {
            'rubric_scores': scores,
            'total': total,
            'decision': 'pass' if total >= len(rubric) * 3.5 else 'hold',
            'summary': f'(ダミー) 要約: 候補者は概ね良好です。Transcript抜粋: {transcript[:60]}...'
        }

    prompt_lines = ["あなたは採用面接の評価者です。以下の条件に従い出力は必ずJSONのオブジェクトだけを返してください。",
                    "- rubricごとに0-5のスコアを付け、rubric_scoresに辞書で入れること。",
                    "- totalには合計点を、decisionにはpass/hold/failのいずれかを入れること。",
                    "- summaryは日本語で簡潔に書くこと。",
                    "--",
                    "Rubric:"]
    prompt_lines += [f"- {r}" for r in rubric]
    prompt_lines += ["--", "Transcript:", transcript]
    # if speaking metrics are provided, include a short JSON summary for the model
    try:
        metrics = payload.get('metrics')
        if metrics:
            mstr = json.dumps(metrics, ensure_ascii=False)
            # truncate to reasonable size to keep prompt short
            if len(mstr) > 2000:
                mstr = mstr[:2000] + '...(truncated)'
            prompt_lines += ["--", "Metrics (JSON):", mstr]
    except Exception:
        # ignore metrics inclusion failures
        pass
    prompt = "\n".join(prompt_lines)

    url = 'https://api.openai.com/v1/responses'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    body = {
        'model': 'gpt-4o-mini',
        'input': prompt,
        'max_output_tokens': 600,
        'temperature': 0.2,
    }

    # improved retry for rate limits / transient errors
    # - increase attempts
    # - respect Retry-After header when present
    # - use exponential backoff with small jitter
    import time
    import random
    max_attempts = 6
    backoff = 1.0
    jr = None
    for attempt in range(1, max_attempts + 1):
        try:
            if requests is None:
                try:
                    current_app.logger.warning('requests not installed; skipping OpenAI call and returning fallback evaluation')
                except Exception:
                    pass
                jr = None
                break
            r = requests.post(url, headers=headers, json=body, timeout=30)
            # if we get an explicit 429, prefer honoring Retry-After header
            if r.status_code == 429:
                ra = r.headers.get('Retry-After')
                wait = None
                if ra:
                    try:
                        wait = float(ra)
                    except Exception:
                        try:
                            # sometimes Retry-After is an HTTP-date; fallback to backoff
                            wait = backoff
                        except Exception:
                            wait = backoff
                else:
                    wait = backoff
                # if the response body indicates insufficient_quota, don't retry
                body_text = r.text or ''
                if 'insufficient_quota' in body_text or 'quota' in body_text.lower():
                    try:
                        current_app.logger.error('OpenAI 429 indicates insufficient quota, returning fallback evaluation; body=%s', body_text[:2000])
                    except Exception:
                        pass
                    jr = None
                    break
                try:
                    current_app.logger.warning(f'OpenAI request returned 429, attempt {attempt}/{max_attempts}, retrying in {wait}s; resp_body={body_text[:1000]}')
                except Exception:
                    pass
                time.sleep(wait + random.uniform(0, 0.5))
                backoff *= 2
                continue

            # raise for other HTTP error statuses
            try:
                r.raise_for_status()
            except requests.exceptions.HTTPError as e:
                status = getattr(e.response, 'status_code', None)
                body = None
                try:
                    body = e.response.text
                except Exception:
                    body = None
                if status == 429 or (status and 500 <= status < 600):
                    # transient server error -> retry
                    try:
                        ra = e.response.headers.get('Retry-After') if e.response is not None else None
                        wait = float(ra) if ra else backoff
                    except Exception:
                        wait = backoff
                    try:
                        current_app.logger.warning(f'OpenAI request failed with {status}, attempt {attempt}/{max_attempts}, retrying in {wait}s; body={body[:1000] if body else None}')
                    except Exception:
                        pass
                    time.sleep(wait + random.uniform(0, 0.5))
                    backoff *= 2
                    continue
                else:
                    # non-retryable HTTP error
                    try:
                        current_app.logger.error(f'OpenAI HTTP error {status}: {body[:1000] if body else None}')
                    except Exception:
                        pass
                    raise

            jr = r.json()
            break
        except requests.exceptions.RequestException:
            # network-level error; retry with backoff
            try:
                current_app.logger.warning(f'OpenAI network error, attempt {attempt}/{max_attempts}, retrying in {backoff}s')
            except Exception:
                pass
            time.sleep(backoff + random.uniform(0, 0.5))
            backoff *= 2
            continue
        except Exception:
            # unexpected parsing/other errors; log and retry a couple times
            try:
                current_app.logger.warning(f'OpenAI request unexpected error, attempt {attempt}/{max_attempts}')
            except Exception:
                pass
            time.sleep(backoff + random.uniform(0, 0.5))
            backoff *= 2
            continue

    # if we couldn't get a response JSON after retries, fallback
    if jr is None:
        try:
            current_app.logger.warning('OpenAI Responses returned no data after retries')
        except Exception:
            pass
        scores = {r: 4 for r in rubric}
        total = sum(scores.values()) if scores else None
        return {
            'rubric_scores': scores,
            'total': total,
            'decision': 'pass' if total and total >= len(rubric) * 3.5 else 'hold',
            'summary': f'(ダミー) 要約: 候補者は概ね良好です。Transcript抜粋: {transcript[:60]}...'
        }

    try:
        # extract text from known shapes
        text = ''
        if isinstance(jr, dict):
            text = jr.get('output_text') or ''
            if not text:
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
                text = '\n'.join(parts)

        # parse JSON block if present
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            data = json.loads(m.group(0))
        else:
            try:
                data = json.loads(text) if text else {}
            except Exception:
                data = {}

        scores = data.get('rubric_scores', {})
        total = data.get('total') or (sum(scores.values()) if scores else None)
        return {
            'rubric_scores': scores,
            'total': total,
            'decision': data.get('decision', 'hold'),
            'summary': data.get('summary', '')
        }
    except Exception:
        try:
            current_app.logger.exception('OpenAI Responses call failed during parsing, falling back')
        except Exception:
            pass
        scores = {r: 4 for r in rubric}
        total = sum(scores.values()) if scores else None
        return {
            'rubric_scores': scores,
            'total': total,
            'decision': 'pass' if total and total >= len(rubric) * 3.5 else 'hold',
            'summary': f'(ダミー) 要約: 候補者は概ね良好です。Transcript抜粋: {transcript[:60]}...'
        }
