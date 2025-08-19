import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.jobs.evaluate import compute_heuristic_scores


def test_compute_heuristic_from_json_string():
    metrics = json.dumps({
        "speakers": {"0": {"ratio": 0.7, "cpm": 120, "avg_turn_sec": 5}},
        "total_time_sec": 300,
        "avg_silence_sec": 0.5,
        "interruptions": 2,
        "filler_rate": 0.01
    })
    rubric = ["speaking", "logical", "volume", "honesty", "proactive"]
    out = compute_heuristic_scores(metrics, rubric)
    assert isinstance(out, dict)
    assert all(k in out for k in rubric)
