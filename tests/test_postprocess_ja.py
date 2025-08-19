import pytest
from app.services.postprocess import process_utterances


def test_postprocess_ja_basic():
    utts = [
        {'speaker': 0, 'start': 0.0, 'end': 1.0, 'text': '今日は、よろしくお願いします。'},
        {'speaker': 0, 'start': 1.0, 'end': 2.0, 'text': '私の名前は山田です。'},
        {'speaker': 1, 'start': 2.0, 'end': 3.0, 'text': 'あの'},
        {'speaker': 0, 'start': 3.0, 'end': 4.0, 'text': '趣味はサッカーです。'},
    ]

    out = process_utterances(utts, lang='ja')
    texts = [u['text'] for u in out]
    # Expect punctuation normalized and splitting: first two from speaker 0 may be split
    assert any('。' in t for t in texts)
    # 'あの' is a backchannel and should be attached to previous or removed
    assert not any(t == 'あの' for t in texts)
    # spelling correction: 'よろしくお願いします' should be normalized (unchanged or corrected form exists)
    assert any('よろしく' in t for t in texts)


if __name__ == '__main__':
    pytest.main(['-q'])
