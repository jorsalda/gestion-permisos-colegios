import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave_super_segura'

    # Base de datos temporal (SQLite) SOLO para que Render arranque
    SQLALCHEMY_DATABASE_URI = 'sqlite:///temp.db'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = True