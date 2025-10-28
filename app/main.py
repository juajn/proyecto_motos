from flask import Flask, redirect
import os
import random
from config import Config
from extensions import db, login_manager, bcrypt

app = Flask(__name__)
app.secret_key = "clave-ultra-secreta"
app_name = os.getenv("APP_NAME", "Aplicacion Flask")
def create_app():
    app = Flask(__name__, template_folder='templates')
    app.config.from_object(Config)

    # Crear carpeta de subidas si no existe
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # Inicializar extensiones
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    

    # Registrar Blueprints
    from controladores import auth_bp, admin_bp, mecanico_bp, usuario_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(mecanico_bp)
    app.register_blueprint(usuario_bp)

    return app  
app = create_app()
@app.template_filter('shuffle')
def shuffle_filter(seq):
    seq = list(seq)
    random.shuffle(seq)
    return seq
@app.route('/')
def inicio():
    return redirect('/principal')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
