class EntrenamientoRealizado:
    def __init__(self, usuario_nombre, nombre, observaciones, ejercicios, fecha, duracion):
        self.nombre = nombre
        self.observaciones = observaciones
        self.usuario_nombre = usuario_nombre

        self.ejercicios = ejercicios  # dict{clave_ej: list[dict{series}]} con series = {"peso": n, "reps": n, "hecha": t/f)
        self.fecha = fecha  # fecha de inicio del entrenamiento en curso
        self.duracion = duracion # duracion en minutos

    @property
    def oid(self) -> str | None:
        return getattr(self, "__oid__", None)
    
    def is_owner(self, usuario_nombre: str) -> bool:
        """Devuelve true si el nombre del usuario pasado es el del "dueño" del objeto.\n
        Se usa principalmente de esta forma: obj.is_owner(current_user.get_id())"""

        return self.usuario_nombre == usuario_nombre