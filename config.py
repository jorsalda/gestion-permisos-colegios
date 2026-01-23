import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Clave secreta para sesiones (Render generará una automáticamente)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-temporal-desarrollo-123'

    # Configuración de base de datos para PlanetScale
    database_url = os.environ.get('DATABASE_URL', '')

    if database_url:
        print(f"🔗 Usando DATABASE_URL proporcionada")
        # PlanetScale usa formato mysql://, necesitamos mysql+pymysql://
        if database_url.startswith('mysql://'):
            SQLALCHEMY_DATABASE_URI = database_url.replace('mysql://', 'mysql+pymysql://')
        else:
            SQLALCHEMY_DATABASE_URI = database_url
    else:
        # Desarrollo local (sin SSL)
        SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/permisos'
        print("🔧 Usando base de datos local")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuración importante para producción
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,  # Reconectar cada 5 minutos
        "pool_pre_ping": True,  # Verificar conexión antes de usar
        "pool_size": 10,
        "max_overflow": 20,
    }

    # SSL para PlanetScale
    if 'psdb.cloud' in database_url:
        print("🔐 Configurando SSL para PlanetScale")
        SQLALCHEMY_ENGINE_OPTIONS["connect_args"] = {
            "ssl": {
                "ssl_ca": "/etc/ssl/certs/ca-certificates.crt"
            }
        }