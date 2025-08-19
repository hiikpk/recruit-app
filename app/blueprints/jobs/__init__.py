from flask import Blueprint
bp = Blueprint("jobs", __name__)
from . import forms  # noqa (forms registers job endpoints)