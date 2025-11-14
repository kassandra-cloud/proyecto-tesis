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
    /recursos/api/v1/solicitudes/
    GET ?mine=true&estado=PENDIENTE|APROBADA|RECHAZADA
    POST crea solicitud (ya lo tienes)
    """
    serializer_class = SolicitudReservaSerializer
    pagination_class = DefaultPagination
    permission_classes = [permissions.IsAuthenticated]
    queryset = SolicitudReserva.objects.select_related("recurso", "solicitante")

    def get_queryset(self):
        qs = super().get_queryset()
        
        # 💡 CORRECCIÓN CRÍTICA:
        # 1. Por defecto, siempre filtramos por el usuario logueado para seguridad (MINE=TRUE implícito).
        qs = qs.filter(solicitante=self.request.user) 

        # 2. Solo si el usuario es STAFF y solicita explícitamente ver TODAS (mine=false),
        # reestablecemos el queryset a TODAS las solicitudes.
        show_all_requested = self.request.query_params.get("mine")
        
        # Verifica si el staff está solicitando ver 'mine=false'
        if show_all_requested and show_all_requested.lower() in ("0", "false", "f", "no"):
             if self.request.user.is_staff: 
                 # Solo Staff puede anular el filtro.
                 qs = super().get_queryset() 

        # 3. Filtro de estado opcional
        estado = self.request.query_params.get("estado")
        if estado in dict(SolicitudReserva.ESTADOS):
            qs = qs.filter(estado=estado)

        return qs.order_by("-creado_el")

    def get_serializer_class(self):
        if self.action == "create":
            return CrearSolicitudSerializer
        return SolicitudReservaSerializer

    def perform_create(self, serializer):
        serializer.save(solicitante=self.request.user)