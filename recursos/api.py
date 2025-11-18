# recursos/api.py
from rest_framework import viewsets, permissions, filters
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import Recurso,SolicitudReserva
from .serializers import RecursoSerializer,SolicitudReservaSerializer, CrearSolicitudSerializer
from .permissions import EsAdminOSectretaria  
from rest_framework.decorators import action           
from rest_framework.response import Response 
from rest_framework import viewsets, permissions, filters, status
class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
class RecursoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Solo lectura: lista y detalle de recursos.
    Filtros:
      - ?search=texto (busca por nombre/descripcion)
      - El campo 'disponible' en la respuesta ahora es calculado.
    """
    queryset = Recurso.objects.all().order_by("nombre")
    serializer_class = RecursoSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    
    # El SearchFilter maneja el parámetro ?search=
    filter_backends = [filters.SearchFilter] 
    search_fields = ["nombre", "descripcion"]

    def get_queryset(self):
        # 💡 CAMBIO CRÍTICO: Eliminamos la lógica de filtro por 'disponible'
        qs = super().get_queryset()
        
        # El SearchFilter aplicado automáticamente por filter_backends ya filtra por 'search'.
        # No necesitamos el bloque de 'disponible' aquí, ya que el cálculo se hace en el Serializer.
        # Si la aplicación móvil necesita filtrar por disponibilidad, deberá hacerlo en el cliente.
        
        # El ViewSet ahora simplemente devuelve todos los recursos (filtrados por search si se usa).
        return qs
class SolicitudReservaViewSet(viewsets.ModelViewSet):
    queryset = SolicitudReserva.objects.all() # Definición base necesaria
    permission_classes = [permissions.IsAuthenticated] # Asegura que esté logueado
    serializer_class = SolicitudReservaSerializer 
    
    def get_queryset(self):
        """
        Filtra las solicitudes para que cada usuario vea SOLO las suyas.
        Si es admin y envía ?todas=1, puede ver todo.
        """
        user = self.request.user
        qs = SolicitudReserva.objects.select_related('recurso', 'solicitante').order_by("-creado_el")

        # 1. Verificar si la app envía el parámetro 'todas' (para admins)
        # Tu app Android envía: @Query("todas") todas: Int?
        ver_todas = self.request.query_params.get('todas')

        # 2. Lógica de filtrado
        if ver_todas == '1' and (user.is_superuser or user.is_staff):
            # Si es admin y explícitamente pide ver todas, devolvemos todo
            return qs
        
        # 3. Por defecto: DEVOLVER SOLO LO DEL USUARIO ACTUAL
        return qs.filter(solicitante=user)

    def get_serializer_class(self):
        if self.action == "create":
            return CrearSolicitudSerializer 
        return SolicitudReservaSerializer

    def perform_create(self, serializer):
        serializer.save(solicitante=self.request.user)

    def create(self, request, *args, **kwargs):
        # ... (Tu código create existente se mantiene igual) ...
        input_serializer = self.get_serializer(data=request.data) 
        input_serializer.is_valid(raise_exception=True)
        self.perform_create(input_serializer)
        output_serializer = SolicitudReservaSerializer(input_serializer.instance)
        headers = self.get_success_headers(output_serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)