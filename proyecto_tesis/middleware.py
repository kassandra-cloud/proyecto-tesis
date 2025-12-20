"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Middleware personalizado para interceptar cada petición HTTP, 
               medir el tiempo que tarda el servidor en responder y guardar 
               métricas de rendimiento en la base de datos (LogRendimiento).
--------------------------------------------------------------------------------
"""
import time  # Para medir el tiempo

from datamart.models import LogRendimiento  # Importa el modelo donde se guardan los logs

class MonitorRendimientoMiddleware:
    def __init__(self, get_response):
        # Guarda la función que procesa la siguiente parte de la cadena de middlewares/vistas
        self.get_response = get_response

    def __call__(self, request):
        # Marca el tiempo de inicio antes de procesar la vista
        inicio = time.time()

        # Pasa la petición a la siguiente capa y obtiene la respuesta
        response = self.get_response(request)

        # Marca el tiempo final después de que la vista respondió
        fin = time.time()
        # Calcula la duración en milisegundos
        duracion_ms = int((fin - inicio) * 1000)

        path = request.path  # Obtiene la ruta solicitada

        # Filtra rutas que no queremos medir (estáticos, media, admin)
        if (
            not path.startswith("/static/")
            and not path.startswith("/media/")
            and not path.startswith("/admin/")
        ):
            # Determina el usuario (o "Anónimo" si no está logueado)
            usuario = (
                request.user.username
                if hasattr(request, "user") and request.user.is_authenticated
                else "Anónimo"
            )

            try:
                # Intenta guardar el registro en la base de datos
                LogRendimiento.objects.create(
                    usuario=usuario,
                    path=path[:255], # Corta el path si es muy largo
                    metodo=request.method, # GET, POST, etc.
                    tiempo_ms=duracion_ms,
                    status_code=getattr(response, "status_code", 200), # Código HTTP (200, 404, 500)
                )
            except Exception:
                # Nunca reventar la request por un problema de logging (fail-safe)
                pass

        # Devuelve la respuesta al cliente
        return response