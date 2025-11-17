# reuniones/api.py
from rest_framework import viewsets, permissions, filters
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import Reunion, Acta,Asistencia
from .serializers import ReunionSerializer, ActaSerializer,AsistenciaSerializer
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Count
from .models import Reunion, EstadoReunion
class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
class ReunionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReunionSerializer
    # Ideal: proteger con autenticación (cuando ya tengas login de la app Android integrado)
    # permission_classes = [permissions.IsAuthenticated]
    permission_classes = [permissions.AllowAny]

    pagination_class = DefaultPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["titulo", "tabla", "tipo"]
    ordering_fields = ["fecha", "titulo"]

    def get_queryset(self):
        # Base: todas las reuniones anotadas con asistentes_count
        qs = Reunion.objects.all().annotate(
            asistentes_count=Count('asistentes')
        ).order_by("-fecha")

        # Leer parámetro ?estado=...
        estado_param = self.request.query_params.get("estado")

        if not estado_param:
            # Sin filtro → devolver todo
            return qs

        # Aceptar tanto "PROGRAMADA" como "programada"
        estado_normalizado = estado_param.upper()

        # Validar que el valor exista en los choices del modelo
        estados_validos = {choice[0] for choice in EstadoReunion.choices}
        if estado_normalizado in estados_validos:
            qs = qs.filter(estado=estado_normalizado)

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
