#!/usr/bin/env python3
"""Normalize interview_evaluations.raw_metrics column.

This script will:
- iterate rows in interview_evaluations
- if raw_metrics is a string, attempt json.loads; if that fails, skip
- for nested fields like 'speaking_metrics' that are strings, json.loads them
- write back the normalized dict into the JSON column

Run from project root: python scripts/normalize_evaluations_raw_metrics.py
"""
import os
import sys
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.evaluation import Evaluation


def normalize_value(val):
    # If val is a string that looks like JSON, try to parse it
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            # leave as-is
            return val
    return val


def main():
    app = create_app()
    with app.app_context():
        total = 0
        fixed = 0
        rows = Evaluation.query.order_by(Evaluation.id).all()
        for ev in rows:
            total += 1
            raw = ev.raw_metrics
            changed = False
            # If raw is a string, attempt to parse
            if isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                    raw = parsed
                    changed = True
                except Exception:
                    # cannot parse, skip
                    continue

            # If nested speaking_metrics is a string, parse it
            if isinstance(raw, dict):
                sm = raw.get('speaking_metrics')
                if isinstance(sm, str):
                    try:
                        raw['speaking_metrics'] = json.loads(sm)
                        changed = True
                    except Exception:
                        # try eval as last resort
                        try:
                            raw['speaking_metrics'] = eval(sm)
                            changed = True
                        except Exception:
                            pass

            if changed:
                ev.raw_metrics = raw
                db.session.add(ev)
                fixed += 1

        if fixed > 0:
            db.session.commit()

        print(f"Processed {total} evaluations, normalized {fixed} rows.")


if __name__ == '__main__':
    main()
