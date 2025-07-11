
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db, bcrypt, login_manager
from models import Usuario, Producto, Trabajo
from datetime import datetime
import os
from config import Config

# Blueprints
auth_bp = Blueprint('auth', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
mecanico_bp = Blueprint('mecanico', __name__, url_prefix='/mecanico')
usuario_bp = Blueprint('usuario', __name__, url_prefix='/usuario')

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
        file.save(os.path.join(Config.UPLOAD_FOLDER, filename))
        return filename
    return None

# ------------------
# AUTENTICACION
# ------------------
@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        rol = request.form['rol']
        nombre = request.form['nombre']
        archivo = request.files.get('imagen')

        if Usuario.query.filter_by(correo=correo).first():
            flash('El correo ya está registrado.', 'danger')
            return redirect(url_for('auth.registro'))

        hash_contraseña = bcrypt.generate_password_hash(contraseña).decode('utf-8')
        nombre_imagen = save_uploaded_file(archivo)

        nuevo_usuario = Usuario(
            correo=correo,
            contraseña=hash_contraseña,
            rol=rol,
            nombre=nombre,
            imagen=nombre_imagen
        )
        db.session.add(nuevo_usuario)
        db.session.commit()

        flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        contraseña = request.form['contraseña']

        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario and bcrypt.check_password_hash(usuario.contraseña, contraseña):
            login_user(usuario)
            flash(f'Bienvenido, {usuario.nombre}', 'success')

            if usuario.rol == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif usuario.rol == 'mecanico':
                return redirect(url_for('mecanico.dashboard'))
            elif usuario.rol == 'usuario':
                return redirect(url_for('usuario.dashboard'))
            else:
                abort(403)
        else:
            flash('Credenciales inválidas.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))

# ------------------
# DASHBOARDS
# ------------------
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.rol != 'admin':
        abort(403)
    stats = {
        'usuarios': Usuario.query.count(),
        'productos': Producto.query.count(),
        'trabajos': Trabajo.query.count()
    }
    return render_template('admin/dashboard_admin.html', usuario=current_user, stats=stats)

@admin_bp.route('/usuarios')
@login_required
def listar_usuarios():
    if current_user.rol != 'admin':
        abort(403)
    usuarios = Usuario.query.all()
    return render_template('admin/usuarios/index.html', usuarios=usuarios)

@admin_bp.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    if current_user.rol != 'admin':
        abort(403)
    usuario = Usuario.query.get_or_404(id)
    if request.method == 'POST':
        usuario.nombre = request.form['nombre']
        usuario.rol = request.form['rol']
        db.session.commit()
        flash('Usuario actualizado.', 'success')
        return redirect(url_for('admin.listar_usuarios'))
    return render_template('admin/usuarios/editar.html', usuario=usuario)

@admin_bp.route('/usuarios/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_usuario(id):
    if current_user.rol != 'admin':
        abort(403)
    usuario = Usuario.query.get_or_404(id)
    db.session.delete(usuario)
    db.session.commit()
    flash('Usuario eliminado.', 'success')
    return redirect(url_for('admin.listar_usuarios'))

@admin_bp.route('/productos')
@login_required
def listar_productos():
    if current_user.rol != 'admin':
        abort(403)
    productos = Producto.query.all()
    return render_template('admin/productos/index.html', productos=productos)

@admin_bp.route('/productos/crear', methods=['GET', 'POST'])
@login_required
def crear_producto():
    if current_user.rol != 'admin':
        abort(403)
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        stock = request.form['stock']
        imagen = request.files.get('imagen')
        nombre_imagen = save_uploaded_file(imagen)
        nuevo = Producto(nombre=nombre, descripcion=descripcion, precio=precio, stock=stock, imagen=nombre_imagen)
        db.session.add(nuevo)
        db.session.commit()
        flash('Producto creado.', 'success')
        return redirect(url_for('admin.listar_productos'))
    return render_template('admin/productos/crear.html')

@admin_bp.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_producto(id):
    if current_user.rol != 'admin':
        abort(403)
    producto = Producto.query.get_or_404(id)
    if request.method == 'POST':
        producto.nombre = request.form['nombre']
        producto.descripcion = request.form['descripcion']
        producto.precio = request.form['precio']
        producto.stock = request.form['stock']
        imagen = request.files.get('imagen')
        if imagen:
            producto.imagen = save_uploaded_file(imagen)
        db.session.commit()
        flash('Producto actualizado.', 'success')
        return redirect(url_for('admin.listar_productos'))
    return render_template('admin/productos/editar.html', producto=producto)

@admin_bp.route('/productos/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_producto(id):
    if current_user.rol != 'admin':
        abort(403)
    producto = Producto.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    flash('Producto eliminado.', 'success')
    return redirect(url_for('admin.listar_productos'))

@admin_bp.route('/trabajos')
@login_required
def listar_trabajos():
    if current_user.rol != 'admin':
        abort(403)
    trabajos = Trabajo.query.all()
    return render_template('admin/trabajos/index.html', trabajos=trabajos)

@admin_bp.route('/trabajos/crear', methods=['GET', 'POST'])
@login_required
def crear_trabajo():
    if current_user.rol != 'admin':
        abort(403)

    if request.method == 'POST':
        descripcion = request.form['descripcion']
        estado = request.form['estado']
        mecanico_id = request.form['mecanico_id']
        cliente_id = request.form['cliente_id']
        foto_file = request.files.get('foto')
        nombre_foto = save_uploaded_file(foto_file)

        nuevo_trabajo = Trabajo(
            descripcion=descripcion,
            estado=estado,
            foto=nombre_foto,
            mecanico_id=mecanico_id,
            cliente_id=cliente_id,
            fecha_creacion=datetime.now()
        )
        db.session.add(nuevo_trabajo)
        db.session.commit()
        flash("Trabajo creado correctamente.", "success")
        return redirect(url_for('admin.listar_trabajos'))

    mecanicos = Usuario.query.filter_by(rol='mecanico').all()
    clientes = Usuario.query.filter_by(rol='usuario').all()
    return render_template('admin/trabajos/crear_trabajo.html', mecanicos=mecanicos, clientes=clientes)

@admin_bp.route('/trabajos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_trabajo(id):
    if current_user.rol != 'admin':
        abort(403)

    trabajo = Trabajo.query.get_or_404(id)

    if request.method == 'POST':
        trabajo.descripcion = request.form['descripcion']
        trabajo.estado = request.form['estado']
        trabajo.mecanico_id = request.form['mecanico_id']
        trabajo.cliente_id = request.form['cliente_id']

        foto_file = request.files.get('foto')
        if foto_file:
            trabajo.foto = save_uploaded_file(foto_file)

        db.session.commit()
        flash("Trabajo actualizado correctamente.", "success")
        return redirect(url_for('admin.listar_trabajos'))

    mecanicos = Usuario.query.filter_by(rol='mecanico').all()
    clientes = Usuario.query.filter_by(rol='usuario').all()
    return render_template('admin/trabajos/editar_trabajo.html', trabajo=trabajo, mecanicos=mecanicos, clientes=clientes)

@admin_bp.route('/trabajos/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_trabajo(id):
    if current_user.rol != 'admin':
        abort(403)

    trabajo = Trabajo.query.get_or_404(id)
    db.session.delete(trabajo)
    db.session.commit()
    flash("Trabajo eliminado correctamente.", "success")
    return redirect(url_for('admin.listar_trabajos'))
# ------------------
# DASHBOARD MECÁNICO
# ------------------
@mecanico_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.rol != 'mecanico':
        abort(403)
    trabajos = Trabajo.query.filter_by(mecanico_id=current_user.id).all()
    return render_template('mecanico/dashboard_mecanico.html', usuario=current_user, trabajos=trabajos)

# Crear nuevo trabajo (para mecánico)
@mecanico_bp.route('/trabajos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_trabajo():
    if current_user.rol != 'mecanico':
        abort(403)

    if request.method == 'POST':
        descripcion = request.form['descripcion']
        cliente_id = request.form['cliente_id']
        foto_file = request.files.get('foto')
        nombre_foto = save_uploaded_file(foto_file)

        nuevo_trabajo = Trabajo(
            descripcion=descripcion,
            estado='pendiente',
            foto=nombre_foto,
            mecanico_id=current_user.id,
            cliente_id=cliente_id,
            fecha_creacion=datetime.now()
        )
        db.session.add(nuevo_trabajo)
        db.session.commit()
        flash("Trabajo creado por el mecánico.", "success")
        return redirect(url_for('mecanico.dashboard'))

    clientes = Usuario.query.filter_by(rol='usuario').all()
    return render_template('mecanico/nuevo_trabajo.html', clientes=clientes)

# ------------------
# DASHBOARD USUARIO
# ------------------
@usuario_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.rol != 'usuario':
        abort(403)
    trabajos = Trabajo.query.filter_by(cliente_id=current_user.id).all()
    return render_template('usuario/dashboard_usuario.html', usuario=current_user, trabajos=trabajos)
