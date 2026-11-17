# catalogos.py

FACULTADES = [
    # ===== ÁREA I =====
    {"codigo": "MH", "area": "ÁREA I", "nombre": "Facultad de Medicina Humana",
     "programas": ["Medicina Humana"]},
    {"codigo": "EN", "area": "ÁREA I", "nombre": "Facultad de Enfermería",
     "programas": ["Enfermería"]},

    # ===== ÁREA II =====
    {"codigo": "AR", "area": "ÁREA II", "nombre": "Facultad de Arquitectura",
     "programas": ["Arquitectura"]},
    {"codigo": "IC", "area": "ÁREA II", "nombre": "Facultad de Ingeniería Civil",
     "programas": ["Ingeniería Civil"]},
    {"codigo": "MI", "area": "ÁREA II", "nombre": "Facultad de Ingeniería de Minas",
     "programas": ["Ingeniería de Minas"]},
    {"codigo": "IS", "area": "ÁREA II", "nombre": "Facultad de Ingeniería de Sistemas",
     "programas": ["Ingeniería de Sistemas"]},
    {"codigo": "IE", "area": "ÁREA II", "nombre": "Facultad de Ingeniería Eléctrica y Electrónica",
     "programas": ["Ingeniería Eléctrica y Electrónica"]},
    {"codigo": "ME", "area": "ÁREA II", "nombre": "Facultad de Ingeniería Mecánica",
     "programas": ["Ingeniería Mecánica"]},
    {"codigo": "MT", "area": "ÁREA II", "nombre": "Facultad de Ingeniería Metalúrgica y de Materiales",
     "programas": ["Ingeniería Metalúrgica y de Materiales"]},
    {"codigo": "IQ", "area": "ÁREA II", "nombre": "Facultad de Ingeniería Química",
     "programas": ["Ingeniería Química", "Ingeniería Química Ambiental",
                   "Ingeniería Química Industrial"]},

    # ===== ÁREA III =====
    {"codigo": "AD", "area": "ÁREA III", "nombre": "Facultad de Ciencias de la Administración",
     "programas": ["Administración de Empresas"]},
    {"codigo": "CO", "area": "ÁREA III", "nombre": "Facultad de Contabilidad",
     "programas": ["Contabilidad"]},
    {"codigo": "EC", "area": "ÁREA III", "nombre": "Facultad de Economía",
     "programas": ["Economía"]},
    {"codigo": "ET", "area": "ÁREA III", "nombre": "Facultad de Ciencias Aplicadas (Tarma)",
     "programas": ["Administración de Negocios Tarma", "Hotelería y Turismo Tarma"]},

    # ===== ÁREA IV =====
    {"codigo": "AN", "area": "ÁREA IV", "nombre": "Facultad de Antropología",
     "programas": ["Antropología"]}, # NOTA: Derecho está en otra facultad, ver abajo
    {"codigo": "DE", "area": "ÁREA IV", "nombre": "Facultad de Derecho y Ciencias Políticas",
     "programas": ["Derecho y Ciencias Políticas"]},
    {"codigo": "SO", "area": "ÁREA IV", "nombre": "Facultad de Sociología",
     "programas": ["Sociología"]},
    {"codigo": "TS", "area": "ÁREA IV", "nombre": "Facultad de Trabajo Social",
     "programas": ["Trabajo Social"]},
    {"codigo": "CC", "area": "ÁREA IV", "nombre": "Facultad de Ciencias de la Comunicación",
     "programas": ["Ciencias de la Comunicación"]},
    {"codigo": "ED", "area": "ÁREA IV", "nombre": "Facultad de Educación",
     "programas": ["Educación Inicial", "Educación Primaria",
                   "Educación Ciencias Matemáticas e Informática",
                   "Educación Ciencias Naturales y Ambientales",
                   "Educación Lenguas, Literatura y Comunicación",
                   "Educación Filosofía, Ciencias Sociales y Relaciones Humanas",
                   "Educación Física y Psicomotricidad"]},

    # ===== ÁREA V =====
    {"codigo": "AG", "area": "ÁREA V", "nombre": "Facultad de Agronomía",
     "programas": ["Agronomía"]},
    {"codigo": "FO", "area": "ÁREA V", "nombre": "Facultad de Ingeniería Forestal y Ambiental",
     "programas": ["Ingeniería Forestal y Ambiental", "Ingeniería Ambiental"]},
    {"codigo": "IA", "area": "ÁREA V", "nombre": "Facultad de Ingeniería en Industrias Alimentarias",
     "programas": ["Ingeniería en Industrias Alimentarias"]},
    {"codigo": "ZO", "area": "ÁREA V", "nombre": "Facultad de Zootecnia",
     "programas": ["Zootecnia"]},
    {"codigo": "CA", "area": "ÁREA V", "nombre": "Facultad de Ciencias Agrarias (Satipo)",
     "programas": ["Agronomía Tropical Satipo", "Ingeniería Forestal Tropical Satipo",
                   "Ingeniería Industrias Alimentarias Tropical Satipo",
                   "Zootecnia Tropical Satipo"]},
    {"codigo": "ET", "area": "ÁREA V", "nombre": "Facultad de Ciencias Aplicadas (Tarma)",
     "programas": ["Ingeniería Agroindustrial Tarma"]},
]


def lista_areas():
    return sorted(set(f["area"] for f in FACULTADES))


def lista_facultades(area=None):
    vistas, resultado = set(), []
    for f in FACULTADES:
        if area and f["area"] != area:
            continue
        if f["nombre"] in vistas:
            continue
        vistas.add(f["nombre"])
        resultado.append(f["nombre"])
    return resultado


def lista_programas(area, facultad):
    vistos, resultado = set(), []
    for f in FACULTADES:
        if f["area"] != area or f["nombre"] != facultad:
            continue
        for p in f["programas"]:
            if p not in vistos:
                vistos.add(p)
                resultado.append(p)
    return resultado


def _norm(s):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', str(s))
                   if unicodedata.category(c) != 'Mn').upper().strip()


def facultad_desde_codigo(codigo):
    """'EN' -> 'Facultad de Enfermería'"""
    if not codigo:
        return None
    objetivo = _norm(codigo)
    for f in FACULTADES:
        if _norm(f["codigo"]) == objetivo:
            # Si hay códigos duplicados (ej. ET), devuelve el primero
            return f["nombre"]
    return None


def area_desde_facultad(nombre_o_codigo):
    """Acepta nombre completo o código y devuelve el área."""
    if not nombre_o_codigo:
        return None
    objetivo = _norm(nombre_o_codigo)
    # por código
    for f in FACULTADES:
        if _norm(f["codigo"]) == objetivo:
            return f["area"]
    # por nombre completo
    for f in FACULTADES:
        if _norm(f["nombre"]) == objetivo:
            return f["area"]
    return None