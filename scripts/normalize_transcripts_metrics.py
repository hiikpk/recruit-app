#!/usr/bin/env python3
"""Normalize transcripts.metrics JSON stored as strings.

Iterate transcripts rows, if metrics is a string attempt to json.loads it.
If nested speaking_metrics is a string, json.loads it as well.
"""
import os, sys, json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from app.extensions import db
from app.models.transcript import Transcript


def main():
    app = create_app()
    with app.app_context():
        rows = Transcript.query.order_by(Transcript.id).all()
        total = len(rows)
        fixed = 0
        for tr in rows:
            m = tr.metrics
            changed = False
            if isinstance(m, str):
                try:
                    m = json.loads(m)
                    changed = True
                except Exception:
                    # try eval as last resort
                    try:
                        m = eval(m)
                        if isinstance(m, dict):
                            changed = True
                        else:
                            m = None
                    except Exception:
                        m = None
            if isinstance(m, dict):
                sm = m.get('speaking_metrics')
                if isinstance(sm, str):
                    try:
                        m['speaking_metrics'] = json.loads(sm)
                        changed = True
                    except Exception:
                        try:
                            parsed = eval(sm)
                            if isinstance(parsed, dict):
                                m['speaking_metrics'] = parsed
                                changed = True
                        except Exception:
                            pass
            if changed:
                tr.metrics = m
                db.session.add(tr)
                fixed += 1
        if fixed > 0:
            db.session.commit()
        print(f"Processed {total} transcripts, normalized {fixed} rows.")

if __name__ == '__main__':
    main()
