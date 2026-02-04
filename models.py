from datetime import datetime, timedelta
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    colegio_id = db.Column(db.Integer, db.ForeignKey('colegios.id'))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    estatus = db.Column(db.String(20), default='activo')
    fecha_limite_prueba = db.Column(db.DateTime, nullable=True)
    aprobado_permanentemente = db.Column(db.Boolean, default=False)

    # Relaciones
    colegio = db.relationship('Colegio', backref='usuarios')

    def tiene_acceso(self):
        """Verifica si el usuario tiene acceso al sistema"""
        # 1. Si está aprobado permanentemente
        if self.aprobado_permanentemente:
            return True

        # 2. Si no tiene fecha límite
        if self.fecha_limite_prueba is None:
            return True

        # 3. Verificar si la fecha actual está dentro del período de prueba
        return datetime.utcnow() <= self.fecha_limite_prueba

    def dias_restantes_prueba(self):
        """Calcula los días restantes de prueba"""
        if not self.fecha_limite_prueba:
            return 0
        dias = (self.fecha_limite_prueba - datetime.utcnow()).days
        return max(0, dias)

    def establecer_periodo_prueba(self, dias=30):
        """Establece un período de prueba para el usuario"""
        self.fecha_limite_prueba = datetime.utcnow() + timedelta(days=dias)
        self.aprobado_permanentemente = False

    def aprobar_permanentemente(self):
        """Aprueba al usuario permanentemente"""
        self.aprobado_permanentemente = True
        self.fecha_limite_prueba = None

    def __repr__(self):
        return f'<Usuario {self.email}>'


class Colegio(db.Model):
    __tablename__ = 'colegios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200))
    telefono = db.Column(db.String(20))


class Docente(db.Model):
    __tablename__ = 'docentes'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    colegio_id = db.Column(db.Integer, db.ForeignKey('colegios.id'))

    # Relación con colegio
    colegio = db.relationship('Colegio', backref='docentes')


class Permiso(db.Model):
    __tablename__ = 'permisos'

    id = db.Column(db.Integer, primary_key=True)
    docente_id = db.Column(db.Integer, db.ForeignKey('docentes.id'))
    colegio_id = db.Column(db.Integer, db.ForeignKey('colegios.id'))
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    observacion = db.Column(db.Text)
    aprobado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

    # Relaciones
    docente = db.relationship('Docente', backref='permisos')
    colegio = db.relationship('Colegio', backref='permisos')