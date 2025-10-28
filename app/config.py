import os
from dotenv import load_dotenv

# Cargar el archivo .env
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY","clave_super_secreta")
    print(os.getenv("DATABASE_URI"), flush=True)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Usar ruta absoluta para UPLOAD_FOLDER
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    
    # Asegurar que el directorio existe
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
