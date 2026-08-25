"""Blueprint de autenticación."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required

from app.models.user import User

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Muestra el formulario de login y procesa la autenticación."""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email, activo=True).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Bienvenido, {user.nombre}", "success")
            return redirect(url_for("dashboard.index"))
        else:
            flash("Credenciales incorrectas. Intente nuevamente.", "danger")
            return redirect(url_for("auth.login"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Cierra la sesión del usuario."""
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.login"))