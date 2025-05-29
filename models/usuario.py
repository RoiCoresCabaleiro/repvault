import flask_login
from werkzeug.security import generate_password_hash, check_password_hash
import sirope

class Usuario(flask_login.UserMixin):
    def __init__(self, nombre: str, contraseña: str):
        self._nombre = nombre
        self._contraseña_hash = generate_password_hash(contraseña)

    @property
    def nombre(self):
        return self._nombre

    def get_id(self) -> str:
        return self.nombre
    
    def comprobar_contraseña(self, contraseña: str) -> bool:
        return check_password_hash(self._contraseña_hash, contraseña)

    @staticmethod
    def find(srp: sirope.Sirope, nombre: str) -> "Usuario":
        return srp.find_first(Usuario, lambda u: u.nombre == nombre)