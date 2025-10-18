# Sistema de Gestión para Junta de Vecinos "Villa Vista al Mar"

Este repositorio contiene el código fuente del backend para el proyecto de tesis "Automatización administrativa en junta de vecinos 'Villa vista al mar'". El sistema está desarrollado en Django y provee una API REST para ser consumida por una plataforma web de administración y una aplicación móvil para los vecinos.

## 🚀 Avances Recientes (Tu Trabajo)

En esta última fase de desarrollo, se han implementado las siguientes funcionalidades clave en la plataforma web:

1.  **Módulo de Votaciones Completo:**
    * **Creación Dinámica:** La directiva (roles de Presidente y Tesorero) ahora puede crear nuevas votaciones especificando la pregunta, fecha/hora de cierre y opciones de voto personalizadas.
    * **Previsualización para la Directiva:** Se implementó una vista de monitoreo que permite a la directiva ver los resultados de las votaciones en tiempo real mediante barras de progreso, sin tener que esperar al cierre.
    * **Gestión Administrativa:** Se añadieron controles para que el Presidente pueda cerrar manualmente una votación en curso, editar su fecha de cierre o eliminarla si fue creada por error (solo si aún está abierta).
    * **Historial Inmutable:** Las votaciones ya cerradas no pueden ser eliminadas, garantizando un registro histórico transparente de las decisiones.

2.  **Mejora en Módulo de Reuniones:**
    * **Previsualización de Actas:** En la página de "Detalle de Reunión", ahora se muestra directamente el contenido del acta si esta ya ha sido redactada, facilitando su consulta rápida sin necesidad de exportarla.

---

## ⚙️ Cómo Empezar a Trabajar en el Proyecto

Estas son las instrucciones para que cada integrante del equipo configure su entorno de desarrollo local.

### 1. Preparar el Entorno Virtual (`venv`)

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
* **En macOS o Linux:**
    ```bash
    source venv/bin/activate
    ```
> ✨ Sabrás que el entorno está activo porque verás `(venv)` al inicio de la línea de comandos.

### 2. Instalar las Dependencias

Con el `venv` activado, instala todas las librerías que el proyecto necesita.

```bash
pip install -r requirements.txt
```

### 3. Configurar y Ejecutar el Proyecto

```bash
# 1. Crea las tablas en la base de datos
python manage.py migrate

# 2. Crea tu propio superusuario para acceder al admin
python manage.py createsuperuser

# 3. Inicia el servidor de desarrollo
python manage.py runserver
```

¡Listo! Ya puedes acceder a la aplicación en `http://127.0.0.1:8000/`.

---

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

**¿Por qué es importante?**

* **Evita subir el `venv`:** La razón principal por la que lo agregamos. La carpeta `venv` contiene cientos de archivos que son específicos de tu sistema operativo y que no deben compartirse. El archivo `requirements.txt` ya cumple la función de decirle a los demás qué instalar.
* **Mantiene el repositorio limpio:** Evita que se suban archivos temporales, bases de datos locales (`db.sqlite3`) o carpetas de caché (`__pycache__/`) que se generan automáticamente y no son parte del código fuente.

Al ignorar estos archivos, mantenemos el repositorio ligero, limpio y evitamos conflictos innecesarios.
