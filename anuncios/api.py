"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Define las vistas de la API (Endpoints) para la app móvil.
                       Provee acceso a los datos de anuncios en formato JSON,
                       protegido por autenticación.
--------------------------------------------------------------------------------
"""

# Importa decoradores para definir vistas API y permisos.
from rest_framework.decorators import api_view, permission_classes
# Importa la clase de permiso para requerir usuario autenticado.
from rest_framework.permissions import IsAuthenticated
# Importa el objeto Response para devolver respuestas estandarizadas.
from rest_framework.response import Response
# Importa el modelo y el serializador.
from .models import Anuncio
from .serializers import AnuncioSerializer

# Define que esta vista solo acepta peticiones GET.
@api_view(['GET'])
# Exige que el usuario envíe un token válido (esté autenticado).
@permission_classes([IsAuthenticated])
def lista_anuncios_api(request):
    """
    Entrega la lista de anuncios en formato JSON para la App Móvil.
    """
    # Consulta a la base de datos: obtiene todos los anuncios ordenados por fecha descendente.
    anuncios = Anuncio.objects.all().order_by('-fecha_creacion')
    # Serializa los datos (convierte QuerySet a tipos nativos de Python/JSON).
    # many=True indica que se está serializando una lista de objetos, no uno solo.
    serializer = AnuncioSerializer(anuncios, many=True)
    # Retorna la respuesta HTTP con los datos serializados en el cuerpo.
    return Response(serializer.data)