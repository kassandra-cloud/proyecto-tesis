# anuncios/api.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Anuncio
from .serializers import AnuncioSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lista_anuncios_api(request):
    """
    Entrega la lista de anuncios en formato JSON para la App Móvil.
    """
    # Obtenemos todos los anuncios, ordenados del más nuevo al más viejo
    anuncios = Anuncio.objects.all().order_by('-fecha_creacion')
    serializer = AnuncioSerializer(anuncios, many=True)
    return Response(serializer.data)