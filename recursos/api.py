"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Definición de los ViewSets (Controladores de API) para exponer 
               los recursos y las solicitudes de reserva a través de endpoints REST.
--------------------------------------------------------------------------------
"""
from rest_framework import viewsets, permissions, filters, status
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import Recurso, SolicitudReserva
from .serializers import RecursoSerializer, SolicitudReservaSerializer, CrearSolicitudSerializer
from .permissions import EsAdminOSectretaria  
from rest_framework.decorators import action           
from rest_framework.response import Response 

# Paginación personalizada para la API
class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"

# ViewSet para Recursos (Solo lectura para usuarios normales)
class RecursoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Solo lectura: lista y detalle de recursos.
    Filtros:
      - ?search=texto (busca por nombre/descripcion)
    """
    queryset = Recurso.objects.all().order_by("nombre")
    serializer_class = RecursoSerializer
    permission_classes = [permissions.IsAuthenticated] # Requiere estar autenticado
    pagination_class = DefaultPagination
    
    # Configuración de filtros de búsqueda
    filter_backends = [filters.SearchFilter] 
    search_fields = ["nombre", "descripcion"]

    def get_queryset(self):
        # Obtiene el queryset base
        qs = super().get_queryset()
        # Devuelve todos los recursos. La lógica de disponibilidad se maneja en el Serializer.
        return qs

# ViewSet para Solicitudes de Reserva (CRUD)
class SolicitudReservaViewSet(viewsets.ModelViewSet):
    queryset = SolicitudReserva.objects.all() 
    permission_classes = [permissions.IsAuthenticated] 
    serializer_class = SolicitudReservaSerializer 
    
    def get_queryset(self):
        """
        Filtra las solicitudes para que cada usuario vea SOLO las suyas.
        Si es admin y envía ?todas=1, puede ver todo.
        """
        user = self.request.user
        # Optimización con select_related para traer datos relacionados en una sola query
        qs = SolicitudReserva.objects.select_related('recurso', 'solicitante').order_by("-creado_el")

        # Verifica si se solicita ver todas (parametro para admins)
        ver_todas = self.request.query_params.get('todas')

        # Si es admin/staff y pide ver todas, se retorna todo el listado
        if ver_todas == '1' and (user.is_superuser or user.is_staff):
            return qs
        
        # Por defecto: Filtra solo las solicitudes del usuario actual
        return qs.filter(solicitante=user)

    def get_serializer_class(self):
        # Usa un serializador diferente para la creación (menos campos requeridos)
        if self.action == "create":
            return CrearSolicitudSerializer 
        return SolicitudReservaSerializer

    def perform_create(self, serializer):
        # Asigna automáticamente al usuario actual como solicitante
        serializer.save(solicitante=self.request.user)

    def create(self, request, *args, **kwargs):
        # Método create sobreescrito para usar headers estándar
        input_serializer = self.get_serializer(data=request.data) 
        input_serializer.is_valid(raise_exception=True)
        self.perform_create(input_serializer)
        output_serializer = SolicitudReservaSerializer(input_serializer.instance)
        headers = self.get_success_headers(output_serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)