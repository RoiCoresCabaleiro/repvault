class EntrenamientoRealizado:
    def __init__(self, usuario_nombre, nombre, observaciones, ejercicios, fecha, duracion):
        self.usuario_nombre = usuario_nombre
        self.nombre = nombre
        self.observaciones = observaciones
        self.ejercicios = ejercicios  # dict: clave → lista de series
        self.fecha = fecha  # fecha = hora de inicio
        self.duracion = duracion  # en minutos