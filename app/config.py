import os

class Config:
    SECRET_KEY = 'clave_secreta_segura'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root@localhost/taller_mecanico'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
