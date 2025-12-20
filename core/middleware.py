"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Define Middlewares personalizados:
                       1. ForcePasswordChangeMiddleware: Redirige a cambio de 
                          clave si el usuario tiene la marca 'debe_cambiar_password'.
                       2. BloqueoTotalVecinosMiddleware: Restringe a los usuarios 
                          rol 'VECINO' de acceder al panel web, permitiendo solo 
                          API y página de alerta móvil.
--------------------------------------------------------------------------------
"""

# Importa funciones de redirección y resolución de URLs.
from django.shortcuts import redirect
from django.urls import reverse
# Importa constante de rol.
from core.roles import VECINO 

class ForcePasswordChangeMiddleware:
    """
    Obliga a cambiar la clave si es necesario (ej. primer inicio de sesión).
    """
    def __init__(self, get_response):
        # Configuración inicial estándar del middleware.
        self.get_response = get_response

    def __call__(self, request):
        # Verifica usuario logueado.
        if request.user.is_authenticated:
            # Verifica si tiene perfil y la bandera activada.
            if hasattr(request.user, 'perfil') and request.user.perfil.debe_cambiar_password:
                
                path = request.path
                # Intenta resolver la URL de cambio de clave.
                try:
                    url_cambio = reverse('cambiar_password_obligatorio')
                except:
                    url_cambio = '/usuarios/cambiar-password-obligatorio/' # Fallback por seguridad
                
                url_logout = '/accounts/logout/' # Ruta de cierre de sesión.
                
                # Excluir rutas de API para no romper la app móvil.
                if not path.startswith('/api/'):
                    # Si no está en la página de cambio, ni logout, ni estáticos, redirige.
                    if path != url_cambio and path != url_logout and not path.startswith('/static/') and not path.startswith('/media/'):
                        return redirect('cambiar_password_obligatorio')

        # Continúa con la petición.
        response = self.get_response(request)
        return response


class BloqueoTotalVecinosMiddleware:
    """
    Middleware ESTRICTO de seguridad:
    Si el usuario es VECINO:
    1. Permite acceso a la API (para que la App Móvil funcione).
    2. Permite acceso a archivos estáticos/media.
    3. Permite cerrar sesión.
    4. Permite ver la página de 'alerta_movil' (mensaje: "Use la App").
    5. BLOQUEA CUALQUIER OTRA RUTA WEB y redirige a 'alerta_movil'.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user

        # Solo aplicamos lógica si el usuario está autenticado y tiene perfil.
        if user.is_authenticated and hasattr(user, 'perfil'):
            
            # Verificamos si es VECINO.
            if user.perfil.rol == VECINO:
                path = request.path
                
                # --- LISTA BLANCA (Rutas permitidas) ---
                
                # 1. API (CRUCIAL para la App Móvil).
                if path.startswith('/api/'):
                    return self.get_response(request)
                
                # 2. Recursos estáticos y media (para cargar logos, estilos, etc.).
                if path.startswith('/static/') or path.startswith('/media/'):
                    return self.get_response(request)

                # 3. La propia página de alerta (para evitar bucle infinito de redirección).
                try:
                    url_alerta = reverse('alerta_movil')
                except:
                    url_alerta = '/usuarios/alerta-movil/'

                if path == url_alerta:
                    return self.get_response(request)

                # 4. Cerrar sesión (El usuario debe poder salir).
                try:
                    url_logout = reverse('logout')
                except:
                    url_logout = '/accounts/logout/' 
                
                if path == url_logout:
                    return self.get_response(request)
                
                # --- BLOQUEO ---
                # Si llegó aquí, está intentando entrar a /home, /talleres, /admin, etc.
                return redirect('alerta_movil')

        return self.get_response(request)