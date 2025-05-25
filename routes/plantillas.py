from flask import Blueprint, render_template, request, redirect, url_for, session
from flask_login import login_required, current_user
import sirope
from datetime import datetime

from models.plantilla import Plantilla
from models.ejercicio import Ejercicio
from routes.utils import encode_oid, decode_oid, GRUPOS_VALIDOS, EQUIPAMIENTOS_VALIDOS

plantillas_bp = Blueprint("plantillas", __name__, url_prefix="/plantillas")



@plantillas_bp.route("/")
@login_required
def lista():
    srp = sirope.Sirope()
    plantillas_usuario = []

    for oid in srp.load_all_keys(Plantilla):
        p = srp.load(oid)
        if p.is_owner(current_user.get_id()):
            clave = encode_oid(oid)
            plantillas_usuario.append((clave, p))

    # Ordenar plantillas por fecha de ultima vez realizada y nombre alfabeticamente
    plantillas_usuario.sort(key=lambda tup: tup[1].nombre.lower())
    plantillas_usuario.sort(key=lambda tup: datetime.strptime(tup[1].ultima_vez, "%d/%m/%Y %H:%M:%S") if tup[1].ultima_vez else datetime.min, reverse=True)

    return render_template("plantillas/lista.html", plantillas=plantillas_usuario)


@plantillas_bp.route("/nueva", methods=["GET", "POST"])
@plantillas_bp.route("/editar/<soid>", methods=["GET", "POST"])
@login_required
def gestionar(soid=None):
    srp     = sirope.Sirope()
    plantilla_real = None

    # Si es GET “puro” (sin filtrar), reiniciamos el estado temporal
    if request.method == "GET" and "filtrar" not in request.args:
        session.pop("tmp_plantilla", None)

    # Si estamos editando, cargamos la plantilla real
    if soid:
        try:
            plantilla_real = srp.load(decode_oid(soid))
        except (AttributeError, ValueError, NameError):
            return redirect(url_for("plantillas.ver", soid=soid))

        if not plantilla_real or not plantilla_real.is_owner(current_user.get_id()):
             return redirect(url_for("plantillas.ver", soid=soid))

    # Inicializar estado temporal en sesión si no existe
    if "tmp_plantilla" not in session:
        if plantilla_real:
            session["tmp_plantilla"] = {
                "nombre":        plantilla_real.nombre,
                "observaciones": plantilla_real.observaciones,
                "orden":         plantilla_real.orden.copy(),
                "ejercicios":    plantilla_real.ejercicios.copy(),
            }
        else:
            session["tmp_plantilla"] = {
                "nombre":        "",
                "observaciones": "",
                "orden":         [],
                "ejercicios":    {},
            }

    data  = session["tmp_plantilla"]
    error = None

    # Filtros (GET o POST)
    grupo_filtro        = request.values.get("grupo_muscular", "")
    equipamiento_filtro = request.values.get("equipamiento", "")

    if request.method == "POST":
        # 1) Actualizar nombre y observaciones
        data["nombre"]        = request.form.get("nombre", data["nombre"]).strip()
        data["observaciones"] = request.form.get("observaciones", data["observaciones"]).strip()

        # 2) Actualizar series de ejercicios seleccionados
        for idx, soid_sel in enumerate(data["orden"]):
            raw = request.form.get(f"series_{idx}")
            if raw:
                try:
                    data["ejercicios"][soid_sel] = int(raw)
                except ValueError:
                    pass

        # 3) Procesar mover / quitar / agregar
        if "mover" in request.form:
            tipo, idx = request.form["mover"].split("-")
            idx = int(idx)
            if tipo == "subir" and idx > 0:
                data["orden"][idx-1], data["orden"][idx] = data["orden"][idx], data["orden"][idx-1]
            elif tipo == "bajar" and idx < len(data["orden"]) - 1:
                data["orden"][idx], data["orden"][idx+1] = data["orden"][idx+1], data["orden"][idx]

        elif "quitar" in request.form:
            soid_quitar = request.form["quitar"]
            if soid_quitar in data["ejercicios"]:
                data["orden"].remove(soid_quitar)
                data["ejercicios"].pop(soid_quitar, None)

        elif "agregar" in request.form:
            soid_add = request.form["agregar"]
            if soid_add not in data["ejercicios"]:
                data["ejercicios"][soid_add] = 1
                data["orden"].append(soid_add)

        elif "guardar" in request.form or "guardar_cambios" in request.form:
            # Validaciones básicas
            if not data["nombre"]:
                error = "El nombre de la rutina no puede estar vacío."
            elif len(data["nombre"]) > 50:
                error = "El nombre de la rutina no puede superar los 50 caracteres"

            if not error:
                # Comprobar duplicados (excluyendo la propia al editar)
                original_oid = plantilla_real.oid if plantilla_real else None
                for oid_chk in srp.load_all_keys(Plantilla):
                    p = srp.load(oid_chk)
                    if (p.is_owner(current_user.get_id()) and
                        p.nombre.lower() == data["nombre"].lower() and
                        (not original_oid or oid_chk != original_oid)):
                        error = "Ya tienes una plantilla con ese nombre."
                        break

            if not error and len(data["observaciones"]) > 500:
                error = "Las observaciones de la rutina no pueden superar los 500 caracteres"
            if not error and not data["ejercicios"]:
                error = "Debes seleccionar al menos un ejercicio."
            if not error:
                for soid_sel, v in data["ejercicios"].items():
                    if not isinstance(v, int) or not (1 <= v <= 20):
                        error = "Cada ejercicio debe tener entre 1 y 20 series."
                        break

            if not error:
                if plantilla_real:
                    # Guardar cambios en la existente
                    plantilla_real.nombre        = data["nombre"]
                    plantilla_real.observaciones = data["observaciones"]
                    plantilla_real.orden         = data["orden"]
                    plantilla_real.ejercicios    = data["ejercicios"]
                    srp.save(plantilla_real)
                else:
                    # Crear nueva plantilla
                    nueva = Plantilla(data["nombre"], data["observaciones"], current_user.get_id())
                    nueva.orden      = data["orden"]
                    nueva.ejercicios = data["ejercicios"]
                    srp.save(nueva)

                session.pop("tmp_plantilla", None)
                return redirect(url_for("plantillas.lista"))

        # 4) Guardar estado intermedio en sesión
        session["tmp_plantilla"] = data

    # Preparar objeto Plantilla para la vista
    plantilla = Plantilla(data["nombre"], data["observaciones"], current_user.get_id())
    plantilla.orden      = data["orden"]
    plantilla.ejercicios = data["ejercicios"]

    seleccionados = calcular_seleccionados(plantilla)
    disponibles  = calcular_disponibles(plantilla, grupo_filtro, equipamiento_filtro)

    return render_template(
        "plantillas/gestion_plantillas.html",
        plantilla=plantilla,
        is_edit=bool(soid),
        soid=soid,
        error=error,
        ejercicios_seleccionados=seleccionados,
        ejercicios_disponibles=disponibles,
        grupos_validos=GRUPOS_VALIDOS,
        equipamientos_validos=EQUIPAMIENTOS_VALIDOS,
        grupo_filtro=grupo_filtro,
        equipamiento_filtro=equipamiento_filtro
    )

def calcular_seleccionados(plantilla):
    srp = sirope.Sirope()
    seleccionados = []
    for clave in plantilla.orden:
        try:
            e = srp.load(decode_oid(clave))
            if e and e.is_owner(current_user.get_id()):
                seleccionados.append((clave, e))
        except (AttributeError, ValueError, NameError):
            continue
    return seleccionados

def calcular_disponibles(plantilla, grupo_filtro, equipamiento_filtro):
    srp = sirope.Sirope()
    disponibles = []
    claves_seleccionadas = set(plantilla.ejercicios.keys())

    for oid in srp.load_all_keys(Ejercicio):
        e = srp.load(oid)
        if e.is_owner(current_user.get_id()):
            clave = encode_oid(oid)
            if clave not in claves_seleccionadas and \
               (not grupo_filtro or e.grupo_muscular == grupo_filtro) and \
               (not equipamiento_filtro or e.equipamiento == equipamiento_filtro):
                disponibles.append((clave, e))

    disponibles.sort(key=lambda x: x[1].nombre.lower())
    return disponibles


@plantillas_bp.route("/ver/<path:clave>")
@login_required
def ver(clave):
    srp = sirope.Sirope()
    plantilla = srp.load(decode_oid(clave))

    if not plantilla.is_owner(current_user.get_id()):
        return redirect(url_for("plantillas.lista"))

    # Obtener todos los ejercicios del usuario
    ejercicios_usuario = []
    for oid_e in srp.load_all_keys(Ejercicio):
        e = srp.load(oid_e)
        if e.is_owner(current_user.get_id()):
            clave_ej = encode_oid(oid_e)
            ejercicios_usuario.append((clave_ej, e))

    return render_template("plantillas/ver.html", plantilla=plantilla, ejercicios=ejercicios_usuario, clave=clave, orden=plantilla.orden)


@plantillas_bp.route("/eliminar/<path:clave>", methods=["GET", "POST"])
@login_required
def eliminar(clave):
    srp = sirope.Sirope()
    plantilla = srp.load(decode_oid(clave))

    if plantilla and plantilla.is_owner(current_user.get_id()):
        srp.delete(plantilla.oid)

    return redirect(url_for("plantillas.lista"))