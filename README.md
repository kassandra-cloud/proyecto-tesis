# Sistema de Gestión para Junta de Vecinos "Villa Vista al Mar"

Este repositorio contiene el código fuente del backend para el proyecto de tesis "Automatización administrativa en junta de vecinos 'Villa vista al mar'". El sistema está desarrollado en Django y provee una API REST para ser consumida por una plataforma web de administración y una aplicación móvil para los vecinos.

---

## ⚙️ Cómo Empezar a Trabajar en el Proyecto

Estas son las instrucciones para que cada integrante del equipo configure su entorno de desarrollo local.




### 1. ANTES DE TODO VERIFICAR TENER EL "ffmpeg.exe" EN EL PATH
TUTORIAL EN EL GRUPO DE WSP YA LUEGO Preparar el Entorno Virtual (`venv`)

Cada vez que clones el proyecto en una nueva máquina, o si empiezas desde cero, debes crear un entorno virtual. Esto aísla las librerías del proyecto para no crear conflictos.

```bash
# 1. Clona el repositorio (si no lo tienes)
git clone <URL_DEL_REPOSITORIO>
cd proyecto-tesis

# 2. Crea el entorno virtual (solo se hace una vez)
python -m venv venv
```

Ahora, **activa el entorno**. Este paso debes hacerlo **CADA VEZ** que abras una nueva terminal para trabajar.

* **En Windows:**
    ```bash
    .\venv\Scripts\activate
    ```

> ✨ Sabrás que el entorno está activo porque verás `(venv)` al inicio de la línea de comandos.

### 2. Instalar las Dependencias

Con el `venv` activado, instala todas las librerías que el proyecto necesita.

```bash
pip install -r requirements.txt
```

### 3. para configurar el lanzamiento de tanto la pagina web como el worker (necesario para la transcripcion en la nube)
Pueden verificar el archivo "Procfile" y ahi configurar el lanzamiento, luego hacer

```bash
honcho start 
```
se lanzaran los dos en un solo cmd Y
¡Listo! Ya puedes acceder a la aplicación en `http://127.0.0.1:8000/`.

---
¿Quieres añadir una nueva librería? La añades solo a requirements.in.

Ejecutas pip-compile requirements.in para actualizar el requirements.txt.

Ejecutas pip-sync para instalarla.

Haces git commit de ambos archivos.

## 🤝 Flujo de Trabajo en Equipo con Git

Para evitar conflictos y no borrar el trabajo de los demás, sigan siempre este flujo:

**Al empezar a trabajar:**

1.  **Sincroniza tu repositorio local:** Antes de escribir una sola línea de código, descarga los últimos cambios que tus compañeras hayan subido.
    ```bash
    git pull origin main
    ```

**Al terminar tu trabajo:**

2.  **Guarda tus cambios:** Añade los archivos que modificaste y crea un "commit" con un mensaje claro.
    ```bash
    # Añade todos los cambios
    git add .

    # Crea el commit
    git commit -m "feat: Agrega la funcionalidad X"
    ```
    > **Buenas prácticas para mensajes:** Usa `feat:` para nuevas características, `fix:` para corregir errores, y `docs:` para cambios en la documentación como este README.

3.  **Sube tus cambios:** Ahora que ya tienes tu trabajo guardado y estás sincronizado, sube tus commits a GitHub.
    ```bash
    git push origin main
    ```

---

## 📄 Sobre el Archivo `.gitignore`

Hemos añadido un archivo llamado `.gitignore`. Su propósito es **decirle a Git qué archivos y carpetas debe ignorar y NUNCA subir al repositorio**.


