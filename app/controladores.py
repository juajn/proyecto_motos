from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from extensions import db, bcrypt, login_manager
from models import DetalleVenta, Gasto, Usuario, Producto, Trabajo, Venta ,db
from datetime import datetime, timedelta
from sqlalchemy.sql.expression import func
import os
from config import Config
from flask import session
#import mercadopago
import stripe

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


@auth_bp.route('/principal')
def principal():
    q = request.args.get('q', '').strip()
    categoria_id = request.args.get('categoria', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 6  # Máximo 6 productos en la página

    productos_query = Producto.query

    if q:
        productos_query = productos_query.filter(
            (Producto.nombre.ilike(f"%{q}%")) |
            (Producto.descripcion.ilike(f"%{q}%"))
        )

    if categoria_id:
        productos_query = productos_query.filter(Producto.categoria == categoria_id)

    productos_paginated = productos_query.paginate(page=page, per_page=per_page, error_out=False)

    categorias = db.session.query(Producto.categoria).distinct().all()
    categorias = [c[0] for c in categorias if c[0]]

    carrusel = Producto.query.order_by(func.random()).limit(3).all()
    ofertas = Producto.query.order_by(func.random()).limit(3).all()

    return render_template(
        'auth/principal.html',
        productos=productos_paginated.items,
        pagination=productos_paginated,
        categorias=categorias,
        q=q,
        categoria_id=categoria_id,
        carrusel=carrusel,
        ofertas=ofertas
    )
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
        'trabajos': Trabajo.query.count(),
        'ventas': Venta.query.count()
          
    }

    # Conteo por rol de usuario
    roles = ['admin', 'mecanico', 'usuario']
    conteo_roles = [Usuario.query.filter_by(rol=rol).count() for rol in roles]

    # Obtener categorías únicas desde la base de datos
    categorias_db = db.session.query(Producto.categoria).distinct().all()
    categorias = [c[0] for c in categorias_db if c[0]]

    # Conteo de productos por categorías
    conteo_categorias = [Producto.query.filter(Producto.categoria == cat).count() for cat in categorias]

    # Conteo de trabajos por día (últimos 5 días)
    hoy = datetime.now().date()
    fechas_trabajos = [(hoy - timedelta(days=i)) for i in reversed(range(5))]
    labels_fechas = [fecha.strftime('%d/%m') for fecha in fechas_trabajos]
    conteo_trabajos = [
        Trabajo.query.filter(db.func.date(Trabajo.fecha_creacion) == fecha).count()
        for fecha in fechas_trabajos
    ]

    # Conteo de ventas por día (últimos 7 días)
    fechas_ventas = [(hoy - timedelta(days=i)) for i in reversed(range(7))]
    labels_ventas = [fecha.strftime('%d/%m') for fecha in fechas_ventas]
    conteo_ventas = [
        Venta.query.filter(db.func.date(Venta.fecha) == fecha).count()
        for fecha in fechas_ventas
    ]

    # Pasar también mecánicos y clientes para los modales
    mecanicos = Usuario.query.filter_by(rol='mecanico').all()
    clientes = Usuario.query.filter_by(rol='usuario').all()
    vendedores = Usuario.query.filter_by(rol='admin').all()
    productos = Producto.query.all()


    return render_template(
        'admin/dashboard_admin.html',
        usuario=current_user,
        stats=stats,
        roles=roles,
        conteo_roles=conteo_roles,
        categorias=categorias,
        conteo_categorias=conteo_categorias,
        labels_fechas=labels_fechas,
        conteo_trabajos=conteo_trabajos,
        labels_ventas=labels_ventas,   
        conteo_ventas=conteo_ventas,   
        mecanicos=mecanicos,
        clientes=clientes,
        vendedores=vendedores,
        productos=productos
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
@admin_bp.route('/usuarios/crear', methods=['GET', 'POST'])
@login_required
def crear_usuario():
    if current_user.rol != 'admin':
        abort(403)
    if request.method == 'POST':
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        rol = request.form['rol']
        nombre = request.form['nombre']
        archivo = request.files.get('imagen')

        if Usuario.query.filter_by(correo=correo).first():
            flash('El correo ya está registrado.', 'danger')
            return redirect(url_for('admin.usuarios'))

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

        flash('Usuario creado correctamente.', 'success')
        return redirect(url_for('admin.listar_usuarios'))

    return render_template('admin/usuarios/crear.html')
@admin_bp.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    if current_user.rol != 'admin':
        abort(403)

    usuario = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        # Actualizar nombre y correo
        usuario.nombre = request.form['nombre']
        usuario.correo = request.form['correo']
        
        # Actualizar rol
        usuario.rol = request.form['rol']

        # Si se ingresó una nueva contraseña, actualizarla
        nueva_contraseña = request.form.get('contraseña')
        if nueva_contraseña:  # Solo si no está vacío
            from werkzeug.security import generate_password_hash
            usuario.contraseña = generate_password_hash(nueva_contraseña)

        # Guardar cambios
        db.session.commit()
        flash('Usuario actualizado correctamente.', 'success')
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
        categoria = request.form['categoria']
        nombre_imagen = save_uploaded_file(imagen)
        nuevo = Producto(nombre=nombre, descripcion=descripcion, precio=precio, stock=stock, foto=nombre_imagen, categoria=categoria)
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
        producto.categoria = request.form['categoria']
        foto = request.files.get('foto')
        if foto and foto.filename != '':
            producto.foto = save_uploaded_file(foto)

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
    
    # Obtener filtro de estado si existe
    estado = request.args.get('estado')
    
    # Aplicar filtro si se especificó un estado
    if estado:
        trabajos = Trabajo.query.filter_by(estado=estado).all()
    else:
        trabajos = Trabajo.query.all()
    
    # Obtener estadísticas para los paneles
    total_trabajos = Trabajo.query.count()
    trabajos_pagados = Trabajo.query.filter_by(estado='Pagado').count()
    trabajos_pendientes = Trabajo.query.filter_by(estado='Pendiente').count()
    trabajos_en_proceso = Trabajo.query.filter_by(estado='En proceso').count()
    trabajos_completados = Trabajo.query.filter_by(estado='Completado').count()
    
    # Obtener mecánicos y clientes
    mecanicos = Usuario.query.filter_by(rol='mecanico').all()
    clientes = Usuario.query.filter_by(rol='usuario').all()

    return render_template(
        'admin/trabajos/index.html',
        trabajos=trabajos,
        mecanicos=mecanicos,
        clientes=clientes,
        total_trabajos=total_trabajos,
        trabajos_pagados=trabajos_pagados,
        trabajos_pendientes=trabajos_pendientes,
        trabajos_en_proceso=trabajos_en_proceso,
        trabajos_completados=trabajos_completados
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
        costo = request.form.get('costo', type=float, default=0.0)
        nombre_foto = save_uploaded_file(foto_file)

        nuevo_trabajo = Trabajo(
            descripcion=descripcion,
            estado=estado,
            foto=nombre_foto,
            mecanico_id=mecanico_id,
            cliente_id=cliente_id,
            costo=float(costo) if costo else None,
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

        # Actualizar costo
        costo = request.form.get('costo')
        trabajo.costo = float(costo) if costo else None

        # Si el estado es "Completado", registrar fecha de pago
        if trabajo.estado == 'Completado' and not trabajo.fecha_cancelacion:
            trabajo.fecha_cancelacion = datetime.utcnow()

# Si el estado cambia a otro que no sea "Completado", borrar fecha de pago
        elif trabajo.estado != 'Completado':
            trabajo.fecha_cancelacion = None

        # Subir nueva foto si se cargó
        foto_file = request.files.get('foto')
        if foto_file and foto_file.filename != '':
            trabajo.foto = save_uploaded_file(foto_file)

        db.session.commit()
        flash("Trabajo actualizado correctamente.", "success")
        return redirect(url_for('admin.listar_trabajos'))

    mecanicos = Usuario.query.filter_by(rol='mecanico').all()
    clientes = Usuario.query.filter_by(rol='usuario').all()

    return render_template(
        'admin/trabajos/editar_trabajo.html',
        trabajo=trabajo,
        mecanicos=mecanicos,
        clientes=clientes
    )
    
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


@admin_bp.route("/trabajos/<int:id>/pagado", methods=["POST"])
@login_required
def marcar_pagado(id):
    try:
        trabajo = Trabajo.query.get_or_404(id)

        if trabajo.estado == "Pagado":
            flash("⚠️ Este trabajo ya estaba marcado como pagado.", "warning")
            return redirect(url_for("admin.listar_trabajos"))

        trabajo.estado = "Pagado"
        trabajo.fecha_cancelacion = datetime.utcnow()

        venta = Venta(
            cliente_id=trabajo.cliente_id,
            vendedor_id=current_user.id,
            total=trabajo.costo,
            trabajo_id=trabajo.id
        )
        db.session.add(venta)
        db.session.flush()

        detalle = DetalleVenta(
            cantidad=1,
            precio_unitario=trabajo.costo,
            subtotal=trabajo.costo,
            descripcion=f"Servicio: {trabajo.descripcion}",
            producto_id=None,
            venta=venta
        )
        db.session.add(detalle)
        db.session.commit()

        flash("✅ Trabajo marcado como pagado y registrado en ventas.", "success")
        return redirect(url_for("admin.listar_trabajos"))

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al marcar trabajo como pagado: {str(e)}", "danger")
        return redirect(url_for("admin.listar_trabajos"))

# ------------------
# DASHBOARD MECÁNICO
# ------------------
@mecanico_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.rol != 'mecanico':
        abort(403)

    
    trabajos = Trabajo.query.filter_by(mecanico_id=current_user.id).all()

    
    return render_template(
        'mecanico/dashboard_mecanico.html',
        usuario=current_user,
        trabajos=trabajos
    )

@mecanico_bp.route('/trabajos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_trabajo():
    if current_user.rol != 'mecanico':
        abort(403)

    if request.method == 'POST':
        descripcion = request.form['descripcion']
        cliente_id = request.form['cliente_id']
        costo = request.form.get('costo')  # Nuevo campo
        foto_file = request.files.get('foto')

        nombre_foto = save_uploaded_file(foto_file)

        nuevo_trabajo = Trabajo(
            descripcion=descripcion,
            estado='pendiente',
            foto=nombre_foto,
            mecanico_id=current_user.id,
            cliente_id=cliente_id,
            costo=float(costo),
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

    q = request.args.get('q', '').strip()
    categoria_id = request.args.get('categoria', '').strip()

    # Consulta base
    productos_query = Producto.query

    # Filtrar por texto en nombre o descripción
    if q:
        productos_query = productos_query.filter(
            (Producto.nombre.ilike(f"%{q}%")) |
            (Producto.descripcion.ilike(f"%{q}%"))
        )

    # Filtrar por categoría si está seleccionada
    if categoria_id:
        productos_query = productos_query.filter(Producto.categoria == categoria_id)

    productos = productos_query.all()

    # Obtener categorías únicas de los productos
    categorias = db.session.query(Producto.categoria).distinct().all()
    categorias = [c[0] for c in categorias if c[0]]

    trabajos = Trabajo.query.filter_by(cliente_id=current_user.id).all()

    return render_template(
        'usuario/dashboard_usuario.html',
        usuario=current_user,
        trabajos=trabajos,
        productos=productos,
        categorias=categorias
    )


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


@usuario_bp.route('/ver_trabajos')
@login_required
def ver_trabajos():
    if current_user.rol != 'usuario':
        abort(403)

    trabajos = Trabajo.query.filter_by(cliente_id=current_user.id).all()
    return render_template('usuario/trabajos.html', trabajos=trabajos, usuario=current_user)
#-------------------
# PAGO CON STRIPE
#-------------------
stripe.api_key = Config.STRIPE_SECRET_KEY
@usuario_bp.route('/pagar', methods=['POST'])
@login_required
def pagar():
    carrito = session.get('carrito', [])
    if not carrito:
        flash("El carrito está vacío", "warning")
        return redirect(url_for('usuario.ver_carrito'))

    # Construir la lista de productos en Stripe
    line_items = []
    for item in carrito:
        line_items.append({
            "price_data": {
                "currency": "cop",
                "product_data": {
                    "name": item['nombre'],
                },
                "unit_amount": int(float(item['precio']) * 100),  # en centavos
            },
            "quantity": item['cantidad'],
        })

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            success_url=url_for('usuario.compra_exitosa', _external=True),
            cancel_url=url_for('usuario.ver_carrito', _external=True),
        )
        return redirect(checkout_session.url, code=303)

    except Exception as e:
        flash(f"Error al generar el pago: {str(e)}", "danger")
        return redirect(url_for('usuario.ver_carrito'))
@usuario_bp.route('/compra_exitosa')
@login_required
def compra_exitosa():
    session.pop('carrito', None)
    flash("¡Compra realizada con éxito vía Stripe!", "success")
    return redirect(url_for('usuario.dashboard'))

# ------------------
# inventarios
# ------------------
@admin_bp.route('/inventario')
@login_required
def inventario():
    if current_user.rol != 'admin':
        abort(403)
    productos = Producto.query.all()
    return render_template('admin/inventario/inventario.html', productos=productos)


# ============================
# Registrar nueva venta
# ============================
@admin_bp.route("/ventas/nueva", methods=["POST"])
def nueva_venta():
    try:
        cliente_id = request.form.get("cliente_id")
        vendedor_id = request.form.get("vendedor_id")

        # Crear la venta
        venta = Venta(cliente_id=cliente_id, vendedor_id=vendedor_id, total=0)
        db.session.add(venta)
        db.session.flush()  # para tener venta.id antes de guardar detalles

        total = 0
        productos = request.form.to_dict(flat=False)

        # Recorremos los productos dinámicos del formulario
        index = 0
        while f"productos[{index}][id]" in request.form:
            prod_id = request.form.get(f"productos[{index}][id]")
            cantidad = int(request.form.get(f"productos[{index}][cantidad]", 1))
            precio_unitario = float(request.form.get(f"productos[{index}][precio_unitario]", 0))

            subtotal = cantidad * precio_unitario
            total += subtotal

            if prod_id and prod_id != "":  
                # 👇 Es un producto real
                detalle = DetalleVenta(
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    subtotal=subtotal,
                    producto_id=int(prod_id),
                    venta=venta
                )
            else:
                # 👇 Es un servicio, viene con descripción
                descripcion = request.form.get(f"productos[{index}][descripcion]", "Servicio")
                detalle = DetalleVenta(
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    subtotal=subtotal,
                    descripcion=descripcion,
                    producto_id=None,
                    venta=venta
                )

            db.session.add(detalle)
            index += 1

        # Actualizamos el total
        venta.total = total
        db.session.commit()

        flash("✅ Venta registrada correctamente", "success")
        return redirect(url_for("admin.ventas"))

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al registrar la venta: {str(e)}", "danger")
        return redirect(url_for("admin.ventas"))
# ============================
# Listar y filtrar ventas
# ============================
from datetime import datetime, date, timedelta

@admin_bp.route('/ventas')
@login_required
def ventas():
    if current_user.rol != 'admin':
        abort(403)

    # ==================== FILTRO BASE: SOLO HOY ====================
    hoy = date.today()
    inicio_hoy = datetime.combine(hoy, datetime.min.time())
    fin_hoy = datetime.combine(hoy, datetime.max.time())

    query = Venta.query.join(Usuario, Venta.cliente).filter(
        Venta.fecha >= inicio_hoy,
        Venta.fecha <= fin_hoy
    )

    gasto_query = Gasto.query.filter(
        Gasto.fecha >= inicio_hoy,
        Gasto.fecha <= fin_hoy
    )

    # ====== FILTRO POR USUARIO ======
    usuario = request.args.get("usuario", "").strip()
    if usuario:
        query = query.filter(
            (Usuario.nombre.ilike(f"%{usuario}%")) | 
            (Usuario.correo.ilike(f"%{usuario}%"))
        )

    # ====== FILTRO POR FECHAS ======
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")

    if fecha_inicio:
        try:
            inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            query = query.filter(Venta.fecha >= inicio)
            gasto_query = gasto_query.filter(Gasto.fecha >= inicio)
        except ValueError:
            pass

    if fecha_fin:
        try:
            fin = datetime.strptime(fecha_fin, "%Y-%m-%d")
            fin = fin + timedelta(days=1) - timedelta(seconds=1)  
            query = query.filter(Venta.fecha <= fin)
            gasto_query = gasto_query.filter(Gasto.fecha <= fin)
        except ValueError:
            pass

    # ==================== EJECUTAR CONSULTAS ====================
    ventas = query.order_by(Venta.fecha.desc()).all()
    gastos = gasto_query.order_by(Gasto.fecha.desc()).all()

    total_ventas = sum(venta.total for venta in ventas)
    total_gastos = sum(gasto.monto for gasto in gastos)

    clientes = Usuario.query.filter_by(rol="usuario").all()
    vendedores = Usuario.query.filter_by(rol="admin").all()
    productos = Producto.query.all()

    return render_template(
        "admin/ventas/ingresos.html",
        ventas=ventas,
        clientes=clientes,
        vendedores=vendedores,
        productos=productos,
        total_ventas=total_ventas,
        gastos=gastos,
        total_gastos=total_gastos
    )


# ============================
# Editar venta
# ============================
@admin_bp.route('/ventas/<int:venta_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_venta(venta_id):
    if current_user.rol != "admin":
        abort(403)

    venta = Venta.query.get_or_404(venta_id)

    if request.method == 'POST':
        # Actualizar cliente y vendedor
        cliente_id = request.form.get("cliente_id")
        vendedor_id = request.form.get("vendedor_id")

        venta.cliente_id = cliente_id
        venta.vendedor_id = vendedor_id

        # Eliminar detalles antiguos
        for detalle in venta.detalles:
            # devolver stock antes de borrar
            detalle.producto.stock += detalle.cantidad
            db.session.delete(detalle)

        db.session.flush()  # asegura que se borren antes de recrear

        # Crear nuevos detalles
        total = 0.0
        index = 0
        while True:
            producto_id = request.form.get(f"productos[{index}][id]")
            cantidad = request.form.get(f"productos[{index}][cantidad]")
            precio_unitario = request.form.get(f"productos[{index}][precio_unitario]")
            if not producto_id:
                break

            producto = Producto.query.get(producto_id)
            cantidad = int(cantidad)
            precio_unitario = float(precio_unitario)
            subtotal = cantidad * precio_unitario
            total += subtotal

            detalle = DetalleVenta(
                venta=venta,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                subtotal=subtotal
            )
            db.session.add(detalle)

            # Actualizar stock
            producto.stock -= cantidad
            if producto.stock < 0:
                producto.stock = 0

            index += 1

        venta.total = total
        db.session.commit()
        flash("Venta actualizada correctamente ✅", "success")
        return redirect(url_for("admin.ventas"))

    clientes = Usuario.query.filter_by(rol="usuario").all()
    vendedores = Usuario.query.filter_by(rol="admin").all()
    productos = Producto.query.all()

    return render_template(
        "admin/ventas/editar.html",
        venta=venta,
        clientes=clientes,
        vendedores=vendedores,
        productos=productos
    )


# ============================
# Eliminar venta
# ============================
@admin_bp.route('/ventas/<int:venta_id>/eliminar', methods=['POST'])
@login_required
def eliminar_venta(venta_id):
    if current_user.rol != "admin":
        abort(403)

    venta = Venta.query.get_or_404(venta_id)

    # Devolver stock
    for detalle in venta.detalles:
        detalle.producto.stock += detalle.cantidad

    db.session.delete(venta)
    db.session.commit()
    flash("Venta eliminada correctamente 🗑️", "success")
    return redirect(url_for("admin.ventas"))

# ============================
# Agregar gasto
# ============================
@admin_bp.route("/nuevo_gasto", methods=["POST"])
def nuevo_gasto():
    try:
        descripcion = request.form["descripcion"]
        monto = float(request.form["monto"])
        categoria = request.form["categoria"]
        fecha = datetime.strptime(request.form["fecha"], "%Y-%m-%d").date()

        nuevo = Gasto(
            descripcion=descripcion,
            monto=monto,
            categoria=categoria,
            fecha=fecha
        )
        db.session.add(nuevo)
        db.session.commit()

        flash("✅ Gasto registrado exitosamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al registrar gasto: {str(e)}", "danger")

    return redirect(url_for("admin.ventas")) 
# ============================
# Editar gasto
# ============================
@admin_bp.route('/gastos/<int:gasto_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_gasto(gasto_id):
    if current_user.rol != "admin":
        abort(403)

    gasto = Gasto.query.get_or_404(gasto_id)

    if request.method == 'POST':
        gasto.descripcion = request.form.get("descripcion")
        gasto.monto = float(request.form.get("monto"))
        gasto.categoria = request.form.get("categoria")
        gasto.fecha = datetime.strptime(request.form.get("fecha"), "%Y-%m-%d").date()
        
        db.session.commit()
        flash("Gasto actualizado correctamente ✅", "success")
        return redirect(url_for("admin.ventas"))

    return render_template("admin/ventas/editar_gasto.html", gasto=gasto)

# ============================
# Eliminar gasto
# ============================
@admin_bp.route('/gastos/<int:gasto_id>/eliminar', methods=['POST'])
@login_required
def eliminar_gasto(gasto_id):
    if current_user.rol != "admin":
        abort(403)

    gasto = Gasto.query.get_or_404(gasto_id)
    db.session.delete(gasto)
    db.session.commit()
    flash("Gasto eliminado correctamente 🗑️", "success")
    return redirect(url_for("admin.ventas"))

# ============================
# configuración usuario
# ============================
@usuario_bp.route('/configuracion', methods=['GET', 'POST'])
@login_required
def configuracion():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        contraseña = request.form.get('contraseña')
        imagen = request.files.get('imagen')

        # Actualizar nombre
        if nombre and nombre.strip():
            current_user.nombre = nombre.strip()

        # Actualizar contraseña (si el usuario ingresó una nueva)
        if contraseña and len(contraseña) >= 8:
            current_user.contraseña = bcrypt.generate_password_hash(contraseña)

        # Subir imagen de perfil
        if imagen and imagen.filename != "":
            filename = secure_filename(imagen.filename)
            upload_path = os.path.join(current_app.root_path, 'static/uploads', filename)
            imagen.save(upload_path)
            current_user.imagen = filename

        db.session.commit()
        flash("Tu información ha sido actualizada correctamente ✅", "success")
        return redirect(url_for('usuario.configuracion'))

    return render_template('usuario/usuario.html')

@admin_bp.route('/configuracion', methods=['GET', 'POST'])
@login_required
def configuracion():
    if current_user.rol != 'admin':
        abort(403)

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        contraseña = request.form.get('contraseña')
        imagen = request.files.get('imagen')

        # Actualizar nombre
        if nombre and nombre.strip():
            current_user.nombre = nombre.strip()

        # Actualizar contraseña (si el usuario ingresó una nueva)
        if contraseña and len(contraseña) >= 8:
            current_user.contraseña = bcrypt.generate_password_hash(contraseña)

        # Subir imagen de perfil
        if imagen and imagen.filename != "":
            filename = secure_filename(imagen.filename)
            upload_path = os.path.join(current_app.root_path, 'static/uploads', filename)
            imagen.save(upload_path)
            current_user.imagen = filename

        db.session.commit()
        flash("Tu información ha sido actualizada correctamente ✅", "success")
        return redirect(url_for('admin.configuracion'))

    return render_template('admin/configuracion.html', usuario=current_user)

@mecanico_bp.route('/configuracion', methods=['GET', 'POST'])
@login_required
def configuracion():
    if current_user.rol != 'mecanico':
        abort(403)

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        contraseña = request.form.get('contraseña')
        imagen = request.files.get('imagen')

        # Actualizar nombre
        if nombre and nombre.strip():
            current_user.nombre = nombre.strip()

        # Actualizar contraseña (si el usuario ingresó una nueva)
        if contraseña and len(contraseña) >= 8:
            current_user.contraseña = bcrypt.generate_password_hash(contraseña)

        # Subir imagen de perfil
        if imagen and imagen.filename != "":
            filename = secure_filename(imagen.filename)
            upload_path = os.path.join(current_app.root_path, 'static/uploads', filename)
            imagen.save(upload_path)
            current_user.imagen = filename

        db.session.commit()
        flash("Tu información ha sido actualizada correctamente ✅", "success")
        return redirect(url_for('mecanico.configuracion'))

    return render_template('mecanico/configuracion.html', usuario=current_user)