class EntrenamientoRealizado:
    def __init__(self, usuario_nombre, nombre, observaciones, ejercicios, fecha, duracion):
        self.nombre = nombre
        self.observaciones = observaciones
        self.usuario_nombre = usuario_nombre

        self.ejercicios = ejercicios  # dict: clave(ejercicio) → lista de dicts(series) con {"peso": n, "reps": n, "hecha": t/f)
        self.fecha = fecha  # hora de inicio
        self.duracion = duracion

    @property
    def oid(self) -> str | None:
        return getattr(self, "__oid__", None)
    
    def is_owner(self, usuario_nombre: str) -> bool:
        return self.usuario_nombre == usuario_nombre