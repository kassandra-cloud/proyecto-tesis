from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse
from core.roles import ROLE_MATRIX
from core.models import Perfil

def user_role(user) -> str | None:
    """
    Devuelve el rol del usuario (string de Perfil.Roles) o None.
    Los superusuarios pasan directo por can() y no necesitan Perfil.
    """
    perfil = getattr(user, "perfil", None)
    return getattr(perfil, "rol", None)

def can(user, resource: str, action: str) -> bool:
    """
    Regla única de autorización:
    - Usuario no autenticado => False
    - Superusuario => True (bypass total)
    - Si no tiene Perfil o rol => False
    - Si está en la matriz ROLE_MATRIX[resource][action] => True
    """
    if not (user and user.is_authenticated):
        return False

    # Bypass: el admin/superuser puede TOD
    if getattr(user, "is_superuser", False):
        return True

    rol = user_role(user)
    if not rol:
        return False

    allowed = ROLE_MATRIX.get(resource, {}).get(action, [])
    return rol in allowed

def role_required(resource: str, action: str, *, redirect_name: str = "sin_permiso"):
    """
    Decorador para FBVs. Redirige a 'sin_permiso' si no puede.
    """
    def decorator(viewfunc):
        @wraps(viewfunc)
        def _wrapped(request, *args, **kwargs):
            if can(request.user, resource, action):
                return viewfunc(request, *args, **kwargs)
            return redirect(reverse(redirect_name))
        return _wrapped
    return decorator