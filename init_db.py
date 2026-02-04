import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Colegio, Usuario, Docente, Permiso
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

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

            # Crear usuario administrador (TÚ) - PERMANENTE
            admin = Usuario(
                email="jorsalda@gmail.com",
                password_hash=generate_password_hash("admin123", method='pbkdf2:sha256'),
                colegio_id=colegio.id,
                fecha_registro=datetime.utcnow() - timedelta(days=30),
                estatus='activo',
                fecha_limite_prueba=datetime.utcnow() + timedelta(days=36500),  # 100 años
                aprobado_permanentemente=True
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Usuario administrador creado (email: jorsalda@gmail.com, password: admin123)")
            print("   Estado: ACTIVO (permanente)")

            # Crear usuario TEMPORAL (días restantes)
            usuario_temporal = Usuario(
                email="temporal@colegio.com",
                password_hash=generate_password_hash("temporal123", method='pbkdf2:sha256'),
                colegio_id=colegio.id,
                fecha_registro=datetime.utcnow() - timedelta(days=5),
                estatus='temporal',
                fecha_limite_prueba=datetime.utcnow() + timedelta(days=10),  # 10 días restantes
                aprobado_permanentemente=False
            )
            db.session.add(usuario_temporal)
            db.session.commit()
            print("✅ Usuario temporal creado (email: temporal@colegio.com, password: temporal123)")
            print("   Estado: TEMPORAL (10 días restantes)")

            # Crear usuario VENCIDO
            usuario_vencido = Usuario(
                email="vencido@colegio.com",
                password_hash=generate_password_hash("vencido123", method='pbkdf2:sha256'),
                colegio_id=colegio.id,
                fecha_registro=datetime.utcnow() - timedelta(days=20),
                estatus='pendiente_aprobacion',
                fecha_limite_prueba=datetime.utcnow() - timedelta(days=5),  # Venció hace 5 días
                aprobado_permanentemente=False
            )
            db.session.add(usuario_vencido)
            db.session.commit()
            print("✅ Usuario vencido creado (email: vencido@colegio.com, password: vencido123)")
            print("   Estado: PENDIENTE_APROBACION (vencido hace 5 días)")

            # Crear docentes de ejemplo
            docentes_nombres = ["Juan Pérez", "María García", "Carlos López", "Ana Martínez"]
            for nombre in docentes_nombres:
                docente = Docente(nombre=nombre, colegio_id=colegio.id)
                db.session.add(docente)

            db.session.commit()
            print("✅ 4 docentes de ejemplo creados")

            print("\n" + "=" * 60)
            print("📋 USUARIOS DE PRUEBA DISPONIBLES:")
            print("=" * 60)
            print("1. jorsalda@gmail.com / admin123 - ADMIN (permanente)")
            print("2. temporal@colegio.com / temporal123 - TEMPORAL (10 días restantes)")
            print("3. vencido@colegio.com / vencido123 - VENCIDO (esperando aprobación)")
            print("=" * 60)

        else:
            print("ℹ️ Ya existen datos en la base de datos")

        print("\n🎉 Base de datos inicializada correctamente")

    except Exception as e:
        print(f"❌ Error al inicializar la base de datos: {e}")
        import traceback

        traceback.print_exc()