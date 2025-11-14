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
    # ... (propiedades existentes)
    
    def get_serializer_class(self):
        if self.action == "create":
            # Usar CrearSolicitudSerializer para la ENTRADA (Validación)
            return CrearSolicitudSerializer 
        # Usar SolicitudReservaSerializer para el resto (GET, SALIDA)
        return SolicitudReservaSerializer

    def perform_create(self, serializer):
        # El serializador de entrada (CrearSolicitudSerializer) no tiene el solicitante.
        serializer.save(solicitante=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Sobrescribe el método create para usar SolicitudReservaSerializer 
        (el completo) en la serialización de la respuesta 201.
        """
        # 1. Usar el serializador de ENTRADA para validar y crear.
        input_serializer = self.get_serializer(data=request.data) 
        input_serializer.is_valid(raise_exception=True)
        
        # 2. Guardar la instancia (esto llama a perform_create)
        self.perform_create(input_serializer)

        # 3. Serializar la SALIDA con el serializador COMPLETO (SolicitudReservaSerializer).
        # input_serializer.instance es la SolicitudReserva recién creada.
        output_serializer = SolicitudReservaSerializer(input_serializer.instance)

        # 4. Devolver la respuesta 201 Created con el objeto completo
        headers = self.get_success_headers(output_serializer.data)
        # Cambiamos input_serializer.data por output_serializer.data
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)