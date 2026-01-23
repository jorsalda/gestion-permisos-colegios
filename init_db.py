import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Colegio, Usuario, Docente, Permiso
from werkzeug.security import generate_password_hash
from datetime import datetime

print("🚀 Inicializando base de datos...")

with app.app_context():
    try:
        # Crear todas las tablas
        db.create_all()
        print("✅ Tablas creadas exitosamente")

        # Verificar si ya existe un colegio
        if not Colegio.query.first():
            # Crear colegio de ejemplo
            colegio = Colegio(nombre="Colegio Principal")
            db.session.add(colegio)
            db.session.commit()
            print("✅ Colegio creado")

            # Crear usuario admin
            admin = Usuario(
                email="admin@colegio.com",
                password_hash=generate_password_hash("admin123", method='pbkdf2:sha256'),
                colegio_id=colegio.id,
                fecha_registro=datetime.utcnow(),
                estatus='activo'
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Usuario admin creado (email: admin@colegio.com, password: admin123)")
        else:
            print("ℹ️  Ya existen datos en la base de datos")

        print("🎉 Base de datos inicializada correctamente")

    except Exception as e:
        print(f"❌ Error al inicializar la base de datos: {e}")
        import traceback

        traceback.print_exc()