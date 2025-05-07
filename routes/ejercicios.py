from flask import Blueprint, render_template, request, redirect, url_for, abort
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
    srp = sirope.Sirope()
    ejercicios_usuario = []

    # Capturar filtros
    grupo_filtro = request.args.get("grupo_muscular", "")
    equipamiento_filtro = request.args.get("equipamiento", "")

    for obj_id in srp.load_all_keys(Ejercicio):
        ejercicio = srp.load(obj_id)
        if ejercicio.usuario_nombre == current_user.get_id():
            if (not grupo_filtro or ejercicio.grupo_muscular == grupo_filtro) and (not equipamiento_filtro or ejercicio.equipamiento == equipamiento_filtro):
                clave = encode_oid(obj_id)
                ejercicios_usuario.append((clave, ejercicio))

    ejercicios_usuario.sort(key=lambda x: x[1].nombre.lower())

    return render_template("ejercicios/lista.html", ejercicios=ejercicios_usuario, grupo_filtro=grupo_filtro, equipamiento_filtro=equipamiento_filtro, grupos_validos=GRUPOS_VALIDOS, equipamientos_validos=EQUIPAMIENTOS_VALIDOS)



@ejercicios_bp.route("/nuevo", methods=["GET", "POST"])
@ejercicios_bp.route("/editar/<path:clave>", methods=["GET", "POST"])
@login_required
def gestionar(clave=None):
    srp     = sirope.Sirope()
    usuario = current_user.get_id()
    existente = None
    error = None

    # 1) Si se pasa clave → estamos editando
    if clave:
        try:
            oid = decode_oid(clave)
            existente = srp.load(oid)
        except:
            existente = None

        if not existente or existente.usuario_nombre != usuario:
            abort(404)

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
        
        if not error:
            dup = srp.find_first(Ejercicio, lambda e: e.usuario_nombre == usuario and e.nombre.lower() == nombre.lower() and (not existente or e.__oid__ != existente.__oid__))
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
                    usuario_nombre=usuario,
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
        is_edit=bool(existente),
        clave=clave,
        nombre=nombre,
        descripcion=descripcion,
        grupo=grupo,
        equipamiento=equipamiento,
        error=error,
        grupos_validos=GRUPOS_VALIDOS,
        equipamientos_validos=EQUIPAMIENTOS_VALIDOS
    )



@ejercicios_bp.route("/ver/<path:clave>")
@login_required
def ver(clave):
    srp = sirope.Sirope()
    obj_id = decode_oid(clave)
    ejercicio = srp.load(obj_id)

    if ejercicio.usuario_nombre != current_user.get_id():
        return redirect(url_for("ejercicios.lista"))

    clave_str = encode_oid(obj_id)
    resultados = []

    # — Recopilar sesiones donde aparece este ejercicio —
    for obj_id_r in srp.load_all_keys(EntrenamientoRealizado):
        ent = srp.load(obj_id_r)
        if ent.usuario_nombre == current_user.get_id() and clave_str in ent.ejercicios:
            datos = ent.ejercicios[clave_str]
            series = datos["series"] if isinstance(datos, dict) else datos

            resultados.append({
                "fecha":           ent.fecha,
                "entrenamiento":   ent.nombre,
                "observaciones":   ent.observaciones,
                "series":          series
            })

    resultados.sort(key=lambda x: datetime.strptime(x["fecha"], "%d/%m/%Y %H:%M:%S"), reverse=True)

    # — Aplanar todas las series válidas para este ejercicio —
    flat = []
    for sesion in resultados:
        for s in sesion["series"]:
            try:
                peso = float(s["peso"])
                reps = int(s["reps"])
            except:
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

    return render_template(
        "ejercicios/ver.html",
        ejercicio=ejercicio,
        clave=clave,
        resultados=resultados,
        stats=stats,
        rm_labels=rm_labels,
        rm_values=rm_values
    )



@ejercicios_bp.route("/eliminar/<path:clave>", methods=["POST"])
@login_required
def eliminar(clave):
    srp = sirope.Sirope()
    obj_id = decode_oid(clave)
    ejercicio = srp.load(obj_id)

    if ejercicio.usuario_nombre != current_user.get_id():
        return redirect(url_for("ejercicios.lista"))

    clave_str = encode_oid(obj_id)

    # Eliminar de las plantillas
    for obj_id_p in srp.load_all_keys(Plantilla):
        p = srp.load(obj_id_p)
        if p.usuario_nombre == current_user.get_id():
            if clave_str in p.ejercicios:
                del p.ejercicios[clave_str]
            if clave_str in p.orden:
                p.orden.remove(clave_str)

            if not p.ejercicios:
                srp.delete(obj_id_p)
            else:
                srp.save(p)

    # Actualizar los entrenamientos realizados que lo contengan
    for obj_id_r in srp.load_all_keys(EntrenamientoRealizado):
        ent = srp.load(obj_id_r)
        if ent.usuario_nombre == current_user.get_id() and clave_str in ent.ejercicios:
            original_series = ent.ejercicios[clave_str]
            ent.ejercicios[clave_str] = {
                "nombre": ejercicio.nombre,
                "series": original_series
            }
            srp.save(ent)

    # Eliminar el ejercicio
    srp.delete(obj_id)

    return redirect(url_for("ejercicios.lista"))