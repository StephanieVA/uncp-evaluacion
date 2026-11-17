from app import app
from models import db, Criterio, NivelCriterio

def seed_rubrica():
    # Si ya hay criterios, los borramos para actualizar a la nueva rúbrica
    Criterio.query.delete()
    NivelCriterio.query.delete()
    db.session.commit()

    criterios_data = [
        (
            "Pertinencia curricular", 
            "Evidencia alineación con competencias, sílabo y resultados de aprendizaje.",
            [
                ("Excelente", 4, "Evidencia alineación clara con competencias, sílabo y resultados de aprendizaje."),
                ("Bueno", 3, "Presenta adecuada relación curricular."),
                ("Regular", 2, "La relación curricular es parcial."),
                ("Deficiente", 1, "No evidencia alineación curricular.")
            ]
        ),
        (
            "Innovación pedagógica", 
            "Aplica estrategias o recursos innovadores con valor pedagógico evidente.",
            [
                ("Excelente", 4, "Aplica estrategias o recursos innovadores con valor pedagógico evidente."),
                ("Bueno", 3, "Presenta innovación pertinente."),
                ("Regular", 2, "La innovación es limitada."),
                ("Deficiente", 1, "No presenta innovación relevante.")
            ]
        ),
        (
            "Impacto en el aprendizaje", 
            "Presenta evidencias verificables de mejora en el aprendizaje.",
            [
                ("Excelente", 4, "Presenta evidencias verificables de mejora en el aprendizaje."),
                ("Bueno", 3, "Presenta resultados favorables parcialmente sustentados."),
                ("Regular", 2, "Presenta evidencias limitadas."),
                ("Deficiente", 1, "No presenta evidencias de impacto.")
            ]
        ),
        (
            "Sistematización y evidencias", 
            "La experiencia está organizada y sustentada con evidencias claras.",
            [
                ("Excelente", 4, "La experiencia está organizada y sustentada con evidencias claras."),
                ("Bueno", 3, "Presenta organización y evidencias suficientes."),
                ("Regular", 2, "La organización o evidencias son parciales."),
                ("Deficiente", 1, "Presenta desorden y escasas evidencias.")
            ]
        ),
        (
            "Sostenibilidad y replicabilidad", 
            "La práctica puede mantenerse y aplicarse en otros contextos.",
            [
                ("Excelente", 4, "La práctica puede mantenerse y aplicarse en otros contextos."),
                ("Bueno", 3, "Tiene posibilidades de continuidad y adaptación."),
                ("Regular", 2, "Presenta limitada sostenibilidad o replicabilidad."),
                ("Deficiente", 1, "No evidencia continuidad ni posibilidad de réplica.")
            ]
        ),
        (
            "Inclusión y participación estudiantil", 
            "Promueve participación e inclusión de los estudiantes.",
            [
                ("Excelente", 4, "Promueve participación e inclusión de los estudiantes."),
                ("Bueno", 3, "Considera aspectos básicos de inclusión."),
                ("Regular", 2, "Presenta limitada participación estudiantil."),
                ("Deficiente", 1, "No considera inclusión ni participación.")
            ]
        ),
        (
            "Exposición y defensa", 
            "Expone con claridad, dominio y manejo adecuado del tiempo.",
            [
                ("Excelente", 4, "Expone con claridad, dominio y manejo adecuado del tiempo."),
                ("Bueno", 3, "Expone adecuadamente la experiencia."),
                ("Regular", 2, "Presenta dificultades de claridad o argumentación."),
                ("Deficiente", 1, "Presenta exposición desordenada y poco sustentada.")
            ]
        ),
    ]

    for i, (nombre, desc, niveles) in enumerate(criterios_data):
        c = Criterio(nombre=nombre, descripcion=desc, peso=1.0, orden=i)
        db.session.add(c)
        db.session.flush()
        for etiqueta, puntaje, ndesc in niveles:
            db.session.add(NivelCriterio(criterio_id=c.id, etiqueta=etiqueta,
                                         puntaje=puntaje, descripcion=ndesc))
    db.session.commit()
    print("Rúbrica de 7 criterios cargada correctamente (Total máximo: 28 pts).")

if __name__ == '__main__':
    with app.app_context():
        seed_rubrica()