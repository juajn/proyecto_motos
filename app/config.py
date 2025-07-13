import os

class Config:
    SECRET_KEY = 'clave_secreta_segura'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root@localhost/taller_mecanico'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    MERCADOPAGO_ACCESS_TOKEN = "TEST-763200795261461-071220-c43bf47d7e740ff1b22180ccb81212e0-1683565446"

