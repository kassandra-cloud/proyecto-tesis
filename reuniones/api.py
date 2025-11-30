# reuniones/api.py
from rest_framework import viewsets, permissions, filters, status
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import Reunion, Acta, Asistencia, LogConsultaActa
from .serializers import ReunionSerializer, ActaSerializer,AsistenciaSerializer
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Count
from django.db import transaction # <-- Necesario para asegurar la consistencia del ETL
from .models import Reunion, EstadoReunion
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response 

# 🆕 IMPORTACIONES DEL DATA MART (Necesarias para el mini-ETL síncrono)
from datamart.models import FactConsultaActa, DimVecino, DimActa 

# =========================================================================
# 🆕 FUNCIÓN AUXILIAR: Mini-ETL SÍNCRONO para Consultas de Actas
# =========================================================================
# Esta lógica debe ser idéntica a la que está en procesar_etl.py para este hecho.
def actualizar_fact_consulta_actas_sincrono():
    """
    Realiza una carga completa (full load) de FactConsultaActa basada en LogConsultaActa.
    ASUME que las dimensiones DimVecino y DimActa ya han sido pobladas.
    """
    with transaction.atomic():
        # 1. Eliminar datos antiguos (full load)
        FactConsultaActa.objects.all().delete()
        
        # 2. Extracción y mapeo de dimensiones (Data Mart ID -> Objeto Dimensión)
        vecino_map = {d.vecino_id_oltp: d for d in DimVecino.objects.all()}
        acta_map = {d.acta_id_oltp: d for d in DimActa.objects.all()}

        # 3. Extraer logs transaccionales
        logs = LogConsultaActa.objects.all().select_related('acta', 'vecino')

        # 4. Transformación y Carga
        fact_consultas = []
        for log in logs:
            dim_vecino = vecino_map.get(log.vecino_id) 
            dim_acta = acta_map.get(log.acta_id)

            if dim_vecino and dim_acta:
                fact_consultas.append(FactConsultaActa(
                    vecino=dim_vecino,
                    acta=dim_acta,
                    fecha_consulta=log.fecha_consulta
                ))
                
        FactConsultaActa.objects.bulk_create(fact_consultas)

# =========================================================================
# FIN DE FUNCIÓN AUXILIAR
# =========================================================================

class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    
class ReunionViewSet(viewsets.ReadOnlyModelViewSet):
    # ... (código ReunionViewSet existente)
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

        if estado == "programada":
            return qs.filter(estado=EstadoReunion.PROGRAMADA)
        if estado == "en_curso":
            return qs.filter(estado=EstadoReunion.EN_CURSO)
        if estado == "realizada":
            return qs.filter(estado=EstadoReunion.REALIZADA)
        return qs

class ActaViewSet(viewsets.ReadOnlyModelViewSet):
    # ... (código ActaViewSet existente)
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
    
    # --- ACCIÓN PARA REGISTRAR LA CONSULTA (CORREGIDA) ---
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="consultar")
    def registrar_consulta(self, request, pk=None):
        try:
            acta = Acta.objects.get(pk=pk)
        except Acta.DoesNotExist:
            return Response({"detail": "Acta no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        # 1. CREAR EL REGISTRO TRANSACCIONAL (OLTP)
        LogConsultaActa.objects.create(
            acta=acta,
            vecino=request.user # Asumiendo que request.user es el vecino que consulta
        )

        # 2. EJECUTAR EL MINI-ETL SÍNCRONO PARA EL ANÁLISIS (Data Mart)
        actualizar_fact_consulta_actas_sincrono() 
        
        # 3. FIX: SERIALIZAR Y DEVOLVER LOS DATOS DEL ACTA (Cambio de 204 No Content a 200 OK + Data)
        serializer = self.get_serializer(acta)
        return Response(serializer.data, status=status.HTTP_200_OK)
    # ---------------------------------------------

class AsistenciaViewSet(viewsets.ReadOnlyModelViewSet):
    # ... (código AsistenciaViewSet existente)
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
        user = request.user
        if not user.is_authenticated:
            qs = self.get_queryset().none()
        else:
            qs = self.get_queryset().filter(vecino=user)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)