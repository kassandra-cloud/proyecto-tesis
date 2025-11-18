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
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response 
class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
class ReunionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReunionSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = DefaultPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["titulo", "tabla", "tipo"]
    ordering_fields = ["fecha", "titulo"]

    def get_queryset(self):
        qs = (
            Reunion.objects.all()
            .select_related("acta")
            .annotate(asistentes_count=Count("asistentes"))
            .order_by("-fecha")
        )

        estado = self.request.query_params.get("estado")
        if not estado:
            return qs

        # 👇 AHORA filtramos por el campo estado, no solo por fecha
        if estado == "programada":
            return qs.filter(estado=EstadoReunion.PROGRAMADA)
        if estado == "en_curso":
            return qs.filter(estado=EstadoReunion.EN_CURSO)
        if estado == "realizada":
            return qs.filter(estado=EstadoReunion.REALIZADA)
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
    queryset = Asistencia.objects.select_related("reunion", "vecino")
    serializer_class = AsistenciaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        reunion_id = self.request.query_params.get("reunion")
        if reunion_id:
            qs = qs.filter(reunion_id=reunion_id)
        return qs

    @action(detail=False, methods=["get"], url_path="mis")
    def mis_asistencias(self, request):
        """
        Devuelve las asistencias donde el 'vecino' es el usuario logueado.
        """
        user = request.user

        if not user.is_authenticated:
            # Por seguridad: si no está logueado, devolvemos lista vacía
            qs = self.get_queryset().none()
        else:

            qs = self.get_queryset().filter(vecino=user)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)