from flask import Blueprint
bp = Blueprint("org", __name__)
from .routes import bp  # noqa