class Ejercicio:
    def __init__(self, nombre, descripcion, usuario_nombre, grupo_muscular, equipamiento):
        self.nombre = nombre
        self.descripcion = descripcion
        self.usuario_nombre = usuario_nombre

        self.grupo_muscular = grupo_muscular  # Uno de: Pecho, Espalda, etc.
        self.equipamiento = equipamiento      # Uno de: Peso libre, Máquinas

        self.historial = []  # Entrenamientos donde fue usado
        self.ultimas_series = []  # Lista de dicts(series) con {"peso": n, "reps": n}

    @property
    def oid(self) -> str | None:
        return getattr(self, "__oid__", None)
    
    def is_owner(self, usuario_nombre: str) -> bool:
        return self.usuario_nombre == usuario_nombre