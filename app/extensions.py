from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from redis import Redis
from rq import Queue
from flask import current_app

class RQWrapper:
    def __init__(self):
        self.redis = None
        self.queue = None

    def init_app(self, app):
        self.redis = Redis.from_url(app.config["REDIS_URL"])
        self.queue = Queue("default", connection=self.redis)

    def enqueue(self, *args, **kwargs):
        return self.queue.enqueue(*args, **kwargs)


db = SQLAlchemy()
login_manager = LoginManager()
rq = RQWrapper()