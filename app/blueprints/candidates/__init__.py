from flask import Blueprint
bp = Blueprint("candidates", __name__, template_folder="../../templates/candidates")
from . import routes  # noqa