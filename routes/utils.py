import json, os
from flask import current_app
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



# Listas comunes
GRUPOS_VALIDOS = ["Pecho", "Espalda", "Hombros", "Bíceps", "Tríceps", "Piernas", "Abdomen"]
EQUIPAMIENTOS_VALIDOS = ["Peso libre", "Máquina"]



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
                lambda x: x.usuario_nombre == usuario_nombre and x.nombre == item["nombre_ejercicio"]
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

        tpl = srp.find_first(Plantilla, lambda p: p.usuario_nombre == usuario_nombre and p.nombre.lower() == rutina)
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

            # — Actualizar últimas series de cada ejercicio —
            for soid, series in ejercicios_payload.items():
                try:
                    ej = srp.load(decode_oid(soid))
                    ej.ultimas_series = series
                    srp.save(ej)
                except:
                    pass

            # — Actualizar última vez de la plantilla origen —
            try:
                 p = srp.load(decode_oid(tpl._id))
                 if p and p.usuario_nombre == usuario_nombre:
                     p.ultima_vez = fecha.strftime("%d/%m/%Y %H:%M:%S")
                     srp.save(p)
            except:
                 pass

        fecha += timedelta(days=1)
        i += 1

    print("✅ Generación histórica completada para", usuario_nombre)