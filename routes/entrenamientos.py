from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
import sirope
from datetime import datetime
from calendar import monthrange

from models.ejercicio import Ejercicio
from models.entrenamiento_en_curso import EntrenamientoEnCurso
from models.entrenamiento_realizado import EntrenamientoRealizado
from routes.utils import encode_oid, decode_oid, GRUPOS_VALIDOS, EQUIPAMIENTOS_VALIDOS, build_entrenamiento_context, serie_valida

entrenamientos_bp = Blueprint("entrenamientos", __name__, url_prefix="/entrenamiento")


@entrenamientos_bp.route("/iniciar", defaults={"clave": None}, methods=["POST"])
@entrenamientos_bp.route("/iniciar/<path:clave>", methods=["POST"])
@login_required
def iniciar(clave):
    """
    Iniciar un entrenamiento.\n
    Se crea un EntrenamientoEnCurso a partir de una Plantilla, en el que se podrá registrar el progreso
    a lo largo de un entrenamiento y se podrán hacer todo tipo de cambios en tiempo real que no afectan
    a la plantilla de origen.\n
    Tambien se puede iniciar un entrenamiento vacío sin basarse en ninguna plantilla.
    """
    srp = sirope.Sirope()
    
    # Eliminar posibles entrenamientos en curso existentes (erroneos)
    for ent in srp.filter(
        EntrenamientoEnCurso,
        lambda e: e.is_owner(current_user.get_id())
    ):
        srp.delete(ent.oid)

    if clave:
        try:
            plantilla = srp.load(decode_oid(clave))
        except (AttributeError, ValueError, NameError):
            return redirect(url_for("plantillas.lista", error_redirect="Rutina no encontrada."))

        if not plantilla.is_owner(current_user.get_id()):
            return redirect(url_for("plantillas.lista", error_redirect="No tienes permiso para iniciar un entrenamiento con esta rutina."))

        # Entrenamiento basado en la plantilla
        nuevo = EntrenamientoEnCurso.from_plantilla(plantilla, current_user.get_id())
    else:
        # Entrenamiento completamente vacío
        nuevo = EntrenamientoEnCurso.empty(current_user.get_id())

    srp.save(nuevo)
    return redirect(url_for("entrenamientos.actual"))



@entrenamientos_bp.route("/actual", methods=["GET", "POST"])
@login_required
def actual():
    """
    Gestiona el progreso del usuario en el EntrenamientoEnCurso, guardando a cada paso el estado actual del mismo.\n
    También maneja todos los cambios que se pueden hacer desde la propia vista actual (cambiar el nombre y las observaciones, 
    añadir o quitar ejercicios (pudiendo filtrarlos para facilitar la busqueda) y añadir o quitar series a cada ejercicio).\n
    Se manejan desde esta ruta tambíen las validaciones previas a finalizar el entrenamiento
    """
    srp = sirope.Sirope()

    # — Cargar en curso —
    entrenamiento = srp.find_first(
        EntrenamientoEnCurso,
        lambda e: e.is_owner(current_user.get_id())
    )
    if not entrenamiento:
        return redirect(url_for("home.home"))

    # — Reconstruir contexto —
    ejercicios_usuario, ultimos_valores, grupo_filtro, equipamiento_filtro, ejercicios_disponibles = build_entrenamiento_context(entrenamiento)
    
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
            return redirect(url_for("entrenamientos.actual", grupo_filtro=grupo_filtro, equipamiento_filtro=equipamiento_filtro))

        # — 4) Agregar ejercicio — preservando filtros
        add = request.form.get("agregar")
        if add and add not in entrenamiento.ejercicios:
            entrenamiento.ejercicios[add] = [{"peso": "", "reps": "", "hecha": False}]
            srp.save(entrenamiento)
            return redirect(url_for("entrenamientos.actual", grupo_filtro=grupo_filtro, equipamiento_filtro=equipamiento_filtro))

        # — 5) Modificar series —
        accion = request.form.get("modificar_series")
        if accion:
            tipo, soid = accion.split("-")
            if soid in entrenamiento.ejercicios:
                if tipo == "añadir"and len(entrenamiento.ejercicios[soid]) < 20:
                    entrenamiento.ejercicios[soid].append({"peso": "", "reps": "", "hecha": False})
                elif tipo == "quitar" and len(entrenamiento.ejercicios[soid]) > 1:
                    entrenamiento.ejercicios[soid].pop()
                srp.save(entrenamiento)

        # — 6) Validación previa a “Terminar Entrenamiento” = "validar" —
        error = None
        if "validar" in request.form: 
            show_confirm = False
            if not entrenamiento.nombre_plantilla:
                error = "El nombre del entrenamiento no puede estar vacío."
            elif len(entrenamiento.nombre_plantilla) > 40:
                error = "El nombre del entrenamiento no puede superar los 40 caracteres."
            elif entrenamiento.observaciones and len(entrenamiento.observaciones) > 500:
                error = "Las observaciones no pueden superar los 500 caracteres."
            if not error:
                any_done = any(
                    serie_valida(s)
                    for series in entrenamiento.ejercicios.values()
                    for s in series
                )
                if not any_done:
                    error = "Debes completar al menos una serie válida para finalizar el entrenamiento."
                else:
                    show_confirm = True  # Mostrar mensaje de confirmacion de Terminar Entrenamiento

            srp.save(entrenamiento)

            # Renderizar con error de validacion o con confirmacion de Terminar Entrenamiento
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

    # GET inicial o POST diferente a Terminar Entrenamiento
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
        show_confirm=False
    )



@entrenamientos_bp.route("/finalizar", methods=["POST"])
@login_required
def finalizar():
    """
    Terminar un entrenamiento.\n
    Se crea un EntrenamientoRealizado a partir de los datos procesados del EntrenamientoEnCurso del usuario.\n
    Además se actualiza la fecha de ultima vez de la plantilla a partir de la que se creó el EntrenamientoEnCurso y
    se actualizan las ultimas series de cada ejercicio.\n
    Se borra el EntrenamientoEnCurso sobrante.
    """
    srp = sirope.Sirope()
    
    # — Cargar entrenamiento en curso —
    entrenamiento = srp.find_first(
        EntrenamientoEnCurso,
        lambda e: e.is_owner(current_user.get_id())
    )
    if not entrenamiento:
        return redirect(url_for("home.home"))

    # — 1) Recuperar nombre y observaciones desde el formulario —
    entrenamiento.nombre_plantilla = request.form.get("nombre_plantilla", entrenamiento.nombre_plantilla).strip()
    entrenamiento.observaciones = request.form.get("observaciones", entrenamiento.observaciones).strip()

    # — 2) Filtrar sólo ejercicios con al menos una serie hecha y válida —
    ejercicios_filtrados = {
        soid: [s for s in series if serie_valida(s)]
        for soid, series in entrenamiento.ejercicios.items()
        if any(serie_valida(s) for s in series)
    }

    # — 3) Pasar a histórico con cálculo de duración —
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

    # — 4) Actualizar última vez de la plantilla origen si la hay— 
    if entrenamiento.plantilla_soid:
        try:
            p = srp.load(decode_oid(entrenamiento.plantilla_soid))
            if p and p.is_owner(current_user.get_id()):
                p.ultima_vez = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                srp.save(p)
        except (ValueError, NameError, AttributeError):
            pass


    # — 5) Actualizar últimas series de cada ejercicio —
    ej_oids = [decode_oid(soid) for soid in ejercicios_filtrados]
    ej_iter = srp.multi_load(ej_oids)
    
    for soid, ejercicio in zip(ejercicios_filtrados, ej_iter):
        if ejercicio:
            # Cada serie solo contiene peso y reps
            series_filtradas = [
                {"peso": s["peso"], "reps": s["reps"]}
                for s in ejercicios_filtrados[soid]
            ]
            ejercicio.ultimas_series = series_filtradas
            srp.save(ejercicio)
    
    # — 6) Borrar entrenamiento en curso —
    srp.delete(entrenamiento.oid)

    return redirect(url_for("entrenamientos.historial"))



@entrenamientos_bp.route("/cancelar", methods=["POST"])
@login_required
def cancelar():
    """
    Cancelar entrenamiento sin guardar y salir\n
    Se borra el EntrenamientoEnCurso sobrante
    """
    srp = sirope.Sirope()

    ent = srp.find_first(
        EntrenamientoEnCurso,
        lambda e: e.is_owner(current_user.get_id())
    )
    if ent:
        srp.delete(ent.oid)

    return redirect(url_for("plantillas.lista"))



@entrenamientos_bp.route("/historial")
@login_required
def historial():
    """
    Generar Historial de Entrenamientos a partir de los EntrenamientoRealizado del usuario\n
    Construir calendario con estos datos.
    """
    srp = sirope.Sirope()

    # Cargar entrenamientos realizados y ordenar por fecha (más reciente primero)
    realizados = sorted(
        srp.filter(
            EntrenamientoRealizado,
            lambda e: e.is_owner(current_user.get_id())
        ),
        key=lambda x: datetime.strptime(x.fecha, "%d/%m/%Y %H:%M:%S"),
        reverse=True
    )

    # Agrupar por día
    agrupados = {}
    for ent in realizados:
        fecha_sola = ent.fecha.split()[0]
        agrupados.setdefault(fecha_sola, []).append(ent)

    # Nombres de ejercicios activos
    ejercicios_nombres = {
        encode_oid(e.oid): e.nombre
        for e in srp.filter(
            Ejercicio,
            lambda e: e.is_owner(current_user.get_id())
        )
    }

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
