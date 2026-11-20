import os
import io
from flask import request, send_file
from openpyxl import Workbook
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from flask import (Flask, render_template, request, redirect,
                   url_for, flash, abort)
from catalogos import (FACULTADES, lista_areas, lista_facultades,
                       lista_programas, area_desde_facultad,
                       facultad_desde_codigo)
from models import (db, Docente, Proyecto, Jurado, Criterio, 
                    NivelCriterio, Calificacion, DetalleCalificacion, NotaPeriodo)
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-uncp-2026')

database_url = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
def calcular_promedio_final(proyecto):
    # 1. Nota de jurados (sobre 28) a porcentaje
    cals = Calificacion.query.filter_by(proyecto_id=proyecto.id).all()
    if cals:
        suma_notas = sum(c.nota_final for c in cals)
        prom_jurados = suma_notas / len(cals)
        porcentaje_jurados = (prom_jurados / 28) * 100
    else:
        prom_jurados = 0
        porcentaje_jurados = 0

    # 2. Notas de desempeño y cuestionario desde el HISTORIAL (NotaPeriodo)
    doc = proyecto.autor
    nota_des = 0
    nota_cue = 0
    
    if doc:
        # Buscar todas las notas de Desempeño del docente y promediarlas
        notas_des_obj = NotaPeriodo.query.filter_by(docente_id=doc.id, tipo='desempeno').all()
        if notas_des_obj:
            nota_des = sum(n.nota for n in notas_des_obj) / len(notas_des_obj)
            
        # Buscar todas las notas de Cuestionario del docente y promediarlas
        notas_cue_obj = NotaPeriodo.query.filter_by(docente_id=doc.id, tipo='cuestionario').all()
        if notas_cue_obj:
            nota_cue = sum(n.nota for n in notas_cue_obj) / len(notas_cue_obj)

    # 3. Promedio final (40% Jurados, 30% Desempeño, 30% Cuestionario)
    prom_final = (porcentaje_jurados * 0.40) + (nota_des * 0.30) + (nota_cue * 0.30)

    # 4. Determinar Nivel (Según tu imagen)
    nivel = "Deficiente"
    if prom_final >= 81:
        nivel = "Bueno"
    elif prom_final >= 61:
        nivel = "Regular"
    elif prom_final >= 41:
        nivel = "Bajo"

    return {
        'prom_jurados': round(prom_jurados, 2),
        'porcentaje_jurados': round(porcentaje_jurados, 2),
        'nota_des': round(nota_des, 2),
        'nota_cue': round(nota_cue, 2),
        'prom_final': round(prom_final, 2),
        'nivel': nivel
    }
@app.context_processor
def inject_helpers():
    from catalogos import area_desde_facultad, lista_areas
    return {
        'area_desde_facultad': area_desde_facultad,
        'lista_areas': lista_areas,
        'facultades': FACULTADES, 
    }

# ============ HOME ============
@app.route('/')
def index():
    stats = {
        'docentes': Docente.query.count(),
        'proyectos': Proyecto.query.count(),
        'jurados': Jurado.query.count(),
        'calificaciones': Calificacion.query.count()
    }
    return render_template('index.html', stats=stats)


# ============ DOCENTES (CRUD) ============
@app.route('/docentes')
def lista_docentes():
    docentes = Docente.query.order_by(Docente.facultad, Docente.nombre).all()
    return render_template('docentes/lista.html', docentes=docentes)


@app.route('/docentes/nuevo', methods=['GET', 'POST'])
@app.route('/docentes/<int:id>/editar', methods=['GET', 'POST'])
@app.route('/docentes/nuevo', methods=['GET', 'POST'])
@app.route('/docentes/<int:id>/editar', methods=['GET', 'POST'])
def form_docente(id=None):
    docente = Docente.query.get_or_404(id) if id else None

    # Facultades únicas
    facultades_unicas = []
    vistas = set()
    for f in FACULTADES:
        if f["nombre"] not in vistas:
            vistas.add(f["nombre"])
            facultades_unicas.append(f["nombre"])

    if request.method == 'POST':
        if not docente:
            docente = Docente()
            db.session.add(docente)
        docente.dni = request.form['dni']
        docente.nombre = request.form['nombre']
        docente.condicion = request.form.get('condicion')
        docente.categoria = request.form.get('categoria')
        docente.facultad = request.form['facultad']
        docente.area = area_desde_facultad(docente.facultad)  # SIEMPRE AUTOMÁTICO
        docente.correo = request.form.get('correo') or None

        if not id:
            existente = Docente.query.filter_by(dni=docente.dni).first()
            if existente:
                flash(f'Ya existe un docente con DNI {docente.dni}.', 'danger')
                return render_template('docentes/form.html',
                                       docente=None,
                                       facultades=facultades_unicas)

        db.session.commit()
        flash('Docente guardado correctamente', 'success')
        return redirect(url_for('lista_docentes'))

    return render_template('docentes/form.html',
                           docente=docente,
                           facultades=facultades_unicas)


@app.route('/docentes/<int:id>/eliminar', methods=['POST'])
def eliminar_docente(id):
    docente = Docente.query.get_or_404(id)
    db.session.delete(docente)
    db.session.commit()
    flash('Docente eliminado', 'info')
    return redirect(url_for('lista_docentes'))


# ============ PROYECTOS (CRUD) ============
@app.route('/proyectos')
def lista_proyectos():
    # Leer el parámetro de filtro por día (si existe)
    dia_filtro = request.args.get('dia', type=int)
    
    query = Proyecto.query
    if dia_filtro:
        query = query.filter_by(dia=dia_filtro)
        
    proyectos = query.order_by(Proyecto.area, Proyecto.nombre_bp).all()
    
    return render_template('proyectos/lista.html', proyectos=proyectos)


@app.route('/proyectos/nuevo', methods=['GET', 'POST'])
@app.route('/proyectos/<int:id>/editar', methods=['GET', 'POST'])
def form_proyecto(id=None):
    proyecto = Proyecto.query.get_or_404(id) if id else None
    docentes = Docente.query.order_by(Docente.nombre).all()

    if request.method == 'POST':
        if not proyecto:
            proyecto = Proyecto()
            db.session.add(proyecto)
        
        proyecto.nombre_bp = request.form['nombre_bp']
        
        # Los campos de descripción se guardan según lo que se haya enviado
        proyecto.contexto = request.form.get('contexto')
        proyecto.proposito = request.form.get('proposito')
        proyecto.descripcion = request.form.get('descripcion')
        proyecto.link = request.form.get('link')
        proyecto.recursos = request.form.get('recursos')
        proyecto.resultados = request.form.get('resultados')
        proyecto.evidencias = request.form.get('evidencias')
        
        # Datos del docente y del proyecto
        proyecto.docente_id = int(request.form['docente_id'])
        docente = Docente.query.get(proyecto.docente_id)
        
        # Autocompletados
        proyecto.area = docente.area if docente else None
        proyecto.facultad = docente.facultad if docente else None
        proyecto.condicion = docente.condicion if docente else None
        
        # Manuales y correo
        proyecto.programa_estudio = request.form.get('programa_estudio')
        proyecto.asignatura = request.form.get('asignatura')
        proyecto.ciclo = request.form.get('ciclo')
        
        # Actualizar correo si se cambió
        correo = request.form.get('correo_institucional')
        if correo:
            proyecto.correo_institucional = correo
            if docente:
                docente.correo = correo # Actualiza también al docente
        
        db.session.commit()
        flash('Proyecto guardado correctamente', 'success')
        return redirect(url_for('lista_proyectos'))

    # Pasar los docentes convertidos a diccionario para el JS
    docentes_json = [{
        'id': d.id,
        'nombre': d.nombre,
        'area': d.area or '',
        'facultad': d.facultad or '',
        'condicion': d.condicion or '',
        'correo': d.correo or ''
    } for d in docentes]

    return render_template('proyectos/form.html', 
                           proyecto=proyecto, 
                           docentes=docentes, 
                           docentes_json=docentes_json)

@app.route('/proyectos/<int:id>')
def detalle_proyecto(id):
    proyecto = Proyecto.query.get_or_404(id)
    return render_template('proyectos/detalle.html', proyecto=proyecto)


@app.route('/proyectos/<int:id>/eliminar', methods=['POST'])
def eliminar_proyecto(id):
    proyecto = Proyecto.query.get_or_404(id)
    db.session.delete(proyecto)
    db.session.commit()
    flash('Proyecto eliminado', 'info')
    return redirect(url_for('lista_proyectos'))

# ============ CRONOGRAMA ============
@app.route('/cronograma')
def cronograma():
    # Ordenar por Área, luego por el nombre del Docente (Alfabético)
    proyectos = Proyecto.query.join(Docente).order_by(
        Proyecto.area, 
        Docente.nombre
    ).all()

    # Agrupar por área
    agrupados = {}
    for p in proyectos:
        area = p.area or 'SIN ÁREA'
        agrupados.setdefault(area, []).append(p)

    # Ordenar las áreas alfabéticamente
    agrupados = dict(sorted(agrupados.items()))

    return render_template('cronograma.html', agrupados=agrupados, total=len(proyectos))


@app.route('/cronograma/asignar', methods=['POST'])
def asignar_cronograma():
    for key, value in request.form.items():
        if key.startswith('dia_'):
            pid = int(key.replace('dia_', ''))
            p = Proyecto.query.get(pid)
            if p:
                p.dia = int(value)
                hora_key = f'hora_{pid}'
                p.hora = request.form.get(hora_key, '')
    db.session.commit()
    flash('Cronograma guardado', 'success')
    return redirect(url_for('cronograma'))


import re

def limpiar_texto_excel(texto):
    """Elimina caracteres de control que openpyxl no acepta (como \x00 a \x1f)"""
    if texto is None:
        return ''
    texto = str(texto)
    # Reemplaza caracteres de control por espacio (excepto \n y \r)
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', texto)

@app.route('/cronograma/excel')
def cronograma_excel():
    """Genera y descarga un Excel con el cronograma ordenado."""
    # Ordenar por Área y luego por nombre del Docente
    proyectos = Proyecto.query.join(Docente).order_by(
        Proyecto.area, 
        Docente.nombre
    ).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Cronograma"

    # Encabezados (Agregamos Facultad aquí)
    headers = ["Área", "Facultad", "Docente", "Nombre del Proyecto", "Día", "Hora"]
    ws.append(headers)

    # Estilos
    fill_header = PatternFill(start_color="1A3D7C", end_color="1A3D7C", fill_type="solid")
    font_header = Font(bold=True, color="FFFFFF")
    fill_area = PatternFill(start_color="E8F0FA", end_color="E8F0FA", fill_type="solid")
    thin = Side(style='thin', color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Aplicar estilos a la cabecera
    for col_idx, cell in enumerate(ws[1], 1):
        cell.fill = fill_header
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border

    # Agrupar y escribir por área
    current_area = None
    for p in proyectos:
        area = p.area or 'SIN ÁREA'
        # Usamos p.facultad, si no existe ponemos un guion
        facultad = p.facultad or '-'
        
        # Agregamos la facultad a la fila (asegurándonos de limpiar caracteres extraños)
        ws.append([
            limpiar_texto_excel(area),
            limpiar_texto_excel(facultad),
            limpiar_texto_excel(p.autor.nombre if p.autor else '-'),
            limpiar_texto_excel(p.nombre_bp),
            limpiar_texto_excel(f"Día {p.dia}" if p.dia else '-'),
            limpiar_texto_excel(p.hora or '-')
        ])

        # Aplicar bordes a la fila
        row_idx = ws.max_row
        for cell in ws[row_idx]:
            cell.border = border
            cell.alignment = Alignment(vertical="center", wrap_text=True)

        # Colorear filas al cambiar de área
        if area != current_area:
            for cell in ws[row_idx]:
                cell.fill = fill_area
            current_area = area

    # Ajustar ancho de columnas (Actualizado para la nueva columna)
    ws.column_dimensions['A'].width = 12  # Área
    ws.column_dimensions['B'].width = 40  # Facultad
    ws.column_dimensions['C'].width = 35  # Docente
    ws.column_dimensions['D'].width = 50  # Nombre del Proyecto
    ws.column_dimensions['E'].width = 10  # Día
    ws.column_dimensions['F'].width = 10  # Hora

    # Congelar la primera fila
    ws.freeze_panes = "A2"

    # Guardar en memoria
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='cronograma_uncp.xlsx'
    )
# ============ JURADOS (CRUD) ============
@app.route('/jurados')
def lista_jurados():
    jurados = Jurado.query.order_by(Jurado.dia_asignado, Jurado.nombre).all()
    return render_template('jurados/lista.html', jurados=jurados)


@app.route('/jurados/nuevo', methods=['GET', 'POST'])
@app.route('/jurados/<int:id>/editar', methods=['GET', 'POST'])
def form_jurado(id=None):
    jurado = Jurado.query.get_or_404(id) if id else None
    if request.method == 'POST':
        if not jurado:
            jurado = Jurado()
            db.session.add(jurado)
        jurado.nombre = request.form['nombre']
        jurado.dni = request.form.get('dni')
        jurado.dia_asignado = int(request.form['dia_asignado'])
        db.session.commit()
        flash('Jurado guardado', 'success')
        return redirect(url_for('lista_jurados'))
    return render_template('jurados/form.html', jurado=jurado)


@app.route('/jurados/<int:id>/eliminar', methods=['POST'])
def eliminar_jurado(id):
    Jurado.query.get_or_404(id)
    db.session.delete(Jurado.query.get(id))
    db.session.commit()
    flash('Jurado eliminado', 'info')
    return redirect(url_for('lista_jurados'))


# ============ CALIFICAR (tablet) ============
@app.route('/calificar/<int:proyecto_id>', methods=['GET', 'POST'])
def calificar(proyecto_id):
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    criterios = Criterio.query.order_by(Criterio.orden).all()
    calificados = Calificacion.query.filter_by(proyecto_id=proyecto_id).all()
    ids_calificados = [c.jurado_id for c in calificados]
    jurados_dia = Jurado.query.filter_by(dia_asignado=proyecto.dia).all()

    if request.method == 'POST':
        jurado_id = int(request.form['jurado_id'])
        
        # Evitar que el mismo jurado califique 2 veces
        existente = Calificacion.query.filter_by(
            proyecto_id=proyecto_id, jurado_id=jurado_id).first()
        if existente:
            flash('Este jurado ya calificó este proyecto', 'warning')
            return redirect(url_for('calificar', proyecto_id=proyecto_id))

        total = 0
        detalles = []
        
        # Recorrer criterios y sumar los puntajes
        for c in criterios:
            nivel_id = request.form.get(f'criterio_{c.id}')
            if not nivel_id:
                flash(f'Falta seleccionar el criterio: {c.nombre}', 'danger')
                return redirect(url_for('calificar', proyecto_id=proyecto_id))
            
            nivel = NivelCriterio.query.get(int(nivel_id))
            total += nivel.puntaje
            detalles.append((c.id, nivel.id, nivel.puntaje))

        # La nota final es la suma directa de los puntos (máximo 28)
        nota_final = total
        
        cal = Calificacion(proyecto_id=proyecto_id, jurado_id=jurado_id,
                           nota_final=nota_final,
                           comentario=request.form.get('comentario', ''))
        db.session.add(cal)
        db.session.flush()
        
        for cid, nid, punt in detalles:
            db.session.add(DetalleCalificacion(calificacion_id=cal.id,
                                               criterio_id=cid, nivel_id=nid,
                                               puntaje_obtenido=punt))
        db.session.commit()
        
        flash(f'Calificación guardada. Puntaje total: {nota_final} / 28 pts', 'success')
        return redirect(url_for('calificar', proyecto_id=proyecto_id))

    return render_template('calificar.html',
                           proyecto=proyecto,
                           criterios=criterios,
                           jurados=jurados_dia,
                           calificados=calificados,
                           ids_calificados=ids_calificados)



# ============ PORTAL DE JURADOS ============
@app.route('/jurado')
def portal_jurado():
    """Pantalla inicial para que el jurado elija su nombre."""
    jurados_d1 = Jurado.query.filter_by(dia_asignado=1).all()
    jurados_d2 = Jurado.query.filter_by(dia_asignado=2).all()
    return render_template('jurado_portal.html', jurados_d1=jurados_d1, jurados_d2=jurados_d2)


@app.route('/jurado/<int:jurado_id>')
def jurado_proyectos(jurado_id):
    """Lista de proyectos para un jurado específico."""
    jurado = Jurado.query.get_or_404(jurado_id)
    # Trae los proyectos del día del jurado, ordenados por área y hora
    proyectos = Proyecto.query.filter_by(dia=jurado.dia_asignado)\
                              .order_by(Proyecto.area, Proyecto.hora).all()
    
    # Ver qué proyectos ya calificó este jurado
    calificados_ids = [c.proyecto_id for c in Calificacion.query.filter_by(jurado_id=jurado_id).all()]
    
    return render_template('jurado_proyectos.html', jurado=jurado, proyectos=proyectos, calificados_ids=calificados_ids)


# ============ CALIFICAR Y EDITAR ============
@app.route('/calificar/<int:proyecto_id>/jurado/<int:jurado_id>', methods=['GET', 'POST'])
def calificar_jurado(proyecto_id, jurado_id):
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    jurado = Jurado.query.get_or_404(jurado_id)
    criterios = Criterio.query.order_by(Criterio.orden).all()
    
    calificacion_existente = Calificacion.query.filter_by(proyecto_id=proyecto_id, jurado_id=jurado_id).first()

    if request.method == 'POST':
        # Verificar si se marcó la opción "No se presentó"
        no_se_presento = request.form.get('no_se_presento')
        
        if no_se_presento:
            total = 0
            detalles = []
            # No procesamos los criterios, la nota final es 0
        else:
            total = 0
            detalles = []
            for c in criterios:
                nivel_id = request.form.get(f'criterio_{c.id}')
                if not nivel_id:
                    flash(f'Falta seleccionar el criterio: {c.nombre}', 'danger')
                    return redirect(url_for('calificar_jurado', proyecto_id=proyecto_id, jurado_id=jurado_id))
                
                nivel = NivelCriterio.query.get(int(nivel_id))
                total += nivel.puntaje
                detalles.append((c.id, nivel.id, nivel.puntaje))

        if calificacion_existente:
            calificacion_existente.nota_final = total
            calificacion_existente.comentario = request.form.get('comentario', '')
            
            # Borrar detalles viejos y crear nuevos (si los hay)
            DetalleCalificacion.query.filter_by(calificacion_id=calificacion_existente.id).delete()
            for cid, nid, punt in detalles:
                db.session.add(DetalleCalificacion(calificacion_id=calificacion_existente.id,
                                                   criterio_id=cid, nivel_id=nid, puntaje_obtenido=punt))
            flash(f'Calificación actualizada. Total: {total} / 28 pts', 'success')
        else:
            cal = Calificacion(proyecto_id=proyecto_id, jurado_id=jurado_id,
                               nota_final=total, comentario=request.form.get('comentario', ''))
            db.session.add(cal)
            db.session.flush()
            for cid, nid, punt in detalles:
                db.session.add(DetalleCalificacion(calificacion_id=cal.id,
                                                   criterio_id=cid, nivel_id=nid, puntaje_obtenido=punt))
            flash(f'Calificación guardada. Total: {total} / 28 pts', 'success')
        
        db.session.commit()
        return redirect(url_for('jurado_proyectos', jurado_id=jurado_id))

    return render_template('calificar.html',
                           proyecto=proyecto,
                           jurado=jurado,
                           criterios=criterios,
                           calificacion=calificacion_existente)
  
# ============ RESULTADOS (Actualizado) ============
@app.route('/resultados')
def resultados():
    data = []
    for p in Proyecto.query.order_by(Proyecto.area, Proyecto.nombre_bp).all():
        calculos = calcular_promedio_final(p)
        data.append({
            'proyecto': p,
            'calificaciones': Calificacion.query.filter_by(proyecto_id=p.id).all(),
            'calculos': calculos,
            'completo': len(Calificacion.query.filter_by(proyecto_id=p.id).all()) == 4
        })
    
    # Ordenar por el promedio final de mayor a menor
    data.sort(key=lambda x: x['calculos']['prom_final'], reverse=True)
    return render_template('resultados.html', data=data)

@app.route('/resultados/excel')
def resultados_excel():
    proyectos = Proyecto.query.order_by(Proyecto.area, Proyecto.nombre_bp).all()
    todos_jurados = Jurado.query.order_by(Jurado.dia_asignado, Jurado.nombre).all()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Resultados Consolidados"

    # Encabezados
    headers = ["Área", "Facultad", "Docente", "Proyecto", "Programa"]
    for j in todos_jurados:
        nombre_corto = j.nombre.split()[0] if j.nombre else 'Jurado'
        headers.append(f"J_{nombre_corto} (28)")
    
    headers.extend(["Prom. Jurados (%)", "Desempeño (%)", "Cuestionario (%)", "PROMEDIO FINAL (%)", "NIVEL"])
    ws.append(headers)

    # Estilos
    fill_header = PatternFill(start_color="1A3D7C", end_color="1A3D7C", fill_type="solid")
    font_header = Font(bold=True, color="FFFFFF")
    fill_area = PatternFill(start_color="E8F0FA", end_color="E8F0FA", fill_type="solid")
    thin = Side(style='thin', color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for cell in ws[1]:
        cell.fill = fill_header
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border

    current_area = None

    for p in proyectos:
        # Usamos la función que calcula todo
        calcs = calcular_promedio_final(p)
        cals = Calificacion.query.filter_by(proyecto_id=p.id).all()
        notas_por_jurado = {c.jurado_id: c.nota_final for c in cals}
        
        row = [
            limpiar_texto_excel(p.area or ''),
            limpiar_texto_excel(p.facultad or ''),
            limpiar_texto_excel(p.autor.nombre if p.autor else '-'),
            limpiar_texto_excel(p.nombre_bp),
            limpiar_texto_excel(p.programa_estudio or '')
        ]
        
        # Notas individuales de jurados
        for j in todos_jurados:
            nota = notas_por_jurado.get(j.id)
            row.append(nota if nota is not None else '-')
        
        # Agregar los cálculos
        row.append(calcs['porcentaje_jurados'])
        row.append(calcs['nota_des'])
        row.append(calcs['nota_cue'])
        row.append(calcs['prom_final'])
        row.append(calcs['nivel'])
        
        ws.append(row)
        row_idx = ws.max_row
        
        for cell in ws[row_idx]:
            cell.border = border
            cell.alignment = Alignment(vertical="center", wrap_text=True, horizontal="center" if cell.column > 5 else "left")
        
        if p.area != current_area:
            for cell in ws[row_idx]:
                cell.fill = fill_area
            current_area = p.area

    # Ajustar ancho
    for i in range(1, len(headers) + 1):
        col_letter = ws.cell(row=1, column=i).column_letter
        ws.column_dimensions[col_letter].width = 15

    ws.freeze_panes = "A2"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='resultados_consolidados.xlsx'
    )
  
# ============ IMPORTAR DOCENTES DESDE EXCEL ============
import pandas as pd
from werkzeug.utils import secure_filename


@app.route('/docentes/importar', methods=['GET', 'POST'])
def importar_docentes():
    if request.method == 'POST':
        archivo = request.files.get('archivo')
        if not archivo or archivo.filename == '':
            flash('Debes seleccionar un archivo Excel.', 'danger')
            return redirect(url_for('importar_docentes'))

        if not archivo.filename.lower().endswith(('.xlsx', '.xls')):
            flash('El archivo debe ser .xlsx o .xls', 'danger')
            return redirect(url_for('importar_docentes'))

        try:
            df = pd.read_excel(archivo)
        except Exception as e:
            flash(f'No se pudo leer el archivo: {e}', 'danger')
            return redirect(url_for('importar_docentes'))

        # Verificar columnas requeridas
        requeridas = ['DNI', 'Condición', 'Categoria', 'Facultad', 'Apellidos y Nombres']
        df.columns = [str(c).strip() for c in df.columns]
        faltantes = [c for c in requeridas if c not in df.columns]
        if faltantes:
            flash(f'Faltan columnas en el Excel: {", ".join(faltantes)}', 'danger')
            return redirect(url_for('importar_docentes'))

        creados, actualizados, errores = 0, 0, []
        nombres_validos = [f["nombre"] for f in FACULTADES]

        for idx, fila in df.iterrows():
            try:
                dni = str(fila.get('DNI', '')).strip()
                if not dni or dni.lower() == 'nan':
                    errores.append(f'Fila {idx+2}: DNI vacío, omitida.')
                    continue

                nombre_crudo = str(fila.get('Apellidos y Nombres', '')).strip()
                if not nombre_crudo or nombre_crudo.lower() == 'nan':
                    errores.append(f'Fila {idx+2}: nombre vacío, omitida.')
                    continue

                # Procesar la facultad
                facultad_raw = str(fila.get('Facultad', '')).strip()
                
                # 1. Intentar traducir el código (EN -> Facultad de Enfermería)
                facultad = facultad_desde_codigo(facultad_raw)
                
                # 2. Si no se tradujo, verificar si ya es un nombre completo válido
                if not facultad:
                    if facultad_raw in nombres_validos:
                        facultad = facultad_raw
                    else:
                        errores.append(f'Fila {idx+2}: facultad "{facultad_raw}" no reconocida, omitida.')
                        continue

                # Formato del nombre: "AGUIRRE - ROJAS - ALEJANDRO ANIBAL" -> "AGUIRRE ROJAS, ALEJANDRO ANIBAL"
                partes = [p.strip() for p in nombre_crudo.split(' - ')]
                if len(partes) >= 3:
                    nombre_final = f"{partes[0]} {partes[1]}, {' '.join(partes[2:])}"
                else:
                    nombre_final = nombre_crudo

                def limpiar(v):
                    s = str(v).strip() if v is not None else ''
                    return None if s in ('', '--', 'nan', 'None') else s

                # Buscar si el docente ya existe
                docente = Docente.query.filter_by(dni=dni).first()
                if docente:
                    actualizados += 1
                else:
                    docente = Docente(dni=dni)
                    db.session.add(docente)
                    creados += 1

                docente.nombre = nombre_final
                docente.condicion = limpiar(fila.get('Condición'))
                docente.categoria = limpiar(fila.get('Categoria'))
                docente.facultad = facultad
                docente.area = area_desde_facultad(facultad)  # Automático

            except Exception as e:
                errores.append(f'Fila {idx+2}: {e}')

        db.session.commit()
        flash(f'Importación completa. Nuevos: {creados} · Actualizados: {actualizados}', 'success')
        if errores:
            flash('Errores: ' + ' | '.join(errores[:5]), 'warning')
        return redirect(url_for('lista_docentes'))

    return render_template('docentes/importar.html')

# ============ CATÁLOGOS (API para selects en cascada) ============
from catalogos import (FACULTADES, lista_areas, lista_facultades,
                       lista_programas, area_desde_facultad,
                       facultad_desde_codigo)


@app.route('/api/facultades/<area>')
def api_facultades(area):
    return {'facultades': lista_facultades(area)}


@app.route('/api/programas/<area>/<path:facultad>')
def api_programas(area, facultad):
    return {'programas': lista_programas(area, facultad)}


# ============ DASHBOARD POR ÁREA / PROGRAMA ============
@app.route('/dashboard-areas')
def dashboard_areas():
    # Conteo por área
    por_area = db.session.query(
        Proyecto.area, db.func.count(Proyecto.id)
    ).group_by(Proyecto.area).all()

    # Conteo por programa de estudios
    por_programa = db.session.query(
        Proyecto.area, Proyecto.facultad, Proyecto.programa_estudio,
        db.func.count(Proyecto.id)
    ).group_by(Proyecto.area, Proyecto.facultad, Proyecto.programa_estudio)\
     .order_by(Proyecto.area, Proyecto.programa_estudio).all()

    # Docentes por programa (útil para ver la "carga" de cada programa)
    docentes_por_programa = db.session.query(
        Docente.area, Docente.programa_estudio, db.func.count(Docente.id)
    ).group_by(Docente.area, Docente.programa_estudio).all()

    return render_template(
        'dashboard_areas.html',
        por_area=por_area,
        por_programa=por_programa,
        docentes_por_programa=docentes_por_programa,
        total_proyectos=Proyecto.query.count(),
        total_docentes=Docente.query.count(),
    )


# ============ SIMULADOR DE CRONOGRAMA ============
@app.route('/simulador', methods=['GET', 'POST'])
def simulador():
    resultado = None
    if request.method == 'POST':
        # Parámetros del simulador
        num_proyectos = int(request.form.get('num_proyectos', 0))
        duracion = int(request.form.get('duracion', 15))       # minutos por exposición
        hora_inicio = request.form.get('hora_inicio', '08:00')
        hora_fin = request.form.get('hora_fin', '18:00')
        receso_min = int(request.form.get('receso', 10))       # minutos de receso entre exposiciones
        almuerzo_min = int(request.form.get('almuerzo', 60))   # minutos de almuerzo

        # Parsear horas
        from datetime import datetime, timedelta
        def parse_hora(h):
            return datetime.strptime(h, '%H:%M')

        inicio = parse_hora(hora_inicio)
        fin = parse_hora(hora_fin)
        minutos_disponibles_dia = int((fin - inicio).total_seconds() / 60)
        # Restamos el almuerzo
        minutos_efectivos_dia = minutos_disponibles_dia - almuerzo_min

        # Cada proyecto ocupa duracion + receso
        minutos_por_proyecto = duracion + receso_min
        proyectos_por_dia = max(1, minutos_efectivos_dia // minutos_por_proyecto)
        total_capacidad = proyectos_por_dia * 2  # 2 días

        # Distribuir proyectos en 2 días
        dia_1 = min(num_proyectos, proyectos_por_dia)
        dia_2 = min(num_proyectos - dia_1, proyectos_por_dia)

        # Generar agenda sugerida para el día 1
        agenda_dia_1 = []
        hora_actual = inicio
        for i in range(dia_1):
            agenda_dia_1.append({
                'nro': i + 1,
                'inicio': hora_actual.strftime('%H:%M'),
                'fin': (hora_actual + timedelta(minutes=duracion)).strftime('%H:%M'),
                'receso': (hora_actual + timedelta(minutes=duracion + receso_min)).strftime('%H:%M'),
            })
            hora_actual = hora_actual + timedelta(minutes=minutos_por_proyecto)

        # Cuántos quedarían sin cupo
        excedente = max(0, num_proyectos - total_capacidad)

        resultado = {
            'num_proyectos': num_proyectos,
            'duracion': duracion,
            'receso': receso_min,
            'almuerzo': almuerzo_min,
            'hora_inicio': hora_inicio,
            'hora_fin': hora_fin,
            'minutos_efectivos_dia': minutos_efectivos_dia,
            'proyectos_por_dia': proyectos_por_dia,
            'total_capacidad': total_capacidad,
            'dia_1': dia_1,
            'dia_2': dia_2,
            'excedente': excedente,
            'agenda_dia_1': agenda_dia_1,
        }

    # Datos reales del sistema para contexto
    proyectos_reales = Proyecto.query.count()
    por_area_real = db.session.query(
        Proyecto.area, db.func.count(Proyecto.id)
    ).group_by(Proyecto.area).all()

    return render_template('simulador.html',
                           resultado=resultado,
                           proyectos_reales=proyectos_reales,
                           por_area_real=por_area_real)


# ============ CRONOGRAMA AUTOMÁTICO POR ÁREA ============
@app.route('/cronograma/auto', methods=['POST'])
def cronograma_auto():
    """Genera día y hora llenando el Día 1 hasta el tope, respetando el almuerzo, y luego el Día 2."""
    from datetime import datetime, timedelta

    duracion = int(request.form.get('duracion', 15))
    receso = int(request.form.get('receso', 10))
    hora_inicio_str = request.form.get('hora_inicio', '08:40')
    hora_fin_str = request.form.get('hora_fin', '17:00')
    almuerzo_min = int(request.form.get('almuerzo', 30))
    hora_almuerzo_str = request.form.get('hora_almuerzo', '13:00')

    inicio = datetime.strptime(hora_inicio_str, '%H:%M')
    fin = datetime.strptime(hora_fin_str, '%H:%M')
    hora_almuerzo = datetime.strptime(hora_almuerzo_str, '%H:%M')
    fin_almuerzo = hora_almuerzo + timedelta(minutes=almuerzo_min)

    # 1. Traer proyectos ordenados ESTRICTAMENTE por Área y Docente
    proyectos = Proyecto.query.join(Docente).order_by(
        Proyecto.area, 
        Docente.nombre
    ).all()

    if not proyectos:
        flash('No hay proyectos para agendar.', 'warning')
        return redirect(url_for('cronograma'))

    # 2. Variables de control
    dia_actual = 1
    hora_actual = inicio
    contador_dia_1 = 0
    contador_dia_2 = 0
    minutos_por_proyecto = duracion + receso

    for p in proyectos:
        # Si ya nos pasamos de la hora de fin, saltamos al Día 2 y reiniciamos la hora
        if hora_actual + timedelta(minutes=duracion) > fin:
            dia_actual = 2
            hora_actual = inicio

        # Si el bloque de tiempo choca con el almuerzo, saltamos el almuerzo
        # (Verificamos si la hora de inicio o fin del proyecto cae dentro del almuerzo)
        if hora_actual >= hora_almuerzo and hora_actual < fin_almuerzo:
            hora_actual = fin_almuerzo
        # Si el proyecto empezaría justo antes del almuerzo pero terminaría después,
        # mejor lo pasamos después del almuerzo para no interrumpir.
        elif hora_actual < hora_almuerzo and (hora_actual + timedelta(minutes=duracion)) > hora_almuerzo:
            hora_actual = fin_almuerzo

        # Asignar datos
        p.dia = dia_actual
        p.hora = hora_actual.strftime('%H:%M')
        p.duracion = duracion

        # Avanzar el reloj para el siguiente proyecto
        hora_actual += timedelta(minutes=minutos_por_proyecto)

        # Contadores para el mensaje final
        if dia_actual == 1:
            contador_dia_1 += 1
        else:
            contador_dia_2 += 1

    db.session.commit()
    flash(f'Cronograma generado. Día 1: {contador_dia_1} proyectos. Día 2: {contador_dia_2} proyectos.', 'success')
    return redirect(url_for('cronograma'))

@app.route('/exportar_evaluaciones')
def exportar_evaluaciones():
    periodo_des = request.args.get('periodo_desempeno', '2026-I')
    periodo_cues = request.args.get('periodo_cuestionario', '2026-I')
    
    wb = Workbook()
    
    ws1 = wb.active
    ws1.title = "Desempeño Docente"
    ws1.append(["FACULTAD", "DNI", "DOCENTE", "PUNTAJE", "PERIODO"])
    
    ws2 = wb.create_sheet("Cuestionario Docente")
    ws2.append(["Código", "Apellidos y Nombres", "PF", "PERIODO"])

    ws3 = wb.create_sheet("Consolidado Final")
    ws3.append(["Área", "Facultad", "DNI", "Docente", "Proyecto", "Nota Jurados (28)", "Desempeño", "Cuestionario", "Promedio Final (%)"])

    docentes = Docente.query.all()
    
    # Diccionario para guardar las notas consolidadas (para usarlas en la Hoja 3)
    notas_calculadas = {}

    for d in docentes:
        # Función auxiliar para obtener la nota según el periodo
        def obtener_nota(tipo, periodo_elegido):
            if periodo_elegido == 'AMBOS':
                # Si es ambos, promediamos las notas encontradas
                notas = NotaPeriodo.query.filter_by(docente_id=d.id, tipo=tipo).all()
                if notas:
                    return round(sum(n.nota for n in notas) / len(notas), 2)
                return 0
            else:
                nota_obj = NotaPeriodo.query.filter_by(docente_id=d.id, tipo=tipo, periodo=periodo_elegido).first()
                return nota_obj.nota if nota_obj else 0

        n_des = obtener_nota('desempeno', periodo_des)
        n_cue = obtener_nota('cuestionario', periodo_cues)
        
        notas_calculadas[d.id] = {'desempeno': n_des, 'cuestionario': n_cue}

        ws1.append([
            limpiar_texto_excel(d.facultad or '-'), 
            limpiar_texto_excel(d.dni), 
            limpiar_texto_excel(d.nombre), 
            f"{n_des}%", 
            limpiar_texto_excel(periodo_des)
        ])
        ws2.append([
            limpiar_texto_excel(d.dni), 
            limpiar_texto_excel(d.nombre), 
            n_cue, 
            limpiar_texto_excel(periodo_cues)
        ])

    for p in Proyecto.query.all():
        cals = Calificacion.query.filter_by(proyecto_id=p.id).all()
        suma_notas = sum(c.nota_final for c in cals)
        prom_jurados = (suma_notas / len(cals)) if cals else 0
        porcentaje_jurados = (prom_jurados / 28) * 100 if prom_jurados else 0
        
        doc = p.autor
        nota_des = notas_calculadas[doc.id]['desempeno'] if doc and doc.id in notas_calculadas else 0
        nota_cue = notas_calculadas[doc.id]['cuestionario'] if doc and doc.id in notas_calculadas else 0
        
        # Cálculo del promedio final
        prom_final = (porcentaje_jurados * 0.40) + (nota_des * 0.30) + (nota_cue * 0.30)
        
        row = [
            limpiar_texto_excel(p.area or ''),
            limpiar_texto_excel(p.facultad or ''),
            limpiar_texto_excel(doc.dni if doc else '-'),
            limpiar_texto_excel(doc.nombre if doc else '-'),
            limpiar_texto_excel(p.nombre_bp),
            round(prom_jurados, 2), nota_des, nota_cue, round(prom_final, 2)
        ]
        ws3.append(row)

    for ws in [ws1, ws2, ws3]:
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="1A3D7C", end_color="1A3D7C", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 20

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='Reporte_Consolidado.xlsx')
@app.route('/exportar')
def vista_exportar():
    resultados_por_area = {}
    for p in Proyecto.query.all():
        calculos = calcular_promedio_final(p)
        area = p.area or 'SIN ÁREA'
        
        if area not in resultados_por_area:
            resultados_por_area[area] = []
            
        resultados_por_area[area].append({
            'nombre': p.autor.nombre if p.autor else '-',
            'proyecto': p.nombre_bp,
            'promedio': calculos['prom_final'],
            'nivel': calculos['nivel']
        })
    
    # Ordenar cada área por promedio (de mayor a menor)
    for area in resultados_por_area:
        resultados_por_area[area].sort(key=lambda x: x['promedio'], reverse=True)
        
    return render_template('exportar.html', resultados_por_area=resultados_por_area)

from models import db, Docente, Proyecto, Jurado, Criterio, NivelCriterio, Calificacion, DetalleCalificacion, NotaPeriodo

@app.route('/docentes/importar_notas', methods=['GET', 'POST'])
def importar_notas():
    if request.method == 'POST':
        archivo = request.files.get('archivo')
        tipo_nota = request.form.get('tipo_nota') # 'desempeno' o 'cuestionario'
        periodo = request.form.get('periodo')     # '2025-II' o '2026-I'
        
        if not archivo or archivo.filename == '':
            flash('Debes seleccionar un archivo Excel.', 'danger')
            return redirect(url_for('importar_notas'))

        try:
            wb = load_workbook(archivo, data_only=True)
            ws = wb.active
            headers = [cell.value for cell in ws[1]]
            
            idx_dni = None
            idx_nota = None
            
            for i, h in enumerate(headers):
                if h and str(h).strip().upper() in ['DNI', 'CÓDIGO', 'CODIGO']:
                    idx_dni = i
                if h and str(h).strip().upper() in ['NOTA', 'PF', 'PUNTAJE', 'DESEMPEÑO']:
                    idx_nota = i
            
            if idx_dni is None or idx_nota is None:
                flash('El Excel debe tener una columna "DNI" y una columna "Nota" (o PF).', 'danger')
                return redirect(url_for('importar_notas'))

            actualizados = 0
            no_encontrados = 0
            
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or row[idx_dni] is None:
                    continue
                    
                dni = str(row[idx_dni]).strip().replace('.0', '')
                nota_val = row[idx_nota]
                
                if nota_val is None:
                    continue
                    
                try:
                    nota = float(nota_val)
                except:
                    continue

                docente = Docente.query.filter_by(dni=dni).first()
                if docente:
                    # Buscar si ya existe una nota para este docente, tipo y periodo
                    nota_existente = NotaPeriodo.query.filter_by(
                        docente_id=docente.id, 
                        tipo=tipo_nota, 
                        periodo=periodo
                    ).first()
                    
                    if nota_existente:
                        nota_existente.nota = nota
                    else:
                        nueva_nota = NotaPeriodo(
                            docente_id=docente.id,
                            tipo=tipo_nota,
                            periodo=periodo,
                            nota=nota
                        )
                        db.session.add(nueva_nota)
                    
                    actualizados += 1
                else:
                    no_encontrados += 1

            db.session.commit()
            flash(f'Importación exitosa ({periodo} - {tipo_nota}): {actualizados} notas guardadas. ({no_encontrados} DNI no encontrados)', 'success')
            return redirect(url_for('lista_docentes'))

        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'danger')
            return redirect(url_for('importar_notas'))

    return render_template('docentes/importar_notas.html')
# ============ INICIALIZACIÓN ============
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
