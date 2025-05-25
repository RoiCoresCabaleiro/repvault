from datetime import datetime

class EntrenamientoEnCurso:
    def __init__(self, nombre_plantilla, observaciones, usuario_nombre, plantilla_soid, ejercicios_plantilla):
        self.nombre_plantilla = nombre_plantilla  # nombre original de la plantilla que se puede modificar durante el entrenamiento
        self.observaciones = observaciones
        self.usuario_nombre = usuario_nombre
        self.plantilla_soid = plantilla_soid  # plantilla de la que se originó para fecha de ultima vez
        
        self.ejercicios = {}  # dict: clave → lista de series (cada series es un diccionario con "peso", "reps", "hecha")
        for clave, num_series in ejercicios_plantilla:
            self.ejercicios[clave] = []
            for _ in range(num_series):
                self.ejercicios[clave].append({ "peso": "", "reps": "", "hecha": False })

        self._inicio = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    @property
    def inicio(self) -> str:
        return self._inicio

    @property
    def oid(self) -> str | None:
        return getattr(self, "__oid__", None)
    
    def is_owner(self, usuario_nombre: str) -> bool:
        return self.usuario_nombre == usuario_nombre