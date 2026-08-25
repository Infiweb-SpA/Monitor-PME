"""Blueprint de ingesta de datos."""
from flask import Blueprint, render_template
from flask_login import login_required

ingesta_bp = Blueprint("ingesta", __name__, template_folder="../templates/ingesta")


@ingesta_bp.route("/")
@login_required
def index():
    return render_template("ingesta/index.html")