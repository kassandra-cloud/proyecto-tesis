# reuniones/api.py
from rest_framework import viewsets, permissions, filters
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import Reunion, Acta,Asistencia
from .serializers import ReunionSerializer, ActaSerializer,AsistenciaSerializer
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Count
class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

class ReunionViewSet(viewsets.ReadOnlyModelViewSet):
    # 💡 ELIMINAR ESTA LÍNEA o se usa un QuerySet que no se anota y el serializer fallará.
    # queryset = Reunion.objects.all().order_by("-fecha") 
    
    serializer_class = ReunionSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = DefaultPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["titulo", "tabla", "tipo"]
    ordering_fields = ["fecha", "titulo"]

    def get_queryset(self):
        # 💡 CORRECCIÓN CLAVE: ANOTAR el QuerySet base
        qs = Reunion.objects.all().order_by("-fecha").annotate(
            # Calcula el campo que espera el ReunionSerializer
            asistentes_count=Count('asistentes') 
        )

        # A partir de aquí, el código de filtrado por estado es correcto, pero debe aplicarse a 'qs'
        estado = self.request.query_params.get("estado")
        if not estado:
            return qs

        # ... (Lógica de filtrado por estado, que se mantiene igual)
        now = timezone.now()
        if estado == "programada":
            return qs.filter(fecha__gt=now)
        if estado == "en_curso":
            return qs.filter(fecha__lte=now, fecha__gte=now - timedelta(hours=2))
        if estado == "realizada":
            return qs.filter(fecha__lt=now - timedelta(hours=2))
        return qs
class ActaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /reuniones/api/actas/           → lista (paginada)
    GET /reuniones/api/actas/{id}/      → detalle (id = id de la Reunion)
    Filtros:
      ?reunion=<id>   → por reunión
      ?search=texto   → busca en contenido o título de la reunión
      ?ordering=-reunion__fecha
    """
    serializer_class = ActaSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = DefaultPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["contenido", "reunion__titulo"]
    ordering_fields = ["reunion__fecha"]

    def get_queryset(self):
        qs = Acta.objects.select_related("reunion").order_by("-reunion__fecha")
        reunion_id = self.request.query_params.get("reunion")
        if reunion_id:
            qs = qs.filter(reunion_id=reunion_id)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(contenido__icontains=search) | Q(reunion__titulo__icontains=search))
        return qs
class AsistenciaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /reuniones/api/asistencias/?reunion=<id>
    """
    serializer_class   = AsistenciaSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends    = [filters.OrderingFilter]
    ordering_fields    = ["id"]

    def get_queryset(self):

        qs = Asistencia.objects.select_related("vecino", "reunion")
        reunion_id = self.request.query_params.get("reunion")
        if reunion_id:
            qs = qs.filter(reunion_id=reunion_id)
        return qs.order_by("id")
