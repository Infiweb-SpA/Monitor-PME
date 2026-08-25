"""Blueprint de acciones PME."""
from flask import Blueprint, render_template
from flask_login import login_required

acciones_bp = Blueprint("acciones", __name__, template_folder="../templates/acciones")


@acciones_bp.route("/")
@login_required
def index():
    return render_template("acciones/index.html")