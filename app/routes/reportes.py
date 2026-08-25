"""Blueprint de reportes."""
from flask import Blueprint, render_template
from flask_login import login_required

reportes_bp = Blueprint("reportes", __name__, template_folder="../templates/reportes")


@reportes_bp.route("/")
@login_required
def index():
    return render_template("reportes/index.html")