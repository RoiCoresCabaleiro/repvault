class Ejercicio:
    def __init__(self, nombre, descripcion, usuario_nombre, grupo_muscular, equipamiento):
        self.nombre = nombre
        self.descripcion = descripcion
        self.usuario_nombre = usuario_nombre

        self.grupo_muscular = grupo_muscular  # grupo muscular principal
        self.equipamiento = equipamiento  # máquina o peso libre

        self.ultimas_series = []  # List[dicts{series}] con series = {"peso": n, "reps": n}

    @property
    def oid(self) -> str | None:
        return getattr(self, "__oid__", None)
    
    def is_owner(self, usuario_nombre: str) -> bool:
        """Devuelve true si el nombre del usuario pasado es el del "dueño" del objeto.\n
        Se usa principalmente de esta forma: obj.is_owner(current_user.get_id())"""

        return self.usuario_nombre == usuario_nombre
    