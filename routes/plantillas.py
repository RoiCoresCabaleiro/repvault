from flask import Blueprint, render_template, request, redirect, url_for, session
from flask_login import login_required, current_user
import sirope
from datetime import datetime

from models.plantilla import Plantilla
from routes.utils import encode_oid, decode_oid, GRUPOS_VALIDOS, EQUIPAMIENTOS_VALIDOS, calcular_ejs_seleccionados, calcular_ejs_disponibles

plantillas_bp = Blueprint("plantillas", __name__, url_prefix="/plantillas")




@plantillas_bp.route("/")
@login_required
def lista():
    """
    Listar todas las plantillas del Usuario, mostrando sus observaciones, nº de ejercicios y fecha de ultima vez (realizada)
    """
    srp = sirope.Sirope()

    ej_objs = srp.filter(
        Plantilla,
        lambda p: p.is_owner(current_user.get_id())
    )
    plantillas_usuario = [(encode_oid(p.oid), p) for p in ej_objs]

    # Ordenar plantillas por fecha de ultima vez realizada y nombre alfabeticamente
    plantillas_usuario.sort(key=lambda x: x[1].nombre.lower())
    plantillas_usuario.sort(key=lambda x: datetime.strptime(x[1].ultima_vez, "%d/%m/%Y %H:%M:%S") if x[1].ultima_vez else datetime.min, reverse=True)

    return render_template("plantillas/lista.html", plantillas=plantillas_usuario, error_redirect=request.args.get("error_redirect", None))



@plantillas_bp.route("/ver/<path:clave>")
@login_required
def ver(clave):
    """
    Ver detalles de una Plantilla (nombre, observaciones y Ejercicios incluidos y sus series planificadas)
    """
    srp = sirope.Sirope()
    
    try:
        plantilla = srp.load(decode_oid(clave))
    except (AttributeError, ValueError, NameError):
        return redirect(url_for("plantillas.lista", error_redirect="Rutina no encontrada."))
    
    if not plantilla or not plantilla.is_owner(current_user.get_id()):
        return redirect(url_for("plantillas.lista", error_redirect="No tienes permiso para editar esta rutina."))

    # Obtener ejercicios de la plantilla
    ej_oids = [decode_oid(soid) for soid in plantilla.orden]
    ej_iter = srp.multi_load(ej_oids)
    
    ejercicios_plantilla = []
    for soid, ej in zip(plantilla.orden, ej_iter):
        if ej:
            ejercicios_plantilla.append((soid, ej))
    
    return render_template("plantillas/ver.html", plantilla=plantilla, ejercicios_plantilla=ejercicios_plantilla, clave=clave)



@plantillas_bp.route("/nueva", methods=["GET", "POST"])
@plantillas_bp.route("/editar/<path:clave>", methods=["GET", "POST"])
@login_required
def gestionar(clave=None):
    """
    Crear plantillas nuevas y editar existentes de forma interactiva.\n
    Se especifican nombre y observaciones opcionales de forma convencional y los ejercicios se añaden dinámicamente
    a través de un panel que permite aplicar filtros.\n
    De forma que se puede especificar luego el número de series por ejercicio y alterar su orden mediante flechas
    """
    srp     = sirope.Sirope()
    plantilla_real = None

    # Si es GET “puro” (sin filtrar), reiniciamos el estado temporal
    if request.method == "GET" and "filtrar" not in request.args:
        session.pop("tmp_plantilla", None)

    # Si estamos editando, cargar plantilla existente
    if clave:
        try:
            plantilla_real = srp.load(decode_oid(clave))
        except (AttributeError, ValueError, NameError):
            return redirect(url_for("plantillas.lista", error_redirect="Rutina no encontrada."))
        
        if not plantilla_real or not plantilla_real.is_owner(current_user.get_id()):
             return redirect(url_for("plantillas.lista", error_redirect="No tienes permiso para editar esta rutina."))

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
            elif len(data["nombre"]) > 40:
                error = "El nombre de la rutina no puede superar los 40 caracteres"

            # Comprobar duplicados (excluyendo la propia al editar)
            if not error:
                original_oid = plantilla_real.oid if plantilla_real else None
                dup = srp.find_first(
                    Plantilla,
                    lambda p: (
                        p.is_owner(current_user.get_id())
                        and p.nombre.lower() == data["nombre"].lower()
                        and (not original_oid or p.oid != original_oid)
                    )
                )
                if dup:
                    error = "Ya tienes una plantilla con ese nombre."

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
                    session.pop("tmp_plantilla", None)
                    return redirect(url_for("plantillas.ver", clave=encode_oid(plantilla_real.oid)))
                else:
                    # Crear nueva plantilla
                    nueva = Plantilla(data["nombre"], data["observaciones"], current_user.get_id())
                    nueva.orden      = data["orden"]
                    nueva.ejercicios = data["ejercicios"]
                    srp.save(nueva)
                    session.pop("tmp_plantilla", None)
                    return redirect(url_for("plantillas.ver", clave=encode_oid(nueva.oid)))
                
        # 4) Guardar estado intermedio en sesión
        session["tmp_plantilla"] = data

    # Preparar objeto Plantilla para la vista
    plantilla = Plantilla(data["nombre"], data["observaciones"], current_user.get_id())
    plantilla.orden      = data["orden"]
    plantilla.ejercicios = data["ejercicios"]

    seleccionados = calcular_ejs_seleccionados(plantilla)
    disponibles  = calcular_ejs_disponibles(plantilla, grupo_filtro, equipamiento_filtro)

    return render_template(
        "plantillas/gestion_plantillas.html",
        plantilla=plantilla,
        is_edit=bool(clave),
        clave=clave,
        error=error,
        ejercicios_seleccionados=seleccionados,
        ejercicios_disponibles=disponibles,
        grupos_validos=GRUPOS_VALIDOS,
        equipamientos_validos=EQUIPAMIENTOS_VALIDOS,
        grupo_filtro=grupo_filtro,
        equipamiento_filtro=equipamiento_filtro
    )



@plantillas_bp.route("/eliminar/<path:clave>", methods=["POST"])
@login_required
def eliminar(clave):
    """
    Eliminar una plantilla existente.\n
    Esta acción no tiene ningún efecto en el resto de clases
    """
    srp = sirope.Sirope()
    plantilla = srp.load(decode_oid(clave))

    if plantilla and plantilla.is_owner(current_user.get_id()):
        srp.delete(plantilla.oid)

    return redirect(url_for("plantillas.lista"))
