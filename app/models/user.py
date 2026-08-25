"""Modelo de usuario y autenticación para EduGest PME."""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    """Representa un usuario del sistema EduGest PME."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(50), nullable=False, default="Encargado PME")
    activo = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación con establecimiento
    establecimiento_id = db.Column(
        db.Integer, db.ForeignKey("establecimientos.id"), nullable=True
    )
    establecimiento = db.relationship("Establecimiento", back_populates="usuarios")

    # Constantes de roles permitidos
    ROL_DIRECTOR = "Director"
    ROL_UTP = "UTP"
    ROL_ENCARGADO_PME = "Encargado PME"
    ROL_SOSTENEDOR = "Sostenedor"
    ROL_ADMIN = "Administrador"

    ROLES_VALIDOS = [
        ROL_DIRECTOR,
        ROL_UTP,
        ROL_ENCARGADO_PME,
        ROL_SOSTENEDOR,
        ROL_ADMIN,
    ]

    def set_password(self, password):
        """Genera y almacena el hash de la contraseña."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica si la contraseña coincide con el hash almacenado."""
        return check_password_hash(self.password_hash, password)

    def es_admin(self):
        """Retorna True si el usuario tiene rol de administrador o director."""
        return self.rol in (self.ROL_ADMIN, self.ROL_DIRECTOR)

    def es_sostenedor(self):
        """Retorna True si el usuario es sostenedor."""
        return self.rol == self.ROL_SOSTENEDOR

    def __repr__(self):
        return f"<User {self.email} ({self.rol})>"


@login_manager.user_loader
def load_user(user_id):
    """Callback requerido por Flask-Login para cargar usuarios por ID."""
    return User.query.get(int(user_id))