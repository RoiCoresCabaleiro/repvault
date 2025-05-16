from datetime import datetime

class EntrenamientoEnCurso:
    def __init__(self, usuario_nombre, plantilla_soid, nombre_plantilla, observaciones, ejercicios_plantilla):
        self.usuario_nombre = usuario_nombre
        self.plantilla_soid = plantilla_soid  # plantilla de la que se originó
        self.nombre_plantilla = nombre_plantilla 
        self.observaciones = observaciones
        self.ejercicios = {}  # dict: clave → lista de series (cada series es un diccionario con "peso", "reps", "hecha")
        self.inicio = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        for clave, num_series in ejercicios_plantilla:
            self.ejercicios[clave] = []
            for _ in range(num_series):
                self.ejercicios[clave].append({
                    "peso": "",
                    "reps": "",
                    "hecha": False
                })