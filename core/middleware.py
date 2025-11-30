# core/middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Verificar si el usuario está autenticado
        if request.user.is_authenticated:
            # 2. Verificar si tiene perfil y la bandera activada
            if hasattr(request.user, 'perfil') and request.user.perfil.debe_cambiar_password:
                
                # Definir rutas permitidas (para no crear un bucle de redirección infinito)
                # El usuario DEBE poder entrar a cambiar la clave y a cerrar sesión.
                path = request.path
                url_cambio = reverse('cambiar_password_obligatorio')
                url_logout = '/accounts/logout/' # O la que uses para salir
                
                # Excluir rutas de API para no romper la App Móvil si usa sesión web por error
                if not path.startswith('/api/'):
                    if path != url_cambio and path != url_logout and not path.startswith('/static/') and not path.startswith('/media/'):
                        return redirect('cambiar_password_obligatorio')

        response = self.get_response(request)
        return response