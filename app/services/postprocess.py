"""Post-processing utilities for transcripts/utterances.

Provides heuristics to merge short utterances, remove backchannels (相槌),
and correct quick switchbacks between speakers.

These are lightweight, deterministic heuristics intended to improve
readability when diarization/utterance data is available.
"""
from typing import List, Dict, Any
import re

BACKCHANNEL_TOKENS = set([
    'うん','うーん','えー','あの','えっと','あー','はい','そう','なるほど','そうですね','はいー','うんうん','あ','ん'
])


def _is_backchannel(text: str) -> bool:
    if not text:
        return False
    s = ''.join(text.split()).lower()
    # if very short and matches known backchannel tokens
    if len(s) <= 6:
        for t in BACKCHANNEL_TOKENS:
            if t in s:
                return True
    return False


def process_utterances(utterances: List[Dict[str, Any]],
                       min_chars_for_own_utt: int = 8,
                       max_gap_sec: float = 0.7,
                       lang: str = None) -> List[Dict[str, Any]]:
    """Merge and clean a list of utterances.

    Heuristics:
    - Merge consecutive utterances from same speaker when small or short gap.
    - Drop or attach pure backchannels to the previous utterance.
    - If a very short utterance from speaker B is sandwiched between two longer
      utterances from speaker A, consider it a switchback and merge into A.

    Returns a new utterances list with same keys.
    """
    if not utterances:
        return []

    # First, normalize fields
    items = []
    for u in utterances:
        # normalize text and optionally remove Japanese spaces
        text = (u.get('text') or '').strip()
        if lang and lang.lower().startswith('ja'):
            # remove ASCII spaces and full-width spaces for better Japanese readability
            text = text.replace(' ', '').replace('\u3000', '')
            # normalize some punctuation variants to standard Japanese punctuation
            text = text.replace('.', '。').replace('｡', '。')
            text = text.replace(',', '、').replace('､', '、')
            # collapse repeated punctuation
            text = re.sub(r'[。]{2,}', '。', text)
            text = re.sub(r'[、]{2,}', '、', text)
            # small, low-risk spelling/casing fixes (limited mapping)
            SPELL_CORRECTIONS = {
                'お願い致します': 'お願いいたします',
                'お願い致': 'お願いいたします',
                '宜しく': 'よろしく',
            }
            for k, v in SPELL_CORRECTIONS.items():
                if k in text:
                    text = text.replace(k, v)
        items.append({
            'speaker': u.get('speaker') if u.get('speaker') is not None else u.get('speaker_label'),
            'start': u.get('start'),
            'end': u.get('end'),
            'text': text
        })

    merged = []
    for u in items:
        if not merged:
            merged.append(u.copy())
            continue
        prev = merged[-1]
    # same speaker? always merge consecutive same-speaker utterances
        gap = None
        try:
            if prev.get('end') is not None and u.get('start') is not None:
                gap = float(u.get('start')) - float(prev.get('end'))
        except Exception:
            gap = None

        if prev['speaker'] == u['speaker']:
            # merge into prev
            if u['text']:
                # for Japanese we removed internal spaces above; for other langs keep a space between merged parts
                if lang and lang.lower().startswith('ja'):
                    prev['text'] = (prev.get('text','') + u['text']).strip()
                else:
                    prev['text'] = (prev.get('text','') + ' ' + u['text']).strip()
            prev['end'] = u.get('end') or prev.get('end')
        else:
            merged.append(u.copy())

    # Second pass: remove/attach backchannels and fix quick switchbacks
    result = []
    i = 0
    L = len(merged)
    while i < L:
        u = merged[i]
        # backchannel only
        if _is_backchannel(u['text']):
            # attach to previous if exists
            if result:
                prev = result[-1]
                prev['text'] = (prev.get('text','') + ' ' + u['text']).strip()
                prev['end'] = u.get('end') or prev.get('end')
            else:
                # keep it if no previous
                result.append(u)
            i += 1
            continue

        # switchback pattern: A B A where B is short -> attach B to surrounding A
        if i+2 < L:
            a = merged[i]
            b = merged[i+1]
            c = merged[i+2]
            if a['speaker'] == c['speaker'] and b['speaker'] != a['speaker'] and len(b.get('text','')) < min_chars_for_own_utt:
                # merge b into a (attach to a) and skip b
                a['text'] = (a.get('text','') + ' ' + b.get('text','') + ' ' + c.get('text','')).strip()
                a['end'] = c.get('end') or a.get('end')
                result.append(a)
                i += 3
                continue

        # otherwise keep
        result.append(u)
        i += 1

    # final: collapse multiple spaces
    for r in result:
        r['text'] = ' '.join(r.get('text','').split())

    # Additional pass: for Japanese, split long utterances on Japanese sentence-final '。'
    final = []
    for r in result:
        txt = r.get('text','')
        if lang and lang.lower().startswith('ja') and '。' in txt:
            # split preserving punctuation; ignore very short pieces
            parts = [p + '。' for p in txt.split('。') if p]
            # if there's only one part, keep as-is
            if len(parts) == 1:
                final.append(r)
                continue
            # distribute start/end times proportionally by character length when available
            total_chars = sum(len(p) for p in parts)
            start = r.get('start')
            end = r.get('end')
            duration = None
            if start is not None and end is not None:
                try:
                    duration = float(end) - float(start)
                except Exception:
                    duration = None

            offset = 0.0
            char_acc = 0
            for p in parts:
                piece_len = len(p)
                new_u = {
                    'speaker': r.get('speaker'),
                    'text': p.strip(),
                    'start': None,
                    'end': None
                }
                if duration is not None and total_chars > 0:
                    frac = piece_len / float(total_chars)
                    piece_start = float(start) + offset
                    piece_end = piece_start + frac * duration
                    new_u['start'] = piece_start
                    new_u['end'] = piece_end
                    offset += frac * duration
                else:
                    new_u['start'] = r.get('start')
                    new_u['end'] = r.get('end')
                final.append(new_u)
        else:
            final.append(r)

    # ensure no accidental ASCII spaces remain in Japanese output
    if lang and lang.lower().startswith('ja'):
        for r in final:
            r['text'] = r.get('text','').replace(' ', '').replace('\u3000', '')

    return final

