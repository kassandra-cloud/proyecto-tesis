"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Definición de clases de permisos personalizados para DRF.
               Permite restringir vistas solo a Administradores o Secretarias.
--------------------------------------------------------------------------------
"""
from rest_framework.permissions import BasePermission

class EsAdminOSectretaria(BasePermission):
    """
    Permiso que verifica si el usuario es Staff o pertenece a los grupos
    'SECRETARIA' o 'ADMIN'.
    """
    def has_permission(self, request, view):
        u = request.user
        return bool(u and (u.is_staff or u.groups.filter(name__in=["SECRETARIA","ADMIN"]).exists()))