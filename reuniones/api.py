# reuniones/api.py
from datetime import timedelta

from django.db.models import Q, Count
from django.utils import timezone
from django.db import transaction

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets, permissions, filters, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Reunion, Acta, Asistencia, LogConsultaActa, EstadoReunion
from .serializers import ReunionSerializer, ActaSerializer, AsistenciaSerializer

# (Opcional) Si algún día quieres disparar un task al registrar consulta:
# from datamart.tasks import tarea_actualizar_bi_async


class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ReunionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API Reuniones (móvil):
    - Cache 10s para list y retrieve.
    - Filtro por estado: programada | en_curso | realizada
    """
    serializer_class = ReunionSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = DefaultPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["titulo", "tabla", "tipo"]
    ordering_fields = ["fecha", "titulo"]

    @method_decorator(cache_page(10))  # ✅ móvil “casi real-time”
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(10))  # ✅ detalle también rápido
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        qs = (
            Reunion.objects.all()
            .select_related("acta", "creada_por")
            .annotate(asistentes_count=Count("asistentes"))
            .order_by("-fecha")
        )

        estado = self.request.query_params.get("estado")
        if not estado:
            return qs

        # estado viene en minúscula desde el móvil
        if estado == "programada":
            return qs.filter(estado=EstadoReunion.PROGRAMADA)
        if estado == "en_curso":
            return qs.filter(estado=EstadoReunion.EN_CURSO)
        if estado == "realizada":
            return qs.filter(estado=EstadoReunion.REALIZADA)

        # fallback: devuelve todo si viene un valor inválido
        return qs


class ActaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API Actas (móvil):
    - list y retrieve rápidos
    - acción POST /actas/{id}/consultar/ para registrar consulta (OLTP)
    """
    serializer_class = ActaSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = DefaultPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["contenido", "reunion__titulo"]
    ordering_fields = ["reunion__fecha"]

    @method_decorator(cache_page(10))  # ✅ lista de actas rápida
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(10))  # ✅ detalle acta rápido
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        qs = Acta.objects.select_related("reunion").order_by("-reunion__fecha")

        reunion_id = self.request.query_params.get("reunion")
        if reunion_id:
            qs = qs.filter(reunion_id=reunion_id)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(contenido__icontains=search) |
                Q(reunion__titulo__icontains=search)
            )
        return qs

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        url_path="consultar"
    )
    def registrar_consulta(self, request, pk=None):
        """
        ✅ RÁPIDO: solo registra LogConsultaActa (OLTP) y responde con el acta.
        ❌ NO ejecuta mini-ETL síncrono (eso era lo lento).
        """
        try:
            acta = Acta.objects.select_related("reunion").get(pk=pk)
        except Acta.DoesNotExist:
            return Response({"detail": "Acta no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        # 1) Registrar consulta OLTP
        LogConsultaActa.objects.create(
            acta=acta,
            vecino=request.user
        )

        # 2) (Opcional) disparar async para BI si te interesa “casi inmediato”
        # tarea_actualizar_bi_async.delay()

        # 3) Responder con datos del acta (200 OK)
        serializer = self.get_serializer(acta)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AsistenciaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API Asistencia (móvil):
    - endpoint /asistencia/mis/ devuelve asistencias del usuario
    """
    queryset = Asistencia.objects.select_related("reunion", "vecino")
    serializer_class = AsistenciaSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination

    def get_queryset(self):
        qs = super().get_queryset()
        reunion_id = self.request.query_params.get("reunion")
        if reunion_id:
            qs = qs.filter(reunion_id=reunion_id)
        return qs

    @action(detail=False, methods=["get"], url_path="mis")
    def mis_asistencias(self, request):
        user = request.user
        qs = self.get_queryset().filter(vecino=user)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
