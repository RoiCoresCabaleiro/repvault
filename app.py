from flask import Flask, redirect, url_for
from flask_login import LoginManager
import sirope
import json

from routes.auth import auth_bp
from routes.ejercicios import ejercicios_bp
from routes.plantillas import plantillas_bp
from routes.entrenamientos import entrenamientos_bp
from routes.home import home_bp

from models.usuario import Usuario

app = Flask(__name__)

app.config.from_file("secretkey.json", load=json.load)

srp = sirope.Sirope()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.find(srp, user_id)

# — Handler para accesos no autenticados —
@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for("auth.login", error="Debes iniciar sesión para acceder a esa página."))

# Registrar Blueprints
app.register_blueprint(home_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(ejercicios_bp)
app.register_blueprint(plantillas_bp)
app.register_blueprint(entrenamientos_bp)

if __name__ == "__main__":
    app.run(debug=True)              #app.run(host='0.0.0.0', port=5000, debug=True)
