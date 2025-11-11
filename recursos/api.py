# recursos/api.py
from rest_framework import viewsets, permissions, filters
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import Recurso,SolicitudReserva
from .serializers import RecursoSerializer,SolicitudReservaSerializer, CrearSolicitudSerializer
from .permissions import EsAdminOSectretaria  
from rest_framework.decorators import action           
from rest_framework.response import Response 

class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"

class RecursoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Solo lectura: lista y detalle de recursos.
    Filtros:
      - ?disponible=true/false
      - ?search=texto (busca por nombre/descripcion)
    """
    queryset = Recurso.objects.all().order_by("nombre")
    serializer_class = RecursoSerializer
    permission_classes = [permissions.IsAuthenticated]   # así reutilizamos el token ya usado en la app
    pagination_class = DefaultPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["nombre", "descripcion"]

    def get_queryset(self):
        qs = super().get_queryset()
        disponible = self.request.query_params.get("disponible")
        if disponible is not None:
            if disponible.lower() in ("1", "true", "t", "yes", "y"):
                qs = qs.filter(disponible=True)
            else:
                qs = qs.filter(disponible=False)
        return qs
class SolicitudReservaViewSet(viewsets.ModelViewSet):
    """
    /recursos/api/v1/solicitudes/:
      GET: por defecto lista las solicitudes del usuario autenticado
           ?todas=1 -> lista todas (solo SECRETARIA/ADMIN/staff)
      POST: crea solicitud para el usuario (estado PENDIENTE)
    /recursos/api/v1/solicitudes/{id}/aprobar/ (POST) -> estado=APROBADA (SECRETARIA/ADMIN)
    /recursos/api/v1/solicitudes/{id}/rechazar/ (POST) -> estado=RECHAZADA (SECRETARIA/ADMIN)
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SolicitudReservaSerializer
    queryset = SolicitudReserva.objects.select_related("recurso", "solicitante")

    def get_serializer_class(self):
        return CrearSolicitudSerializer if self.action == "create" else SolicitudReservaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        todas = self.request.query_params.get("todas")
        if todas and EsAdminOSectretaria().has_permission(self.request, self):
            return qs
        return qs.filter(solicitante=self.request.user)

    def perform_create(self, serializer):
        serializer.save(solicitante=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[EsAdminOSectretaria])
    def aprobar(self, request, pk=None):
        s = self.get_object()
        s.estado = "APROBADA"
        s.save(update_fields=["estado"])
        return Response(SolicitudReservaSerializer(s).data)

    @action(detail=True, methods=["post"], permission_classes=[EsAdminOSectretaria])
    def rechazar(self, request, pk=None):
        s = self.get_object()
        s.estado = "RECHAZADA"
        s.save(update_fields=["estado"])
        return Response(SolicitudReservaSerializer(s).data)