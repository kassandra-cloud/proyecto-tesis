"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   API REST para Reuniones. Incluye ViewSets para gestionar Reuniones, 
               Actas y Asistencias, además de una función auxiliar para actualizar 
               el Data Mart sincrónicamente cuando se consulta un acta.
--------------------------------------------------------------------------------
"""
# reuniones/api.py
from rest_framework import viewsets, permissions, filters, status # Importa utilidades de DRF
from rest_framework.pagination import PageNumberPagination # Importa paginación
from django.db.models import Q # Importa objeto Q para consultas complejas
from .models import Reunion, Acta, Asistencia, LogConsultaActa # Importa modelos locales
from .serializers import ReunionSerializer, ActaSerializer,AsistenciaSerializer # Importa serializadores
from django.utils import timezone # Importa utilidades de tiempo
from datetime import timedelta # Importa manejo de deltas de tiempo
from django.db.models import Q, Count # Importa funciones de agregación
from django.db import transaction # Importa manejo de transacciones de BD
from .models import Reunion, EstadoReunion # Importa modelos y enumeración de estados
from rest_framework.permissions import IsAuthenticated # Importa permiso de autenticación
from rest_framework.decorators import action # Importa decorador para acciones personalizadas
from rest_framework.response import Response # Importa objeto de respuesta

from datamart.models import FactConsultaActa, DimVecino, DimActa # Importa modelos del Data Mart


# FUNCIÓN AUXILIAR: Mini-ETL SÍNCRONO para Consultas de Actas
def actualizar_fact_consulta_actas_sincrono():
    """
    Realiza una carga completa (full load) de FactConsultaActa basada en LogConsultaActa.
    ASUME que las dimensiones DimVecino y DimActa ya han sido pobladas.
    """
    with transaction.atomic(): # Inicia transacción atómica
        FactConsultaActa.objects.all().delete() # Borra hechos anteriores para recargar
        
        #Extracción y mapeo de dimensiones 
        vecino_map = {d.vecino_id_oltp: d for d in DimVecino.objects.all()} # Crea mapa de Vecinos
        acta_map = {d.acta_id_oltp: d for d in DimActa.objects.all()} # Crea mapa de Actas

        # Extraer logs transaccionales
        logs = LogConsultaActa.objects.all().select_related('acta', 'vecino') # Obtiene logs con relaciones

        # Transformación y Carga
        fact_consultas = [] # Lista para almacenar objetos a crear
        for log in logs: # Recorre cada log
            dim_vecino = vecino_map.get(log.vecino_id) # Busca dimensión vecino
            dim_acta = acta_map.get(log.acta_id) # Busca dimensión acta

            if dim_vecino and dim_acta: # Si ambas dimensiones existen
                fact_consultas.append(FactConsultaActa( # Crea objeto Fact
                    vecino=dim_vecino,
                    acta=dim_acta,
                    fecha_consulta=log.fecha_consulta
                ))
                
        FactConsultaActa.objects.bulk_create(fact_consultas) # Inserta masivamente en BD

# FIN DE FUNCIÓN AUXILIAR

class DefaultPagination(PageNumberPagination): # Configuración de paginación por defecto
    page_size = 20 # Elementos por página
    page_size_query_param = "page_size" # Parámetro para cambiar tamaño
    max_page_size = 100 # Máximo permitido
    
class ReunionViewSet(viewsets.ReadOnlyModelViewSet): # ViewSet de solo lectura para Reuniones
    serializer_class = ReunionSerializer # Define serializador
    permission_classes = [permissions.AllowAny] # Permite acceso a cualquiera
    pagination_class = DefaultPagination # Usa paginación definida
    filter_backends = [filters.SearchFilter, filters.OrderingFilter] # Filtros de búsqueda y orden
    search_fields = ["titulo", "tabla", "tipo"] # Campos buscables
    ordering_fields = ["fecha", "titulo"] # Campos ordenables

    def get_queryset(self): # Personaliza la consulta base
        qs = (
            Reunion.objects.all()
            .select_related("acta") # Optimiza consulta de acta
            .annotate(asistentes_count=Count("asistentes")) # Cuenta asistentes
            .order_by("-fecha") # Ordena por fecha descendente
        )

        estado = self.request.query_params.get("estado") # Obtiene parámetro estado
        if not estado:
            return qs # Si no hay filtro, devuelve todo

        # Filtra según el estado solicitado
        if estado == "programada":
            return qs.filter(estado=EstadoReunion.PROGRAMADA)
        if estado == "en_curso":
            return qs.filter(estado=EstadoReunion.EN_CURSO)
        if estado == "realizada":
            return qs.filter(estado=EstadoReunion.REALIZADA)
        return qs

class ActaViewSet(viewsets.ReadOnlyModelViewSet): # ViewSet de solo lectura para Actas
    serializer_class = ActaSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = DefaultPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["contenido", "reunion__titulo"]
    ordering_fields = ["reunion__fecha"]

    def get_queryset(self):
        qs = Acta.objects.select_related("reunion").order_by("-reunion__fecha")
        reunion_id = self.request.query_params.get("reunion")
        if reunion_id: # Filtra por ID de reunión si se proporciona
            qs = qs.filter(reunion_id=reunion_id)
        search = self.request.query_params.get("search")
        if search: # Filtra por texto en contenido o título
            qs = qs.filter(Q(contenido__icontains=search) | Q(reunion__titulo__icontains=search))
        return qs
    
    # --- ACCIÓN PARA REGISTRAR LA CONSULTA  ---
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="consultar")
    def registrar_consulta(self, request, pk=None):
        try:
            acta = Acta.objects.get(pk=pk) # Busca el acta
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
 

class AsistenciaViewSet(viewsets.ReadOnlyModelViewSet): # ViewSet para Asistencias
    queryset = Asistencia.objects.select_related("reunion", "vecino")
    serializer_class = AsistenciaSerializer
    permission_classes = [IsAuthenticated] # Requiere autenticación

    def get_queryset(self):
        qs = super().get_queryset()
        reunion_id = self.request.query_params.get("reunion")
        if reunion_id: # Filtra por reunión
            qs = qs.filter(reunion_id=reunion_id)
        return qs

    @action(detail=False, methods=["get"], url_path="mis")
    def mis_asistencias(self, request): # Endpoint para ver asistencias propias
        user = request.user
        if not user.is_authenticated:
            qs = self.get_queryset().none()
        else:
            qs = self.get_queryset().filter(vecino=user) # Filtra por usuario actual
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)