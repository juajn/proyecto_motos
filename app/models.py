from extensions import db
from flask_login import UserMixin
from datetime import datetime

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    contraseña = db.Column(db.String(120), nullable=False)
    rol = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    imagen = db.Column(db.String(200))

    

class Producto(db.Model):
    __tablename__ = 'producto'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    foto = db.Column(db.String(200))
    stock = db.Column(db.Integer, nullable=False, default=0)
    categoria = db.Column(db.String(100),nullable=False)

class Trabajo(db.Model):
    __tablename__ = 'trabajo'

    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(255), nullable=False)
    estado = db.Column(db.String(50), nullable=False)
    foto = db.Column(db.String(255))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    costo= db.Column(db.Float, nullable=True)
    fecha_cancelacion = db.Column(db.DateTime, nullable=True)    
    
    
    mecanico_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

    mecanico = db.relationship('Usuario', foreign_keys=[mecanico_id], backref='trabajos_como_mecanico')
    cliente = db.relationship('Usuario', foreign_keys=[cliente_id], backref='trabajos_como_cliente')

class Venta(db.Model):
    __tablename__ = 'venta'

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    total = db.Column(db.Float, nullable=False, default=0.0)

    cliente_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    cliente = db.relationship('Usuario', foreign_keys=[cliente_id], backref='compras')

    vendedor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    vendedor = db.relationship('Usuario', foreign_keys=[vendedor_id], backref='ventas_registradas')

    trabajo_id = db.Column(db.Integer, db.ForeignKey('trabajo.id'), nullable=True)
    trabajo = db.relationship('Trabajo', backref='venta_asociada', uselist=False)

    # 👇 Aquí va el cascade
    detalles = db.relationship(
        'DetalleVenta',
        back_populates='venta',
        cascade="all, delete-orphan",
        single_parent=True
    )


class DetalleVenta(db.Model):
    __tablename__ = 'detalle_venta'

    id = db.Column(db.Integer, primary_key=True)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    venta_id = db.Column(db.Integer, db.ForeignKey('venta.id'), nullable=False)
    venta = db.relationship('Venta', back_populates='detalles')

    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    producto = db.relationship('Producto', backref='detalles_vendidos')
