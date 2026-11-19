from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Docente(db.Model):
    __tablename__ = 'docente'
    id = db.Column(db.Integer, primary_key=True)
    dni = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    condicion = db.Column(db.String(50))         # DN, DC, etc.
    categoria = db.Column(db.String(50))         # ATC--, PDE--, UTP20...
    facultad = db.Column(db.String(150), nullable=False)
    area = db.Column(db.String(50))              # Se completa automáticamente desde la facultad
    correo = db.Column(db.String(100), unique=True)
    nota_desempeno = db.Column(db.Float, default=0.0) # Puntaje del 1er reporte (0 a 100)
    nota_cuestionario = db.Column(db.Float, default=0.0) # Puntaje del 2do reporte (PF)

    proyectos = db.relationship('Proyecto', backref='autor', lazy=True,
                                cascade='all, delete-orphan')


class Proyecto(db.Model):
    __tablename__ = 'proyecto'
    id = db.Column(db.Integer, primary_key=True)
    nombre_bp = db.Column(db.String(250), nullable=False)
    contexto = db.Column(db.Text)
    proposito = db.Column(db.Text)
    descripcion = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(500), nullable=True)
    recursos = db.Column(db.Text)
    resultados = db.Column(db.Text)
    evidencias = db.Column(db.Text)
    
    # Datos que se autocompletan o se llenan en el form
    area = db.Column(db.String(50))
    facultad = db.Column(db.String(150))
    programa_estudio = db.Column(db.String(150))
    asignatura = db.Column(db.String(200))
    ciclo = db.Column(db.String(20))
    condicion = db.Column(db.String(50))
    correo_institucional = db.Column(db.String(100))
    
    dia = db.Column(db.Integer, default=1)
    hora = db.Column(db.String(10))
    duracion = db.Column(db.Integer, default=15)
    
    docente_id = db.Column(db.Integer, db.ForeignKey('docente.id'), nullable=False)
    calificaciones = db.relationship('Calificacion', backref='proyecto',
                                     lazy=True, cascade='all, delete-orphan')


class Jurado(db.Model):
    __tablename__ = 'jurado'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    dni = db.Column(db.String(20))
    dia_asignado = db.Column(db.Integer)  # 1 o 2
    calificaciones = db.relationship('Calificacion', backref='jurado', lazy=True)


class Criterio(db.Model):
    __tablename__ = 'criterio'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    peso = db.Column(db.Float, default=1.0)
    orden = db.Column(db.Integer, default=0)
    niveles = db.relationship('NivelCriterio', backref='criterio',
                              lazy=True, cascade='all, delete-orphan')


class NivelCriterio(db.Model):
    __tablename__ = 'nivel_criterio'
    id = db.Column(db.Integer, primary_key=True)
    criterio_id = db.Column(db.Integer, db.ForeignKey('criterio.id'), nullable=False)
    etiqueta = db.Column(db.String(50))
    puntaje = db.Column(db.Float)
    descripcion = db.Column(db.Text)


class Calificacion(db.Model):
    __tablename__ = 'calificacion'
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)
    jurado_id = db.Column(db.Integer, db.ForeignKey('jurado.id'), nullable=False)
    nota_final = db.Column(db.Float)
    comentario = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    detalles = db.relationship('DetalleCalificacion', backref='calificacion',
                               lazy=True, cascade='all, delete-orphan')


class DetalleCalificacion(db.Model):
    __tablename__ = 'detalle_calificacion'
    id = db.Column(db.Integer, primary_key=True)
    calificacion_id = db.Column(db.Integer, db.ForeignKey('calificacion.id'), nullable=False)
    criterio_id = db.Column(db.Integer, db.ForeignKey('criterio.id'), nullable=False)
    nivel_id = db.Column(db.Integer, db.ForeignKey('nivel_criterio.id'), nullable=False)
    puntaje_obtenido = db.Column(db.Float)
