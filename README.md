# RepVault

**RepVault** es una aplicación web para gestionar entrenamientos, rutinas y ejercicios, con seguimiento de sesiones y estadísticas.

---

## 🚀 Instalación

Sigue estos pasos (Linux / WSL):

1. **Clonar el repositorio**  
   ```bash
   git clone https://github.com/RoiCoresCabaleiro/repvault.git
   cd repvault
   ```

2. **Crear y activar un entorno virtual**  
   Por ejemplo, usando `venv`:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Instalar dependencias**  
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar la secret key**  
   Crea un archivo `secretkey.json` en la raíz del proyecto con este contenido:
   ```json
   {
     "SECRET_KEY": "una_cadena_secreta_super_segura"
   }
   ```

5. **Levantar Redis**  
   Asegúrate de tener un servidor Redis accesible en `localhost:6379` (o ajusta la URL en el código).

6. **Ejecutar la aplicación**  
   ```bash
   python app.py
   ```
   La aplicación quedará disponible en `http://127.0.0.1:5000/`.

---

> **IMPORTANTE:**  
> Para poder explorar completamente el funcionamiento del sistema (en especial las vistas de historial y estadísticas), **registra** un usuario con el nombre **`prueba`**.  
> Al hacerlo, se generarán automáticamente varios `EntrenamientoRealizado` de ejemplo necesarios para estas secciones.
