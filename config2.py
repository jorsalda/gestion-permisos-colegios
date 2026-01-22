# settings.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave_super_segura'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/permisos'# ← SIN CONTRASEÑA, SIN DOS PUNTOS
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = True

def test_db_connection():
    """Prueba si la conexión a la base de datos es exitosa."""
    print("🔍 Verificando conexión a la base de datos...")

    try:
        engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
        with engine.connect() as conn:
           print("✅ Conexión exitosa a MySQL (desde settings.py)")
    except OperationalError as e:
        print("❌ Error de conexión a MySQL:")
        print(e)
    except Exception as ex:
        print("⚠️ Error inesperado al conectar:")
        print(ex)

# Ejecutar la prueba solo si este archivo se ejecuta directamente
if __name__ == "__main__":
    test_db_connection()