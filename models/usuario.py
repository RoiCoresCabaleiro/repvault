from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import sirope

class Usuario(UserMixin):
    def __init__(self, nombre: str, contraseña: str):
        self.nombre = nombre
        self._contraseña_hash = generate_password_hash(contraseña)

    def comprobar_contraseña(self, contraseña: str) -> bool:
        return check_password_hash(self._contraseña_hash, contraseña)

    def get_id(self) -> str:
        return self.nombre

    @staticmethod
    def find(srp: sirope.Sirope, nombre: str) -> "Usuario":
        return srp.find_first(Usuario, lambda u: u.nombre == nombre)