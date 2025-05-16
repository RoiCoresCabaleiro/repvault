class EntrenamientoRealizado:
    def __init__(self, usuario_nombre, nombre, observaciones, ejercicios, fecha, duracion):
        self.usuario_nombre = usuario_nombre
        self.nombre = nombre
        self.observaciones = observaciones
        self.ejercicios = ejercicios  # dict: clave → lista de series (cada series es un diccionario con "peso", "reps", "hecha")
        self.fecha = fecha  # hora de inicio
        self.duracion = duracion