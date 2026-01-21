from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
class Colegio(db.Model):
    __tablename__ = 'colegios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False, unique=True)

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    colegio_id = db.Column(db.Integer, db.ForeignKey('colegios.id'), nullable=False)

    # 👇 AÑADE ESTO:
    def get_id(self):
        return str(self.id)  # Flask-Login requiere que sea string

    is_active = True
    colegio = db.relationship('Colegio', backref='usuarios')


class Docente(db.Model):
    __tablename__ = 'docentes'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    colegio_id = db.Column(db.Integer, db.ForeignKey('colegios.id'), nullable=False)  # ← NUEVO

    colegio = db.relationship('Colegio', backref='docentes')
    permisos = db.relationship('Permiso', back_populates='docente', cascade='all, delete-orphan')

class Permiso(db.Model):
    __tablename__ = 'permisos'
    id = db.Column(db.Integer, primary_key=True)
    docente_id = db.Column(db.Integer, db.ForeignKey('docentes.id'), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(100), nullable=False)
    observacion = db.Column(db.Text)
    colegio_id = db.Column(db.Integer, db.ForeignKey('colegios.id'), nullable=False)  # ← NUEVO

    docente = db.relationship('Docente', back_populates='permisos')
    colegio = db.relationship('Colegio', backref='permisos')