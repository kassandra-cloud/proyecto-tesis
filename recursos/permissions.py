from rest_framework.permissions import BasePermission

class EsAdminOSectretaria(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and (u.is_staff or u.groups.filter(name__in=["SECRETARIA","ADMIN"]).exists()))
