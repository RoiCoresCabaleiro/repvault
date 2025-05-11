from flask import Blueprint, render_template, url_for, redirect
from flask_login import current_user, login_required
import sirope
from datetime import datetime, timedelta
from collections import Counter

from models.entrenamiento_realizado import EntrenamientoRealizado

home_bp = Blueprint("home", __name__, url_prefix="")


@home_bp.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("home.dashboard"))
    
    return render_template("home.html")


@home_bp.route("/home")
@login_required
def dashboard():
    srp = sirope.Sirope()

    # --- 1) Fechas de hoy y hace 8 semanas ---
    hoy = datetime.today().date()
    ocho_semanas_atras = hoy - timedelta(weeks=8)

    # --- 2) Seleccionar sesiones del usuario en ese rango ---
    sesiones_rango = []
    for oid in srp.load_all_keys(EntrenamientoRealizado):
        ent = srp.load(oid)
        if ent.usuario_nombre != current_user.get_id():
            continue
        fecha_dt = datetime.strptime(ent.fecha, "%d/%m/%Y %H:%M:%S").date()
        if fecha_dt >= ocho_semanas_atras:
            sesiones_rango.append(fecha_dt)

    # --- 3) Función auxiliar para calcular el lunes de la semana de una fecha ---
    def lunes_de(fecha):
        return fecha - timedelta(days=fecha.weekday())

    # --- 4) Contar entrenamientos por el lunes de su semana ---
    contador = Counter(lunes_de(s) for s in sesiones_rango)

    # --- 5) Construir etiquetas y valores de las últimas 8 semanas ---
    # Lunes de la semana actual
    lunes_actual = hoy - timedelta(days=hoy.weekday())

    week_labels = []
    week_counts = []
    for i in range(7, -1, -1):  # desde 7 semanas atrás hasta la actual
        semana = lunes_actual - timedelta(weeks=i)
        week_labels.append(semana.strftime("%-d/%-m"))  # "17/3"
        week_counts.append(contador.get(semana, 0))

    max_count = max(week_counts) if week_counts else 0

    return render_template(
        "home.html",
        week_labels=week_labels,
        week_counts=week_counts,
        max_count=max_count
    )
