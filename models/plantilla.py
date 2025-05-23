class Plantilla:
    def __init__(self, nombre, observaciones, usuario_nombre):
        self.nombre = nombre
        self.observaciones = observaciones
        self.usuario_nombre = usuario_nombre

        self.ejercicios = {}  # dict: clave_ejercicio → número de series
        self.orden = []  # lista ordenada de claves de ejercicios
        self.ultima_vez = None

    @property
    def oid(self) -> str | None:
        return getattr(self, "__oid__", None)