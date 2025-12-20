"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Define un backend de autenticación personalizado llamado
                       'LoginConCorreo'. Permite a los usuarios iniciar sesión 
                       utilizando tanto su nombre de usuario (username) como 
                       su dirección de correo electrónico (email).
--------------------------------------------------------------------------------
"""

# Importa la clase base para backends de autenticación de Django.
from django.contrib.auth.backends import ModelBackend
# Importa la función para obtener el modelo de usuario activo de forma dinámica.
from django.contrib.auth import get_user_model
# Importa Q para realizar consultas lógicas OR en la base de datos.
from django.db.models import Q

# Obtiene la referencia al modelo User configurado en settings.
User = get_user_model()

class LoginConCorreo(ModelBackend):
    """Clase que extiende la autenticación para soportar email o username."""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Método principal de autenticación.
        'username' aquí puede ser el nombre de usuario real o el correo.
        """
        # Si no llega username pero llega 'email' en los argumentos, lo usamos.
        if username is None:
            username = kwargs.get('email')

        try:
            # Busca un usuario en la base de datos que coincida con el username 
            # O que coincida con el email. 
            # 'iexact' hace la búsqueda insensible a mayúsculas/minúsculas.
            user = User.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
        except User.DoesNotExist:
            # Si no encuentra a nadie, retorna None (autenticación fallida).
            return None

        # Si encontró usuario, verifica si la contraseña es correcta 
        # y si el usuario tiene permiso para autenticarse (ej. está activo).
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
            
        # Si la contraseña falla o el usuario está inactivo, retorna None.
        return None