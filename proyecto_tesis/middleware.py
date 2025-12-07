import time

from datamart.models import LogRendimiento


class MonitorRendimientoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        inicio = time.time()

        # Procesar la petición
        response = self.get_response(request)

        fin = time.time()
        duracion_ms = int((fin - inicio) * 1000)

        path = request.path

        # No medimos estáticos, media ni rutas de admin
        if (
            not path.startswith("/static/")
            and not path.startswith("/media/")
            and not path.startswith("/admin/")
        ):
            usuario = (
                request.user.username
                if hasattr(request, "user") and request.user.is_authenticated
                else "Anónimo"
            )

            try:
                LogRendimiento.objects.create(
                    usuario=usuario,
                    path=path[:255],
                    metodo=request.method,
                    tiempo_ms=duracion_ms,
                    status_code=getattr(response, "status_code", 200),
                )
            except Exception:
                # Nunca reventar la request por un problema de logging
                pass

        return response
