import os
import sys

# ensure project root is on sys.path so `import app` works when running this script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db
from app.models.recording import Recording
from app.models.evaluation import Evaluation
from app.jobs.transcribe import transcribe_recording

# Simple synchronous test that calls transcribe_recording directly (without RQ)
# It requires a Recording with id=1 to exist in the DB and to have interview_id set.

REC_ID = 1

app = create_app()
with app.app_context():
    rec = Recording.query.get(REC_ID)
    if not rec:
        # create minimal Interview and Recording to exercise pipeline
        from app.models.interview import Interview
        from app.models.candidate import Candidate
        # create a candidate
        from datetime import datetime
        now = datetime.utcnow().replace(microsecond=0)
        cand = Candidate(
            org_id=1,
            name="Smoke Test Candidate",
            applied_at=now.date(),
            created_at=now,
            updated_at=now,
        )
        db.session.add(cand)
        db.session.flush()
        interview = Interview(
            org_id=1,
            candidate_id=cand.id,
            status='done',
            created_at=now,
            updated_at=now,
        )
        db.session.add(interview)
        db.session.flush()
        # create dummy local audio file
        import os as _os
        local_dir = app.config.get('LOCAL_STORAGE_DIR', 'local_storage')
        _os.makedirs(local_dir, exist_ok=True)
        sample_path = _os.path.join(local_dir, 'smoke_test.wav')
        with open(sample_path, 'wb') as f:
            f.write(b"RIFF....")
        rec = Recording(
            org_id=1,
            interview_id=interview.id,
            storage_url=f"file://{_os.path.abspath(sample_path)}",
            created_at=now,
            updated_at=now,
        )
        db.session.add(rec)
        db.session.commit()
        REC_ID = rec.id
        print(f"Created Recording id={REC_ID} for Interview id={interview.id}")

    tr_id = transcribe_recording(REC_ID)
    print("Created Transcript id:", tr_id)
    # Check latest evaluation for interview
    rec = Recording.query.get(REC_ID)
    int_id = rec.interview_id
    ev = Evaluation.query.filter_by(interview_id=int_id).order_by(Evaluation.created_at.desc()).first()
    if ev:
        print("Evaluation created id:", ev.id, "score:", ev.overall_score)
    else:
        print("No evaluation created for interview id:", int_id)
