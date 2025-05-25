from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
import sirope
from datetime import datetime
from calendar import monthrange

from models.ejercicio import Ejercicio
from models.entrenamiento_en_curso import EntrenamientoEnCurso
from models.entrenamiento_realizado import EntrenamientoRealizado
from routes.utils import encode_oid, decode_oid, GRUPOS_VALIDOS, EQUIPAMIENTOS_VALIDOS

entrenamientos_bp = Blueprint("entrenamientos", __name__, url_prefix="/entrenamiento")



@entrenamientos_bp.route("/iniciar/<path:clave>", methods=["POST"])
@login_required
def iniciar(clave):
    srp = sirope.Sirope()
    plantilla = srp.load(decode_oid(clave))

    if not plantilla.is_owner(current_user.get_id()):
        return redirect(url_for("plantillas.lista"))

    # Eliminar previo en curso
    for oid_exist in srp.load_all_keys(EntrenamientoEnCurso):
        e = srp.load(oid_exist)
        if e.is_owner(current_user.get_id()):
            srp.delete(oid_exist)

    nuevo = EntrenamientoEnCurso(
        usuario_nombre=current_user.get_id(),
        plantilla_soid=clave,
        nombre_plantilla=plantilla.nombre,
        observaciones=plantilla.observaciones,
        ejercicios_plantilla=[(soid, plantilla.ejercicios[soid]) for soid in plantilla.orden]
    )
    srp.save(nuevo)
    return redirect(url_for("entrenamientos.actual"))



@entrenamientos_bp.route("/actual", methods=["GET", "POST"])
@login_required
def actual():
    srp = sirope.Sirope()
    error = None
    show_confirm = False

    # — Cargar en curso —
    entrenamiento = None
    for oid in srp.load_all_keys(EntrenamientoEnCurso):
        e = srp.load(oid)
        if e.is_owner(current_user.get_id()):
            entrenamiento = e
            break
    if not entrenamiento:
        return redirect(url_for("home.home"))

    # — Reconstruir contexto —
    ejercicios_usuario, ultimos_valores, grupo_filtro, equipamiento_filtro, ejercicios_disponibles = build_ejercicio_context(srp, entrenamiento)

    if request.method == "POST":
        # — 1) Actualizar nombre y observaciones —
        entrenamiento.nombre_plantilla = request.form.get("nombre_plantilla", entrenamiento.nombre_plantilla).strip()
        entrenamiento.observaciones = request.form.get("observaciones", entrenamiento.observaciones).strip()

        # — 2) Guardar cada serie del formulario —
        for soid, series in entrenamiento.ejercicios.items():
            for i, serie in enumerate(series):
                peso_raw = request.form.get(f"peso_{soid}_{i}", "").strip()
                reps_raw = request.form.get(f"reps_{soid}_{i}", "").strip()
                try:
                    p = round(float(peso_raw), 2)
                    serie["peso"] = str(int(p)) if p.is_integer() else f"{p:.2f}"
                except (ValueError, TypeError):
                    serie["peso"] = ""
                try:
                    serie["reps"] = int(reps_raw)
                except (ValueError, TypeError):
                    serie["reps"] = ""
                serie["hecha"] = f"hecha_{soid}_{i}" in request.form

        # — 3) Quitar ejercicio — preservando filtros
        eliminar = request.form.get("eliminar_ejercicio")
        if eliminar and eliminar in entrenamiento.ejercicios:
            del entrenamiento.ejercicios[eliminar]
            srp.save(entrenamiento)
            return redirect(url_for("entrenamientos.actual", grupo_muscular=grupo_filtro, equipamiento=equipamiento_filtro))

        # — 4) Agregar ejercicio — preservando filtros
        add = request.form.get("agregar")
        if add and add not in entrenamiento.ejercicios:
            entrenamiento.ejercicios[add] = [{"peso": "", "reps": "", "hecha": False}]
            srp.save(entrenamiento)
            return redirect(url_for("entrenamientos.actual", grupo_muscular=grupo_filtro, equipamiento=equipamiento_filtro))

        # — 5) Modificar series —
        accion = request.form.get("modificar_series")
        if accion:
            tipo, soid = accion.split("-")
            if soid in entrenamiento.ejercicios:
                if tipo == "añadir":
                    entrenamiento.ejercicios[soid].append({"peso": "", "reps": "", "hecha": False})
                elif tipo == "quitar" and len(entrenamiento.ejercicios[soid]) > 1:
                    entrenamiento.ejercicios[soid].pop()

        # — 6) Validación previa a “Terminar” —
        error = None
        if "validar" in request.form:
            # Validar nombre
            if not entrenamiento.nombre_plantilla:
                error = "El nombre del entrenamiento no puede estar vacío."
            elif len(entrenamiento.nombre_plantilla) > 50:
                error = "El nombre del entrenamiento no puede superar los 50 caracteres."
            elif entrenamiento.observaciones and len(entrenamiento.observaciones) > 500:
                error = "Las observaciones no pueden superar los 500 caracteres."
            if not error:
                # Validar al menos una serie válida hecha
                any_done = any(
                    s.get("hecha") and s.get("peso") and s.get("reps")
                    for series in entrenamiento.ejercicios.values()
                    for s in series
                )
                if not any_done:
                    error = "Debes completar al menos una serie válida para finalizar el entrenamiento."
                else:
                    show_confirm = True

            # Guardar cambios intermedios
            srp.save(entrenamiento)

            # Renderizar con error o bandera de confirmación
            return render_template(
                "entrenamientos/actual.html",
                entrenamiento=entrenamiento,
                ejercicios=ejercicios_usuario,
                ejercicios_disponibles=ejercicios_disponibles,
                grupos_validos=GRUPOS_VALIDOS,
                equipamientos_validos=EQUIPAMIENTOS_VALIDOS,
                grupo_filtro=grupo_filtro,
                equipamiento_filtro=equipamiento_filtro,
                ultimos_valores=ultimos_valores,
                error=error,
                show_confirm=show_confirm
            )

        # — 7) Guardar cambios intermedios (otras acciones) —
        srp.save(entrenamiento)

    # GET inicial o POST sin validar
    return render_template(
        "entrenamientos/actual.html",
        entrenamiento=entrenamiento,
        ejercicios=ejercicios_usuario,
        ejercicios_disponibles=ejercicios_disponibles,
        grupos_validos=GRUPOS_VALIDOS,
        equipamientos_validos=EQUIPAMIENTOS_VALIDOS,
        grupo_filtro=grupo_filtro,
        equipamiento_filtro=equipamiento_filtro,
        ultimos_valores=ultimos_valores,
        error=error,
        show_confirm=show_confirm
    )


@entrenamientos_bp.route("/finalizar", methods=["POST"])
@login_required
def finalizar():
    srp = sirope.Sirope()
    
    # — Cargar y actualizar entrenamiento en curso —
    entrenamiento = None
    for oid in srp.load_all_keys(EntrenamientoEnCurso):
        e = srp.load(oid)
        if e.is_owner(current_user.get_id()):
            entrenamiento = e
            break
    if not entrenamiento:
        return redirect(url_for("home.home"))

    # — 1) Actualizar nombre y observaciones desde el formulario —
    entrenamiento.nombre_plantilla = request.form.get("nombre_plantilla", entrenamiento.nombre_plantilla).strip()
    entrenamiento.observaciones = request.form.get("observaciones", entrenamiento.observaciones).strip()

    # — 2) Validar nombre no vacío en "guardar definitivo" —
    error = None
    if not entrenamiento.nombre_plantilla:
        error = "El nombre del entrenamiento no puede estar vacío."
    elif len(entrenamiento.nombre_plantilla) > 50:
        error = "El nombre del entrenamiento no puede superar los 50 caracteres"
    elif entrenamiento.observaciones and len(entrenamiento.observaciones) > 500:
        error = "Las observaciones no pueden superar los 500 caracteres."
    if error:    
        # — Reconstruir contexto —
        ejercicios_usuario, ultimos_valores, grupo_filtro, equipamiento_filtro, ejercicios_disponibles = build_ejercicio_context(srp, entrenamiento)

        return render_template(
            "entrenamientos/actual.html",
            entrenamiento=entrenamiento,
            ejercicios=ejercicios_usuario,
            ejercicios_disponibles=ejercicios_disponibles,
            grupos_validos=GRUPOS_VALIDOS,
            equipamientos_validos=EQUIPAMIENTOS_VALIDOS,
            grupo_filtro=grupo_filtro,
            equipamiento_filtro=equipamiento_filtro,
            ultimos_valores=ultimos_valores,
            error=error
        )

    # — 3) Actualizar las series desde el formulario —
    for soid, series in entrenamiento.ejercicios.items():
        for i, serie in enumerate(series):
            peso_raw = request.form.get(f"peso_{soid}_{i}", "").strip()
            reps_raw = request.form.get(f"reps_{soid}_{i}", "").strip()
            try:
                p = round(float(peso_raw), 2)
                serie["peso"] = str(int(p)) if p.is_integer() else f"{p:.2f}"
            except (ValueError, TypeError):
                serie["peso"] = ""
            try:
                serie["reps"] = int(reps_raw)
            except (ValueError, TypeError):
                serie["reps"] = ""

            serie["hecha"] = f"hecha_{soid}_{i}" in request.form

    # — 4) Filtrar sólo ejercicios con al menos una serie hecha y válida —
    def serie_valida(s):
        try:
            p = float(s["peso"])
            r = int(s["reps"])
        except (KeyError, ValueError, TypeError):
            return False
        return s.get("hecha") and (0 <= p <= 1000) and (1 <= r <= 100)

    ejercicios_filtrados = {soid: [s for s in series if serie_valida(s)] for soid, series in entrenamiento.ejercicios.items()}
    ejercicios_filtrados = {k: v for k, v in ejercicios_filtrados.items() if v}

    if not ejercicios_filtrados:
        error="Debes completar al menos una serie válida para finalizar el entrenamiento."
        # — Reconstruir contexto —
        ejercicios_usuario, ultimos_valores, grupo_filtro, equipamiento_filtro, ejercicios_disponibles = build_ejercicio_context(srp, entrenamiento)

        return render_template(
            "entrenamientos/actual.html",
            entrenamiento=entrenamiento,
            ejercicios=ejercicios_usuario,
            ejercicios_disponibles=ejercicios_disponibles,
            grupos_validos=GRUPOS_VALIDOS,
            equipamientos_validos=EQUIPAMIENTOS_VALIDOS,
            grupo_filtro=grupo_filtro,
            equipamiento_filtro=equipamiento_filtro,
            ultimos_valores=ultimos_valores,
            error=error
        )

    # — 5) Pasar a histórico con cálculo de duración y últimas series y borrar entrenamiento en curso —
    inicio = datetime.strptime(entrenamiento.inicio, "%d/%m/%Y %H:%M:%S")
    fin = datetime.now()
    dur = int((fin - inicio).total_seconds() // 60)

    realizado = EntrenamientoRealizado(
        usuario_nombre=current_user.get_id(),
        nombre=entrenamiento.nombre_plantilla,
        observaciones=entrenamiento.observaciones,
        ejercicios=ejercicios_filtrados,
        fecha=entrenamiento.inicio,
        duracion=dur
    )
    srp.save(realizado)

    # — Actualizar última vez de la plantilla origen — 
    try:
        p = srp.load(decode_oid(entrenamiento.plantilla_soid))
        if p and p.is_owner(current_user.get_id()):
            p.ultima_vez = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            srp.save(p)
    except (ValueError, NameError, AttributeError):
        pass

    # — Actualizar últimas series de cada ejercicio —
    for soid in ejercicios_filtrados:
        try:
            ej = srp.load(decode_oid(soid))
            ej.ultimas_series = ejercicios_filtrados[soid]
            srp.save(ej)
        except (ValueError, NameError, AttributeError):
            pass

    srp.delete(entrenamiento.oid)
    return redirect(url_for("entrenamientos.historial"))


# — Metodo auxiliar para reconstruir listas y filtros de ejercicios en actual() y finalizar() —
def build_ejercicio_context(srp, entrenamiento):
    # — 1) Ejercicios del usuario —
    ejercicios_usuario = []
    for oid in srp.load_all_keys(Ejercicio):
        e = srp.load(oid)
        if e.is_owner(current_user.get_id()):
            ejercicios_usuario.append((encode_oid(oid), e))
    ejercicios_usuario.sort(key=lambda x: x[1].nombre.lower())

    # — 2) Últimas series —
    ultimos_valores = {}
    for soid in entrenamiento.ejercicios:
        try:
            ej = srp.load(decode_oid(soid))
            ultimos_valores[soid] = getattr(ej, "ultimas_series", [])
        except (ValueError, NameError, AttributeError):
            ultimos_valores[soid] = []

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



@entrenamientos_bp.route("/cancelar", methods=["POST"])
@login_required
def cancelar():
    srp = sirope.Sirope()
    for oid in srp.load_all_keys(EntrenamientoEnCurso):
        e = srp.load(oid)
        if e.is_owner(current_user.get_id()):
            srp.delete(oid)
            break

    return redirect(url_for("plantillas.lista"))



@entrenamientos_bp.route("/historial")
@login_required
def historial():
    srp = sirope.Sirope()
    realizados = []
    for oid in srp.load_all_keys(EntrenamientoRealizado):
        e = srp.load(oid)
        if e.is_owner(current_user.get_id()):
            realizados.append(e)

    #Ordenar por fecha (más reciente primero)
    realizados.sort(key=lambda x: datetime.strptime(x.fecha, "%d/%m/%Y %H:%M:%S"), reverse=True)

    # Agrupar por día
    agrupados = {}
    for ent in realizados:
        fecha_sola = ent.fecha.split()[0]
        agrupados.setdefault(fecha_sola, []).append(ent)

    # Nombres de ejercicios activos
    ejercicios_nombres = {}
    for oid in srp.load_all_keys(Ejercicio):
        e = srp.load(oid)
        if e.is_owner(current_user.get_id()):
            ejercicios_nombres[encode_oid(oid)] = e.nombre

    # Obtener mes y año desde GET, o usar los actuales
    try:
        mes = int(request.args.get("mes", 0))
        año = int(request.args.get("año", 0))
        if not 1 <= mes <= 12:
            raise ValueError
    except (ValueError, TypeError):
        hoy = datetime.today()
        mes, año = hoy.month, hoy.year

    dias_mes = monthrange(año, mes)[1]  # total días del mes

    # Crear estructura para saber qué días tienen entrenamientos
    dias_con_entreno = set()
    for f_str in agrupados:
        try:
            dt = datetime.strptime(f_str, "%d/%m/%Y")
            if dt.year == año and dt.month == mes:
                dias_con_entreno.add(dt.day)
        except (ValueError, TypeError):
            pass

    # Calcular día de la semana del 1er día (0=lunes, 6=domingo)
    primer_dia_semana = datetime(año, mes, 1).weekday()

    # Construir filas del calendario
    calendario_filas, fila = [], []

    for _ in range(primer_dia_semana):
        fila.append(None)
    for d in range(1, dias_mes+1):
        fila.append({"numero": d, "activo": d in dias_con_entreno})
        if len(fila) == 7:
            calendario_filas.append(fila); fila = []
    if fila:
        while len(fila) < 7: fila.append(None)
        calendario_filas.append(fila)

    # Nombre del mes en castellano
    MESES_ES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
    mes_nombre = MESES_ES[mes - 1]

    # Obtener fecha actual para restaurar el calendario al mes actual
    hoy = datetime.today()
    hoy_mes, hoy_año = hoy.month, hoy.year

    return render_template("entrenamientos/historial.html", historial=agrupados, ejercicios_nombres=ejercicios_nombres, calendario_filas=calendario_filas, mes=mes, año=año, mes_nombre=mes_nombre, hoy_mes=hoy_mes, hoy_año=hoy_año)
