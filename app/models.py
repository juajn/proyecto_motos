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
    
    # Relación con trabajos como cliente
    trabajos = db.relationship(
        'Trabajo', 
        foreign_keys='Trabajo.cliente_id', 
        backref='cliente', 
        lazy=True
    )
    
    # Relación con trabajos como mecánico
    trabajos_asignados = db.relationship(
        'Trabajo', 
        foreign_keys='Trabajo.mecanico_id', 
        backref='mecanico', 
        lazy=True
    )

class Producto(db.Model):
    __tablename__ = 'producto'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    foto = db.Column(db.String(200))
    stock = db.Column(db.Integer, nullable=False, default=0)

class Trabajo(db.Model):
    __tablename__ = 'trabajo'
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(50), nullable=False, default='pendiente')  # Columna añadida
    foto = db.Column(db.String(200))
    cliente_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    mecanico_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)