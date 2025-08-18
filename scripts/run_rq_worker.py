"""Run an RQ worker inside the Flask app context.

Usage:
  source .venv/bin/activate
  export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES   # macOS fork safety if needed
  python scripts/run_rq_worker.py

This ensures the app and extensions are initialized in the worker process
so jobs that use `current_app` or the Flask-SQLAlchemy session work normally.
"""

import sys
import os

# Ensure project root is on sys.path when running from scripts/ or other cwd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
  sys.path.insert(0, ROOT)

from app import create_app
import redis
from rq import Worker, Queue, Connection


def main():
  app = create_app()
  redis_url = app.config.get('REDIS_URL') or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
  conn = redis.from_url(redis_url)
  with app.app_context():
    q = Queue('default', connection=conn)
    worker = Worker([q], connection=conn)
    print('RQ worker starting (pid', os.getpid(), ')')
    try:
            # run in long-running mode (not burst) and show verbose logs for debugging
            worker.work(burst=False, with_scheduler=True, logging_level='DEBUG')
    finally:
      print('RQ worker exiting (pid', os.getpid(), ')')


if __name__ == '__main__':
  main()
