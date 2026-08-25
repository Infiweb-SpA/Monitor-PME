"""Blueprint de configuración."""
from flask import Blueprint, render_template
from flask_login import login_required

config_bp = Blueprint("config", __name__, template_folder="../templates/configuracion")


@config_bp.route("/")
@login_required
def index():
    return render_template("configuracion/index.html")