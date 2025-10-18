# tesis-prueba-gemini
Sigue estos pasos para configurar y ejecutar el servidor en tu máquina local.
Esto es lo que haces cada vez que empiezas a trabajar en el proyecto.

    Clonar el repositorio (si no lo tienes): Abre tu terminal, navega a la carpeta donde guardas tus proyectos y clona el repositorio.
    Bash

git clone <URL_DE_TU_REPOSITORIO_EN_GITHUB>
cd proyecto-tesis

Crear y/o Activar el Entorno Virtual: Si es la primera vez que clonas el proyecto, crea el venv. Si ya existe, solo actívalo.
Bash

# (Solo si es la primera vez)
python -m venv venv

# Activar siempre (en Windows)
.\venv\Scripts\activate

    ✨ Recuerda que verás (venv) al inicio de la línea en tu terminal.

Instalar Dependencias: Asegúrate de tener todas las librerías necesarias.
Bash

pip install -r requirements.txt

Ejecutar el Servidor: ¡Inicia el servidor de Django para ver los cambios en vivo!
Bash

python manage.py runserver

Ahora puedes abrir tu navegador en http://127.0.0.1:8000/ para ver la página.
Prerrequisitos
Tener instalado Python 3.
Tener instalado Git
