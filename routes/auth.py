from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_user, logout_user, login_required
import sirope

from models.usuario import Usuario
from routes.utils import importar_ejercicios_por_defecto, importar_plantillas_por_defecto, generar_entrenamientos_historicos

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")



@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Registrar nuevo Usuario y cargar ejercicios y rutinas por defecto\n
    IMPORTANTE: Crear un usuario con el nombre "prueba", cargará ademas una serie de EntrenamientoRealizado
    que será util para comprobar el funcionamiento completo del sistema"""

    error = None
    nombre = ""
    if request.method == "POST":
        srp = sirope.Sirope()
        nombre = request.form.get("nombre", "").strip()
        contraseña = request.form.get("contraseña", "")
        confirma = request.form.get("confirma", "")

        # Validaciones
        if not nombre:
            error = "Por favor, introduce un nombre de usuario."
        elif Usuario.find(srp, nombre):
            error = "Este nombre de usuario ya existe."
        elif len(nombre) > 20:
            error = "El nombre de usuario no puede superar los 20 caracteres."
        elif not contraseña:
            error = "Por favor, introduce una contraseña."
        elif len(contraseña) < 4:
            error = "La contraseña debe tener al menos 4 caracteres."
        elif contraseña != confirma:
            error = "Las contraseñas no coinciden."

        if not error:
            nuevo_usuario = Usuario(nombre, contraseña)
            srp.save(nuevo_usuario)

            importar_ejercicios_por_defecto(nuevo_usuario.get_id())
            importar_plantillas_por_defecto(nuevo_usuario.get_id())

            # Crear un usuario "prueba" para probar el funcionamiento de la vista de historial de entrenamientos y de ejercicios
            if nuevo_usuario.get_id() == "prueba":
                generar_entrenamientos_historicos(nuevo_usuario.nombre)

            login_user(nuevo_usuario)
            return redirect(url_for("home.home"))

    return render_template("auth.html", mode="register", error=error, nombre=nombre)



@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Iniciar sesion de Usuario registrado previamente"""

    error = request.args.get("error")
    nombre = ""
    if request.method == "POST":
        srp = sirope.Sirope()
        nombre = request.form.get("nombre", "").strip()
        contraseña = request.form.get("contraseña", "")

        # Validaciones
        if not nombre:
            error = "Por favor, introduce un nombre de usuario."
        elif not contraseña:
            error = "Por favor, introduce una contraseña."
        else:
            usuario = Usuario.find(srp, nombre)
            if usuario and usuario.comprobar_contraseña(contraseña):
                login_user(usuario)
                return redirect(url_for("home.home"))
            else:
                error = "Usuario o contraseña incorrectos."

    return render_template("auth.html", mode="login", error=error, nombre=nombre)



@auth_bp.route("/logout")
@login_required
def logout():
    """Cerrar sesión de Usuario "loggeado" """
    
    logout_user()
    return redirect(url_for("home.home"))
