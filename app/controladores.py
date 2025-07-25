from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db, bcrypt, login_manager
from models import Usuario, Producto, Trabajo ,db
from datetime import datetime, timedelta
import os
from config import Config
from flask import session
import mercadopago


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
        upload_path = Config.UPLOAD_FOLDER
        # Crear carpeta si no existe
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
        file.save(os.path.join(upload_path, filename))
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

    # Conteo por rol de usuario
    roles = ['admin', 'mecanico', 'usuario']
    conteo_roles = [Usuario.query.filter_by(rol=rol).count() for rol in roles]

    # Conteo de productos por categorías simuladas
    categorias = ['Llantas', 'Aceites', 'Herramientas']
    conteo_categorias = [
        Producto.query.filter(Producto.nombre.ilike('%llanta%')).count(),
        Producto.query.filter(Producto.nombre.ilike('%aceite%')).count(),
        Producto.query.filter(Producto.nombre.ilike('%herramienta%')).count()
    ]

    # Conteo de trabajos por día (últimos 5 días)
    hoy = datetime.now().date()
    fechas = [(hoy - timedelta(days=i)) for i in reversed(range(5))]
    labels_fechas = [fecha.strftime('%d/%m') for fecha in fechas]
    conteo_trabajos = [
        Trabajo.query.filter(db.func.date(Trabajo.fecha_creacion) == fecha).count()
        for fecha in fechas
    ]

    return render_template(
        'admin/dashboard_admin.html',
        usuario=current_user,
        stats=stats,
        roles=roles,
        conteo_roles=conteo_roles,
        categorias=categorias,
        conteo_categorias=conteo_categorias,
        labels_fechas=labels_fechas,
        conteo_trabajos=conteo_trabajos
    )

# ------------------
# CRUD Usuarios
# ------------------
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

# ------------------
# CRUD Productos
# ------------------
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
        nuevo = Producto(nombre=nombre, descripcion=descripcion, precio=precio, stock=stock, foto=nombre_imagen)
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
        if imagen and imagen.filename != '':
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

# ------------------
# CRUD Trabajos 
# ------------------
@admin_bp.route('/trabajos')
@login_required
def listar_trabajos():
    if current_user.rol != 'admin':
        abort(403)

    trabajos = Trabajo.query.all()
    mecanicos = Usuario.query.filter_by(rol='mecanico').all()
    clientes = Usuario.query.filter_by(rol='usuario').all()

    return render_template(
        'admin/trabajos/index.html',
        trabajos=trabajos,
        mecanicos=mecanicos,
        clientes=clientes
    )


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
@mecanico_bp.route('/trabajo/<int:id>/cambiar_estado', methods=['POST'])
@login_required
def cambiar_estado(id):
    nuevo_estado = request.form.get('estado')
    trabajo = Trabajo.query.get_or_404(id)

    if trabajo.mecanico_id != current_user.id:
        abort(403)

    trabajo.estado = nuevo_estado
    db.session.commit()
    flash("Estado actualizado correctamente", "success")
    return redirect(url_for('mecanico.dashboard'))



# ------------------
# DASHBOARD USUARIO
# ------------------
@usuario_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.rol != 'usuario':
        abort(403)
    trabajos = Trabajo.query.filter_by(cliente_id=current_user.id).all()
    productos = Producto.query.all()  
    return render_template('usuario/dashboard_usuario.html', usuario=current_user, trabajos=trabajos, productos=productos)


@usuario_bp.route('/carrito')
@login_required
def ver_carrito():
    carrito = session.get('carrito', [])
    # Asegurar que todos tengan cantidad
    for item in carrito:
        if 'cantidad' not in item:
            item['cantidad'] = 1
    session['carrito'] = carrito  # Guardar actualización
    total = sum(p['precio'] * p['cantidad'] for p in carrito)
    return render_template('usuario/carrito.html', carrito=carrito, total=total)


@usuario_bp.route('/agregar_carrito/<int:producto_id>', methods=['POST'])
@login_required
def agregar_carrito(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    try:
        cantidad = int(request.form.get('cantidad', 1))
    except ValueError:
        cantidad = 1

    carrito = session.get('carrito', [])

    for item in carrito:
        if item['id'] == producto.id:
            item['cantidad'] += cantidad
            break
    else:
        carrito.append({
            'id': producto.id,
            'nombre': producto.nombre,
            'precio': producto.precio,
            'foto': producto.foto,
            'cantidad': cantidad
        })

    session['carrito'] = carrito
    flash('Producto agregado al carrito.', 'success')
    return redirect(url_for('usuario.dashboard'))



@usuario_bp.route('/eliminar_carrito/<int:producto_id>', methods=['POST'])
@login_required
def eliminar_del_carrito(producto_id):
    carrito = session.get('carrito', [])
    carrito = [p for p in carrito if p['id'] != producto_id]
    session['carrito'] = carrito
    flash('Producto eliminado del carrito.', 'info')
    return redirect(url_for('usuario.ver_carrito'))

@usuario_bp.route('/vaciar_carrito', methods=['POST'])
@login_required
def vaciar_carrito():
    session.pop('carrito', None)
    flash('Carrito vaciado.', 'warning')
    return redirect(url_for('usuario.ver_carrito'))

@usuario_bp.route('/comprar', methods=['POST'])
@login_required
def comprar_carrito():
    session.pop('carrito', None)
    flash("¡Compra realizada con éxito!", "success")
    return redirect(url_for('usuario.dashboard'))

@usuario_bp.route('/pagar', methods=['POST'])
@login_required
def pagar():
    carrito = session.get('carrito', [])
    if not carrito:
        flash("El carrito está vacío", "warning")
        return redirect(url_for('usuario.ver_carrito'))

    sdk = mercadopago.SDK(current_app.config['MERCADOPAGO_ACCESS_TOKEN'])

    items = []
    for item in carrito:
        cantidad = item.get('cantidad', 1)
        items.append({
            "title": item['nombre'],
            "quantity": cantidad,
            "unit_price": float(item['precio']),
            "currency_id": "COP"
        })

    preference_data = {
        "items": items,
        "back_urls": {
            "success": url_for('usuario.compra_exitosa', _external=True),
            "failure": url_for('usuario.ver_carrito', _external=True),
            "pending": url_for('usuario.ver_carrito', _external=True)
        },
        "auto_return": "approved"
    }

    preference_response = sdk.preference().create(preference_data)
    print("Respuesta MercadoPago:", preference_response)

    preference = preference_response.get("response", {})

    if 'init_point' not in preference:
        flash("Error al generar la pasarela de pago", "danger")
        return redirect(url_for('usuario.ver_carrito'))

    return redirect(preference["init_point"])


@usuario_bp.route('/compra_exitosa')
@login_required
def compra_exitosa():
    session.pop('carrito', None)
    flash("¡Compra realizada con éxito!", "success")
    return redirect(url_for('usuario.dashboard'))

