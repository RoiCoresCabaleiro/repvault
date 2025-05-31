from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
import sirope
from datetime import datetime

from models.ejercicio import Ejercicio
from models.plantilla import Plantilla
from models.entrenamiento_realizado import EntrenamientoRealizado
from routes.utils import encode_oid, decode_oid, GRUPOS_VALIDOS, EQUIPAMIENTOS_VALIDOS

ejercicios_bp = Blueprint("ejercicios", __name__, url_prefix="/ejercicios")



@ejercicios_bp.route("/")
@login_required
def lista():
    """
    Listar todos los ejercicios del usuario, permitiendo filtrarlos mediante grupo muscular y equipamiento
    """

    srp = sirope.Sirope()

    # Capturar filtros
    grupo_filtro = request.args.get("grupo_muscular", "")
    equipamiento_filtro = request.args.get("equipamiento", "")

    if grupo_filtro not in GRUPOS_VALIDOS: grupo_filtro = ""
    if equipamiento_filtro not in EQUIPAMIENTOS_VALIDOS: equipamiento_filtro = ""

    ej_objs = srp.filter(
        Ejercicio,
        lambda e: (
            e.is_owner(current_user.get_id())
            and (not grupo_filtro or e.grupo_muscular == grupo_filtro)
            and (not equipamiento_filtro or e.equipamiento == equipamiento_filtro)
        )
    )    
    ejercicios_usuario = sorted([(encode_oid(e.oid), e) for e in ej_objs], key=lambda x: x[1].nombre.lower())

    return render_template(
        "ejercicios/lista.html",
        ejercicios=ejercicios_usuario,
        grupo_filtro=grupo_filtro,
        equipamiento_filtro=equipamiento_filtro,
        grupos_validos=GRUPOS_VALIDOS,
        equipamientos_validos=EQUIPAMIENTOS_VALIDOS,
        error_redirect=request.args.get("error_redirect", None),
        mensaje=request.args.get("mensaje", None)
    )



@ejercicios_bp.route("/ver/<path:clave>")
@login_required
def ver(clave):
    """
    Ver detalles de un ejercicio existente (Nombre, descripcion, grupo muscular, equipamiento, Historial del ejercicio y Estadísticas)
    """

    srp = sirope.Sirope()

    try:
        ejercicio = srp.load(decode_oid(clave))
    except (AttributeError, ValueError, NameError):
        return redirect(url_for("ejercicios.lista", error_redirect="Ejercicio no encontrado."))
    
    if (ejercicio.__class__ != Ejercicio):
        return redirect(url_for("ejercicios.lista", error_redirect="El objeto llamado no es un Ejercicio"))
    elif not ejercicio.is_owner(current_user.get_id()):
        return redirect(url_for("ejercicios.lista", error_redirect="No tienes permiso para ver este ejercicio."))

    historial_ej = []

    # — Recopilar sesiones donde aparece este ejercicio —
    for ent in srp.filter(
        EntrenamientoRealizado,
        lambda ent: ent.is_owner(current_user.get_id()) and clave in ent.ejercicios
    ):
        datos = ent.ejercicios[clave]
        series = datos["series"] if isinstance(datos, dict) else datos

        historial_ej.append({
            "fecha":           ent.fecha,
            "entrenamiento":   ent.nombre,
            "observaciones":   ent.observaciones,
            "series":          series
        })

    historial_ej.sort(key=lambda x: datetime.strptime(x["fecha"], "%d/%m/%Y %H:%M:%S"), reverse=True)

    # — Aplanar todas las series válidas para este ejercicio —
    flat = []
    for sesion in historial_ej:
        for s in sesion["series"]:
            try:
                peso = float(s["peso"])
                reps = int(s["reps"])
            except (KeyError, ValueError, TypeError):
                continue
            flat.append({
                "peso":   peso,
                "reps":   reps,
                "fecha":  sesion["fecha"]
            })

    # — Inicializar stats por defecto —
    stats = {
        "max_weight":   {"value": 0, "peso": 0, "reps": 0, "fecha": ""},
        "max_volume":   {"value": 0, "peso": 0, "reps": 0, "vol": 0, "fecha": ""},
        "best_1rm":     {"value": 0, "peso": 0, "reps": 0, "estimate": 0, "fecha": ""},
        "total_reps":   0,
        "total_volume": 0.0
    }

    # — Si hay datos, calcular records y totales —
    if flat:
        # 1) Peso máximo
        mw = max(flat, key=lambda s: s["peso"])
        stats["max_weight"].update({
            "value": mw["peso"],
            "peso":  mw["peso"],
            "reps":  mw["reps"],
            "fecha": mw["fecha"]
        })

        # 2) Volumen máximo
        mv = max(flat, key=lambda s: s["peso"] * s["reps"])
        vol = mv["peso"] * mv["reps"]
        stats["max_volume"].update({
            "value": vol,
            "peso":  mv["peso"],
            "reps":  mv["reps"],
            "vol":   vol,
            "fecha": mv["fecha"]
        })

        # 3) Mejor 1RM (Brzycki)
        def brzycki(s):
            return s["peso"] * 36 / (37 - s["reps"])
        b1 = max(flat, key=brzycki)
        est = brzycki(b1)
        stats["best_1rm"].update({
            "value":    est,
            "peso":     b1["peso"],
            "reps":     b1["reps"],
            "estimate": est,
            "fecha":    b1["fecha"]
        })

        # 4) Totales
        stats["total_reps"]   = sum(s["reps"] for s in flat)
        stats["total_volume"] = sum(s["peso"] * s["reps"] for s in flat)

    # — Serie temporal de 1RM por día —
    # agrupamos el mejor 1RM de cada fecha (solo dd/mm/YYYY)
    daily = {}
    for s in flat:
        fecha_dia = s["fecha"].split(" ")[0]
        val = brzycki(s)
        if fecha_dia not in daily or val > daily[fecha_dia]:
            daily[fecha_dia] = val
    # ordenamos fechas cronológicamente
    sorted_dates = sorted(
        daily.keys(),
        key=lambda d: datetime.strptime(d, "%d/%m/%Y")
    )
    rm_labels = sorted_dates
    rm_values = [ round(daily[d], 1) for d in sorted_dates ]

    from_plantilla = request.args.get("from_plantilla")
    if from_plantilla:
        back_url = url_for("plantillas.ver", clave=from_plantilla)
    else:
        back_url = url_for("ejercicios.lista")


    return render_template(
        "ejercicios/ver.html",
        ejercicio=ejercicio,
        clave=clave,
        historial_ej=historial_ej,
        stats=stats,
        rm_labels=rm_labels,
        rm_values=rm_values,
        back_url=back_url
    )



@ejercicios_bp.route("/nuevo", methods=["GET", "POST"])
@ejercicios_bp.route("/editar/<path:clave>", methods=["GET", "POST"])
@login_required
def gestionar(clave=None):
    """
    Crear ejercicios nuevos y editar existentes (especificando nombre, descripción opcional, grupo muscular principal y equipamiento)\n
    Editar un ejercicio actualiza su nombre en el Historial de Entrenamientos
    """
    srp     = sirope.Sirope()
    error   = None
    existente = None

    # 1) Si se pasa clave → estamos editando
    if clave:
        try:
            existente = srp.load(decode_oid(clave))
        except (AttributeError, ValueError, NameError):
            return redirect(url_for("ejercicios.lista", error_redirect="Ejercicio no encontrado."))

        if not existente or not existente.is_owner(current_user.get_id()):
            return redirect(url_for("ejercicios.lista", error_redirect="No tienes permiso para editar este ejercicio."))
 
    # 2) Valores iniciales del formulario
    if existente:
        nombre       = existente.nombre
        descripcion  = existente.descripcion
        grupo        = existente.grupo_muscular
        equipamiento = existente.equipamiento
    else:
        nombre = descripcion = grupo = equipamiento = ""

    # 3) Procesar POST
    if request.method == "POST":
        nombre       = request.form.get("nombre", "").strip()
        descripcion  = request.form.get("descripcion", "").strip()
        grupo        = request.form.get("grupo_muscular", "")
        equipamiento = request.form.get("equipamiento", "")

        # Validaciones
        if not nombre:
            error = "Debes introducir un nombre."
        elif len(nombre) > 55:
            error = "El nombre del ejercicio no puede superar los 55 caracteres."
        elif descripcion and len(descripcion) > 300:
            error = "La descripción no puede superar los 300 caracteres."
        
        if not error:
            dup = srp.find_first(
                Ejercicio,
                lambda e: e.is_owner(current_user.get_id())
                and e.nombre.lower() == nombre.lower()
                and (not existente or e.oid != existente.oid)
            )
            if dup:
                error = "Ya tienes otro ejercicio con ese nombre."

        if not error and grupo not in GRUPOS_VALIDOS:
            error = "Selecciona un grupo muscular válido."

        if not error and equipamiento not in EQUIPAMIENTOS_VALIDOS:
            error = "Selecciona un equipamiento válido."

        # Guardar si no hay error
        if not error:
            if existente:
                existente.nombre         = nombre
                existente.descripcion    = descripcion
                existente.grupo_muscular = grupo
                existente.equipamiento   = equipamiento
                srp.save(existente)
                return redirect(url_for("ejercicios.ver", clave=clave))
            else:
                nuevo = Ejercicio(
                    usuario_nombre=current_user.get_id(),
                    nombre=nombre,
                    descripcion=descripcion,
                    grupo_muscular=grupo,
                    equipamiento=equipamiento
                )
                srp.save(nuevo)
                return redirect(url_for("ejercicios.lista"))

    # 4) Renderizar formulario
    return render_template(
        "ejercicios/gestion_ejercicios.html",
        is_edit=bool(clave),
        clave=clave,
        nombre=nombre,
        descripcion=descripcion,
        grupo=grupo,
        equipamiento=equipamiento,
        error=error,
        grupos_validos=GRUPOS_VALIDOS,
        equipamientos_validos=EQUIPAMIENTOS_VALIDOS
    )



@ejercicios_bp.route("/eliminar/<path:clave>", methods=["POST"])
@login_required
def eliminar(clave):
    """
    Eliminar un ejercicio existente.\n
    Esta acción actualiza las plantillas que lo incluían, y en caso de tratarse de su último ejercicio, también se borran la plantillas en cuestión.\n
    También se actualizan sus entradas en el Historial de Entrenamientos, marcándolo como "(eliminado)" pero conservando los valores de las series realizadas.
    """

    srp = sirope.Sirope()
    
    try:
        ejercicio = srp.load(decode_oid(clave))
    except (AttributeError, ValueError, NameError):
        return redirect(url_for("ejercicios.lista"))

    if not ejercicio.is_owner(current_user.get_id()):
        return redirect(url_for("ejercicios.lista"))

    # Eliminar de las plantillas que lo contengan
    n_plant_borrada = 0
    for plant in srp.filter(
        Plantilla,
        lambda p: p.is_owner(current_user.get_id()) and clave in p.ejercicios
    ):
        # Borrar el ejercicio de la plantilla
        del plant.ejercicios[clave]
        if clave in plant.orden:
            plant.orden.remove(clave)

        # Si la plantilla queda vacía, la borramos; si no, la guardamos con el cambio
        if not plant.ejercicios:
            srp.delete(plant.oid)
            n_plant_borrada += 1
        else:
            srp.save(plant)

    # Notificar sobre las plantillas eliminadas como resultado si las hay
    if n_plant_borrada < 1:
        msj_plant_borrada = ""
    elif n_plant_borrada == 1:
        msj_plant_borrada = f"Se ha borrado 1 rutina porque '{ejercicio.nombre}' era su ultimo ejercicio"
    else:
        msj_plant_borrada = f"Se han borrado {n_plant_borrada} rutinas porque '{ejercicio.nombre}' era su ultimo ejercicio"

    # Actualizar los entrenamientos realizados donde aparezca
    for ent in srp.filter(
        EntrenamientoRealizado,
        lambda ent: ent.is_owner(current_user.get_id()) and clave in ent.ejercicios
    ):
        original_series = ent.ejercicios[clave]
        # Dejamos el nombre y series originales y se añade el indicador de "(eliminado)" en el front
        ent.ejercicios[clave] = {
            "nombre": ejercicio.nombre,
            "series": original_series
        }
        srp.save(ent)

    # Eliminar el ejercicio definitivamente
    srp.delete(ejercicio.oid)

    return redirect(url_for("ejercicios.lista", mensaje=msj_plant_borrada))
