from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import redis
from redis import Redis
from rq import Queue
from flask import current_app

class RQWrapper:
    def __init__(self):
        self.redis = None
        self.queue = None

    def init_app(self, app):
        try:
            self.redis = Redis.from_url(app.config.get("REDIS_URL"))
            self.queue = Queue("default", connection=self.redis)
        except Exception:
            # if Redis is not available (dev machine, no redis server),
            # leave queue as None and fall back to synchronous execution
            try:
                current_app.logger.exception('Redis/RQ init failed, falling back to sync execution')
            except Exception:
                pass
            self.redis = None
            self.queue = None

    def enqueue(self, *args, **kwargs):
        # Prefer enqueueing to RQ if available, but fall back to calling
        # the function synchronously if Redis/RQ is not reachable.
        if not self.queue:
            # synchronous fallback
            func = args[0] if args else None
            func_args = args[1:] if len(args) > 1 else ()
            # strip common RQ kwargs that are not valid for the function call
            rq_keys = {'job_timeout', 'timeout', 'at_front', 'depends_on', 'result_ttl', 'ttl', 'meta', 'description'}
            safe_kwargs = {k: v for k, v in kwargs.items() if k not in rq_keys}
            try:
                if func:
                    return func(*func_args, **safe_kwargs)
            except Exception:
                try:
                    current_app.logger.exception('Synchronous fallback execution failed')
                except Exception:
                    pass
            return None

        try:
            return self.queue.enqueue(*args, **kwargs)
        except Exception as e:
            # If enqueue fails due to Redis being down, fall back to sync execution.
            try:
                current_app.logger.exception('RQ enqueue failed, falling back to sync execution')
            except Exception:
                pass
            func = args[0] if args else None
            func_args = args[1:] if len(args) > 1 else ()
            rq_keys = {'job_timeout', 'timeout', 'at_front', 'depends_on', 'result_ttl', 'ttl', 'meta', 'description'}
            safe_kwargs = {k: v for k, v in kwargs.items() if k not in rq_keys}
            try:
                if func:
                    return func(*func_args, **safe_kwargs)
            except Exception:
                try:
                    current_app.logger.exception('Synchronous fallback execution after enqueue failure also failed')
                except Exception:
                    pass
            return None


db = SQLAlchemy()
login_manager = LoginManager()
rq = RQWrapper()