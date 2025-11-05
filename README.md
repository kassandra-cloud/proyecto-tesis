# Sistema de Gestión para Junta de Vecinos "Villa Vista al Mar"

Este repositorio contiene el código fuente del backend para el proyecto de tesis "Automatización administrativa en junta de vecinos 'Villa vista al mar'". El sistema está desarrollado en Django y provee una API REST para ser consumida por una plataforma web de administración y una aplicación móvil para los vecinos.

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

## 📡 API REST de Votaciones (v1)

Esta API permite a la app web y móvil interactuar con el módulo de votaciones.

🔐 Autenticación

Requiere Token (DRF).

Header:
Authorization: Token <TU_TOKEN>

Si usas rest_framework.authtoken:

python manage.py migrate
python manage.py drf_create_token <usuario>


(o crea el token desde el admin)

🔗 Endpoints

1) Listar votaciones abiertas

GET /votaciones/api/v1/abiertas/

200 OK (ejemplo):

[
  {
    "id": 12,
    "pregunta": "¿Aprobar presupuesto 2026?",
    "fecha_cierre": "2025-10-30T23:59:59",
    "activa": true,
    "esta_abierta": true,
    "opciones": [
      {"id": 51, "texto": "Sí"},
      {"id": 52, "texto": "No"}
    ],
    "ya_vote": false,
    "opcion_votada_id": null
  }
]


2) Emitir voto

POST /votaciones/api/v1/<pk>/votar/

Body JSON:

{ "opcion_id": 51 }


Respuestas esperadas

200: { "ok": true, "mensaje": "Voto registrado" }

400/409: faltan datos / voto duplicado

403: votación cerrada

3) Resultados de una votación

GET /votaciones/api/v1/<pk>/resultados/

200 OK (ejemplo):

{
  "votacion": { "id": 12, "pregunta": "¿Aprobar presupuesto 2026?" },
  "total_votos": 147,
  "opciones": [
    { "opcion_id": 51, "texto": "Sí", "votos": 91 },
    { "opcion_id": 52, "texto": "No", "votos": 56 }
  ]
}

🧪 Pruebas rápidas (cURL)
# Listar abiertas
curl -H "Authorization: Token $TOKEN" http://127.0.0.1:8000/votaciones/api/v1/abiertas/

# Votar (reemplaza {pk} y opcion_id)
curl -X POST -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
-d '{"opcion_id":51}' http://127.0.0.1:8000/votaciones/api/v1/{pk}/votar/

# Resultados
curl -H "Authorization: Token $TOKEN" http://127.0.0.1:8000/votaciones/api/v1/{pk}/resultados/

📱 App móvil (emulador Android)

Base URL: http://10.0.2.2:8000/

Producción: usar el dominio/IP del servidor.

🧭 Reglas clave

Un usuario solo puede votar una vez por votación (enforced en base de datos).

Solo se puede votar si la votación está abierta (activa y no expirada).

Un voto solo es válido si la opción pertenece a esa votación.
