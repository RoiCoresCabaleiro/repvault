from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_user, logout_user, login_required
import sirope

from models.usuario import Usuario
from routes.utils import importar_ejercicios_por_defecto, importar_plantillas_por_defecto

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = request.args.get("error")
    nombre = ""
    if request.method == "POST":
        srp = sirope.Sirope()
        nombre = request.form.get("nombre", "").strip()
        contraseña = request.form.get("contraseña", "")

        usuario = Usuario.find(srp, nombre)
        if usuario and usuario.comprobar_contraseña(contraseña):
            login_user(usuario)
            return redirect(url_for("home.home"))
        else:
            error = "Usuario o contraseña incorrectos."

    return render_template("auth.html", mode="login", error=error, nombre=nombre)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    error = None
    nombre = ""
    if request.method == "POST":
        srp = sirope.Sirope()
        nombre = request.form.get("nombre", "").strip()
        contraseña = request.form.get("contraseña", "")

        # Validaciones
        if not nombre:
            error = "El nombre de usuario no puede estar vacío."
        elif Usuario.find(srp, nombre):
            error = "Este nombre de usuario ya existe."
        else:
            nuevo_usuario = Usuario(nombre, contraseña)
            srp.save(nuevo_usuario)

            importar_ejercicios_por_defecto(nuevo_usuario.get_id())

            importar_plantillas_por_defecto(nuevo_usuario.get_id())

            login_user(nuevo_usuario)
            return redirect(url_for("home.home"))

    return render_template("auth.html", mode="register", error=error, nombre=nombre)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home.home"))
