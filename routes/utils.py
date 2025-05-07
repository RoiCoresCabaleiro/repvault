import json, os
from flask import current_app
import sirope

from models.ejercicio import Ejercicio
from models.plantilla import Plantilla



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

            oid = e.__oid__
            soid = encode_oid(oid)
            orden.append(soid)
            ejercicios[soid] = item.get("series", 1)

        p.orden      = orden
        p.ejercicios = ejercicios
        srp.save(p)