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

        # Filtros (Ignorar estáticos y admin interno)
        path = request.path
        if not path.startswith('/static/') and not path.startswith('/media/') and not path.startswith('/admin/jsi18n/'):
            
            usuario = request.user.username if request.user.is_authenticated else "Anónimo"
            
            try:
                LogRendimiento.objects.create(
                    usuario=usuario,
                    path=path[:255],
                    metodo=request.method,
                    tiempo_ms=duracion_ms,
                    status_code=response.status_code # <--- GUARDAMOS EL CÓDIGO AQUÍ
                )
            except: pass

        return response