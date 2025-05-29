from flask import Blueprint, render_template, url_for, redirect
from flask_login import current_user, login_required
import sirope
from datetime import datetime, timedelta
from collections import Counter

from models.entrenamiento_realizado import EntrenamientoRealizado

home_bp = Blueprint("home", __name__)



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
    entrenamientos_usuario = srp.filter(
        EntrenamientoRealizado,
        lambda e: e.is_owner(current_user.get_id())
    )
    sesiones_rango = [
        datetime.strptime(ent.fecha, "%d/%m/%Y %H:%M:%S").date()
        for ent in entrenamientos_usuario
        if datetime.strptime(ent.fecha, "%d/%m/%Y %H:%M:%S").date() >= ocho_semanas_atras
    ]

    # --- 3) Función auxiliar para calcular el lunes de la semana de una fecha ---
    def lunes_de(fecha):
        return fecha - timedelta(days=fecha.weekday())

    # --- 4) Contar entrenamientos por el lunes de su semana ---
    contador = Counter(lunes_de(s) for s in sesiones_rango)

    # --- 5) Construir etiquetas y valores de las últimas 8 semanas ---
    # Lunes de la semana actual
    lunes_actual = hoy - timedelta(days=hoy.weekday())

    week_labels, week_counts = [], []
    for i in range(7, -1, -1):  # desde 7 semanas atrás hasta la actual
        semana = lunes_actual - timedelta(weeks=i)
        week_labels.append(f"{semana.day}/{semana.month}")  # "17/3"
        week_counts.append(contador.get(semana, 0))

    max_count = max(week_counts, default=0)

    entrenamientos_totales = sum(
        1 for _ in srp.filter(
            EntrenamientoRealizado,
            lambda e: e.is_owner(current_user.get_id())
        )
    )

    return render_template(
        "home.html",
        week_labels=week_labels,
        week_counts=week_counts,
        max_count=max_count,
        entrenamientos_totales=entrenamientos_totales
    )
