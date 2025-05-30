from datetime import datetime
from routes.utils import encode_oid

class EntrenamientoEnCurso:
    def __init__(self, nombre_plantilla, observaciones, usuario_nombre, plantilla_soid, ejercicios_plantilla):
        self.nombre_plantilla = nombre_plantilla  # nombre original de la plantilla que se puede modificar durante el entrenamiento
        self.observaciones = observaciones
        self.usuario_nombre = usuario_nombre
        self.plantilla_soid = plantilla_soid  # plantilla de la que se originó para actualizar fecha de ultima vez
        
        self.ejercicios = {}  # dict{clave_ej: list[dict{series}]} con series = {"peso": n, "reps": n, "hecha": t/f)
        # Se crea a partir de los ejercicios de la plantilla original)
        for clave, num_series in ejercicios_plantilla:
            self.ejercicios[clave] = []
            for _ in range(num_series):
                self.ejercicios[clave].append({ "peso": "", "reps": "", "hecha": False })

        self._inicio = datetime.now().strftime("%d/%m/%Y %H:%M:%S")  # fecha de creación del objeto, fecha de inicio del entrenamiento

    @property
    def inicio(self) -> str:
        return self._inicio

    @property
    def oid(self) -> str | None:
        return getattr(self, "__oid__", None)
    

    @classmethod
    def from_plantilla(cls, plantilla, usuario_nombre):
        """
        Construye un EntrenamientoEnCurso a partir de una Plantilla existente:
        copia nombre, observaciones y la lista de ejercicios con su orden.
        """
        return cls(
            usuario_nombre=usuario_nombre,
            plantilla_soid=encode_oid(plantilla.oid),
            nombre_plantilla=plantilla.nombre,
            observaciones=plantilla.observaciones,
            ejercicios_plantilla=[(soid, plantilla.ejercicios[soid]) for soid in plantilla.orden]
        )

    
    @classmethod
    def empty(cls, usuario_nombre):
        """
        Construye un EntrenamientoEnCurso “vacío” sin ejercicios previos.
        """
        return cls(
            usuario_nombre=usuario_nombre,
            plantilla_soid=None,
            nombre_plantilla="",
            observaciones="",
            ejercicios_plantilla=[]
        )


    def is_owner(self, usuario_nombre: str) -> bool:
        """
        Devuelve true si el nombre del usuario pasado es el del "dueño" del objeto.\n
        Se usa principalmente de esta forma: obj.is_owner(current_user.get_id())
        """

        return self.usuario_nombre == usuario_nombre