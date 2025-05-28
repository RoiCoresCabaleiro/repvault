import json, os
from flask import current_app, request
from flask_login import current_user
import sirope
import random
from datetime import datetime, timedelta

from models.ejercicio import Ejercicio
from models.plantilla import Plantilla
from models.entrenamiento_realizado import EntrenamientoRealizado



# Devuelve la identificación segura para un objeto, dado su OID
def encode_oid(oid):
    s = sirope.Sirope()
    return s.safe_from_oid(oid)

# Devuelve el OID de un objeto, dada su identificación segura
def decode_oid(soid):
    s = sirope.Sirope()
    return s.oid_from_safe(soid)



# Listas de grupos musculares y equipamientos válidos para filtros
GRUPOS_VALIDOS = ["Pecho", "Espalda", "Hombros", "Bíceps", "Tríceps", "Piernas", "Abdomen"]
EQUIPAMIENTOS_VALIDOS = ["Peso libre", "Máquina"]


# Método auxiliar para calcular los ejercicios seleccionados (es decir, ya incluidos en la plantilla)
# a los que se les puede asignar el numero de series y editar su orden en la vista gestion_plantillas.html
def calcular_ejs_seleccionados(plantilla):
    srp = sirope.Sirope()
    
    orden_oids = [decode_oid(soid) for soid in plantilla.orden]
    ej_iter = srp.multi_load(orden_oids)

    seleccionados = []
    for soid, ej in zip(plantilla.orden, ej_iter):
        if ej:
            seleccionados.append((soid, ej))

    return seleccionados

# Método auxiliar para calcular los ejercicios disponibles (es decir, aun no incluidos en la plantilla)
# sobre los que se aplican los filtros en la vista gestion_plantillas.html
def calcular_ejs_disponibles(plantilla, grupo_filtro, equipamiento_filtro):
    srp = sirope.Sirope()
    claves_sel = set(plantilla.ejercicios.keys())

    #propiedad, no estar ya seleccionado, y filtros
    ent_objs = srp.filter(
        Ejercicio,
        lambda e: (
            e.is_owner(current_user.get_id())
            and (encode_oid(e.oid) not in claves_sel)
            and (not grupo_filtro or e.grupo_muscular == grupo_filtro)
            and (not equipamiento_filtro or e.equipamiento == equipamiento_filtro)
        )
    )
    disponibles = sorted([(encode_oid(e.oid), e) for e in ent_objs], key=lambda x: x[1].nombre.lower())
    
    return disponibles



# Metodo auxiliar para reconstruir listas y filtros de ejercicios en actual() y finalizar() (vista entrenamientos/actual.html)
def build_entrenamiento_context(entrenamiento):
    srp = sirope.Sirope()
    # — 1) Ejercicios del usuario —
    ej_objs = srp.filter(
        Ejercicio,
        lambda e: e.is_owner(current_user.get_id())
    )
    ejercicios_usuario = sorted([(encode_oid(e.oid), e) for e in ej_objs], key=lambda x: x[1].nombre.lower())

    # — 2) Últimas series —
    ej_oids = [decode_oid(soid) for soid in entrenamiento.ejercicios]
    ejercicios = srp.multi_load(ej_oids)
    ultimos_valores = {
        safe_oid: getattr(ej, "ultimas_series", [])
        for safe_oid, ej in zip(entrenamiento.ejercicios.keys(), ejercicios) if ej
    }

    # — 3) Capturar filtros —
    grupo_filtro        = request.values.get("grupo_muscular", "")
    equipamiento_filtro = request.values.get("equipamiento", "")

    # — 4) Filtrar disponibles —
    actuales = set(entrenamiento.ejercicios.keys())
    ejercicios_disponibles = [
        (soid, ej) for soid, ej in ejercicios_usuario
        if soid not in actuales
           and (not grupo_filtro or ej.grupo_muscular == grupo_filtro)
           and (not equipamiento_filtro or ej.equipamiento == equipamiento_filtro)
    ]

    return ejercicios_usuario, ultimos_valores, grupo_filtro, equipamiento_filtro, ejercicios_disponibles



def serie_valida(s):
        try:
            p = float(s["peso"])
            r = int(s["reps"])
        except (KeyError, ValueError, TypeError):
            return False
        return s.get("hecha") and (0 <= p <= 1000) and (1 <= r <= 100)




# Carga ejercicios desde data/default_exercises.json y los salva en Redis bajo el usuario dado.
def importar_ejercicios_por_defecto(usuario_nombre):
    srp = sirope.Sirope()
    ruta = os.path.join(current_app.root_path, "data", "default_ejercicios.json")
    with open(ruta, encoding="utf-8") as f:
        defaults = json.load(f)

    for d in defaults:
        ej = Ejercicio(
            usuario_nombre = usuario_nombre,
            nombre         = d["nombre"],
            descripcion    = d["descripcion"],
            grupo_muscular = d["grupo_muscular"],
            equipamiento   = d["equipamiento"]
        )
        srp.save(ej)



# Lee data/default_plantillas.json y crea una Plantilla por cada entrada, asignándola al usuario dado.
# Para mapear nombre_ejercicio → OID usamos el nombre de ejercicio y Sirope.filter().
def importar_plantillas_por_defecto(usuario_nombre):
    srp = sirope.Sirope()
    ruta = os.path.join(current_app.root_path, "data", "default_plantillas.json")
    with open(ruta, encoding="utf-8") as f:
        defaults = json.load(f)

    for tpl in defaults:
        p = Plantilla(tpl["nombre"], tpl.get("observaciones",""), usuario_nombre)
        orden = []
        ejercicios = {}
        for item in tpl["ejercicios"]:
            e = srp.find_first(
                Ejercicio,
                lambda x: x.is_owner(usuario_nombre) and x.nombre == item["nombre_ejercicio"]
            )
            if not e:
                continue

            oid = e.oid
            soid = encode_oid(oid)
            orden.append(soid)
            ejercicios[soid] = item.get("series", 1)

        p.orden      = orden
        p.ejercicios = ejercicios
        srp.save(p)



# Genera entrenamientos diarios para el usuario siguiendo el ciclo dado,
# rellenando cada ejercicio de la plantilla con valores aleatorios de reps y peso
def generar_entrenamientos_historicos(usuario_nombre: str) -> None:
    dias_hacia_atras = 90
    ciclo = ["push", "pull", "legs", "descanso"]
    rango_reps = (8, 15)
    rango_peso = (20, 80)
    
    srp = sirope.Sirope()
    inicio = datetime.now() - timedelta(days=dias_hacia_atras)
    fin    = datetime.now()
    fecha = inicio
    i = 0

    while fecha <= fin:
        rutina = ciclo[i % len(ciclo)].lower()
        # saltar descanso antes de buscar plantilla
        if rutina == "descanso":
            fecha += timedelta(days=1)
            i += 1
            continue

        tpl = srp.find_first(Plantilla, lambda p: p.is_owner(usuario_nombre) and p.nombre.lower() == rutina)
        if tpl:
            ejercicios_payload = {}
            for soid in tpl.orden:
                n_series = tpl.ejercicios.get(soid, 0)
                series = []
                for _ in range(n_series):
                    series.append({
                        "peso": str(random.randint(*rango_peso)),
                        "reps":  random.randint(*rango_reps)
                    })
                ejercicios_payload[soid] = series

            ent = EntrenamientoRealizado(
                usuario_nombre = usuario_nombre,
                nombre         = f"{tpl.nombre.title()} {fecha.strftime('%d-%m-%Y')}",
                observaciones  = tpl.observaciones or "",
                ejercicios     = ejercicios_payload,
                fecha          = fecha.strftime("%d/%m/%Y %H:%M:%S"),
                duracion       = random.randint(30, 90)
            )
            srp.save(ent)

            # Guardar valores adicionales de los entrenamientos del ultimo ciclo realizado
            if (i > (dias_hacia_atras - (len(ciclo) + 1))):
                # — Actualizar últimas series de cada ejercicio —
                for soid, series in ejercicios_payload.items():
                    try:
                        ej = srp.load(decode_oid(soid))
                        ej.ultimas_series = series
                        srp.save(ej)
                    except (ValueError, NameError, AttributeError, TypeError):
                        pass

                # — Actualizar última vez de la plantilla origen —
                tpl.ultima_vez = fecha.strftime("%d/%m/%Y %H:%M:%S")
                srp.save(tpl)

        fecha += timedelta(days=1)
        i += 1

    print("✅ Generación histórica completada para", usuario_nombre)