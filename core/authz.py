"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Contiene la lógica de autorización del sistema (RBAC).
                       Define funciones helper ('can', 'user_role') para verificar
                       si un usuario tiene permisos para realizar una acción sobre
                       un recurso, basándose en la matriz de roles definida en 
                       roles.py. Incluye un decorador para proteger vistas.
--------------------------------------------------------------------------------
"""

# Importa wraps para preservar metadatos de funciones decoradas.
from functools import wraps
# Importa utilidades de redirección de Django.
from django.shortcuts import redirect
from django.urls import reverse
# Importa la matriz de configuración de permisos.
from core.roles import ROLE_MATRIX
# Importa el modelo Perfil para acceder al rol.
from core.models import Perfil

def user_role(user) -> str | None:
    """
    Devuelve el rol del usuario (string de Perfil.Roles) o None.
    Los superusuarios pasan directo por can() y no necesitan Perfil.
    """
    # Intenta obtener el atributo 'perfil' del usuario de forma segura.
    perfil = getattr(user, "perfil", None)
    # Retorna el atributo 'rol' del perfil si existe, sino None.
    return getattr(perfil, "rol", None)

def can(user, resource: str, action: str) -> bool:
    """
    Regla única de autorización:
    - Usuario no autenticado => False
    - Superusuario => True (bypass total)
    - Si no tiene Perfil o rol => False
    - Si está en la matriz ROLE_MATRIX[resource][action] => True
    """
    # 1. Verifica si el usuario existe y está logueado.
    if not (user and user.is_authenticated):
        return False

    # 2. Bypass: el admin/superuser puede hacer TODO en el sistema.
    if getattr(user, "is_superuser", False):
        return True

    # 3. Obtiene el rol del usuario normal.
    rol = user_role(user)
    # Si no tiene rol asignado, no tiene permisos.
    if not rol:
        return False

    # 4. Consulta la matriz de permisos.
    # Busca en ROLE_MATRIX -> recurso (ej. 'talleres') -> acción (ej. 'create').
    # Devuelve una lista vacía [] si no encuentra la clave.
    allowed = ROLE_MATRIX.get(resource, {}).get(action, [])
    
    # 5. Verifica si el rol del usuario está en la lista de permitidos.
    return rol in allowed

def role_required(resource: str, action: str, *, redirect_name: str = "sin_permiso"):
    """
    Decorador para Vistas Basadas en Funciones (FBVs). 
    Verifica permisos antes de ejecutar la vista. 
    Redirige a 'sin_permiso' si la verificación falla.
    """
    def decorator(viewfunc):
        @wraps(viewfunc)
        def _wrapped(request, *args, **kwargs):
            # Llama a la función 'can' con el usuario de la request.
            if can(request.user, resource, action):
                # Si tiene permiso, ejecuta la vista original.
                return viewfunc(request, *args, **kwargs)
            # Si no, redirige a la página de error configurada.
            return redirect(reverse(redirect_name))
        return _wrapped
    return decorator