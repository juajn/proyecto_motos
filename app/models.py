from extensions import db
from flask_login import UserMixin
from datetime import datetime

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    contraseña = db.Column(db.Text, nullable=False)
    rol = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    imagen = db.Column(db.String(200))

class Producto(db.Model):
    __tablename__ = "producto"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=True)
    foto = db.Column(db.String(200), nullable=True)
    categoria = db.Column(db.String(100), nullable=True)
    destacado = db.Column(db.Boolean, default=False)  # Nuevo campo para productos destacados

    # Relación inversa
    detalles = db.relationship("DetalleVenta", back_populates="producto")

from enum import Enum

class EstadoTrabajo(str, Enum):
    PENDIENTE = "Pendiente"
    EN_PROCESO = "En proceso"
    COMPLETADO = "Completado"
    PAGADO = "Pagado"

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
    detalles = db.relationship("DetalleVenta", back_populates="venta", lazy=True)
    # 👇 Aquí va el cascade
    detalles = db.relationship(
        'DetalleVenta',
        back_populates='venta',
        cascade="all, delete-orphan",
        single_parent=True
    )


class DetalleVenta(db.Model):
    __tablename__ = "detalle_venta"

    id = db.Column(db.Integer, primary_key=True)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    descripcion = db.Column(db.String(255), nullable=True)

    venta_id = db.Column(db.Integer, db.ForeignKey("venta.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("producto.id"), nullable=True)  # 👈 permite NULL

    venta = db.relationship("Venta", back_populates="detalles")
    producto = db.relationship("Producto", back_populates="detalles")

class Gasto(db.Model):
    __tablename__ = "gastos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    descripcion = db.Column(db.Text, nullable=False)
    monto = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)   
