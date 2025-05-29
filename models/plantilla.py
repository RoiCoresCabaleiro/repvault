class Plantilla:
    def __init__(self, nombre, observaciones, usuario_nombre):
        self.nombre = nombre
        self.observaciones = observaciones
        self.usuario_nombre = usuario_nombre

        self.ejercicios = {}  # dict: clave(ejercicio) → número de series
        self.orden = []  # lista de claves de ejercicios ordenados por el usuario en en plantillas.gestionar
        self.ultima_vez = None  # fecha de ultima vez que se realizó un entrenamiento a partir la plantilla

    @property
    def oid(self) -> str | None:
        return getattr(self, "__oid__", None)
    
    def is_owner(self, usuario_nombre: str) -> bool:
        """Devuelve true si el nombre del usuario pasado es el del "dueño" del objeto.\n
        Se usa principalmente de esta forma: obj.is_owner(current_user.get_id())"""

        return self.usuario_nombre == usuario_nombre