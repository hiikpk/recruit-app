from flask import Blueprint
bp = Blueprint("interviews", __name__, template_folder="../../templates/interviews")
from . import routes  # noqa