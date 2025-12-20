"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Definición del ViewSet para la API de Talleres. Proporciona endpoints 
               para listar talleres disponibles, ver detalles e inscribirse/desinscribirse.
--------------------------------------------------------------------------------
"""
# talleres/api.py
from rest_framework import viewsets, permissions, status  # Importa clases base de DRF
from rest_framework.decorators import action  # Decorador para acciones personalizadas
from rest_framework.response import Response  # Objeto de respuesta HTTP
from rest_framework.permissions import IsAuthenticated, AllowAny  # Permisos
from rest_framework.authentication import TokenAuthentication, SessionAuthentication  # Autenticación
from django.shortcuts import get_object_or_404  # Helper para obtener objeto o 404
from django.db.models import Count # <-- Importación necesaria para optimización de consultas
from .models import Taller, Inscripcion  # Importa modelos
from .serializers import TallerSerializer  # Importa serializador

class TallerViewSet(viewsets.ReadOnlyModelViewSet):
    # Define el serializador a usar
    serializer_class = TallerSerializer

    # Permite lectura pública (lista/detalle), pero las acciones POST pedirán login
    permission_classes = [AllowAny]
    # Soporta autenticación por Token (Móvil) y Sesión (Web)
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    
    def get_queryset(self):
        """
        Sobrescribe el queryset para:
        1. Solo mostrar talleres con estado 'PROGRAMADO'.
        2. Optimizar contando los inscritos en la misma consulta (annotate).
        """
        # Filtra por el estado PROGRAMADO (que son los disponibles para ver/inscribirse)
        return Taller.objects.filter(
            estado=Taller.Estado.PROGRAMADO
        ).annotate(
            inscritos_count=Count('inscripcion')  # Agrega campo calculado con total de inscritos
        ).order_by("fecha_inicio") # Ordenamos por fecha de inicio para mejor UX
    
    # Endpoint para inscribirse en un taller (POST /api/talleres/{id}/inscribir/)
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def inscribir(self, request, pk=None):
        taller = self.get_object()  # Obtiene el taller
        user = request.user  # Obtiene el usuario autenticado

        # Verifica si ya está inscrito
        if taller.inscripcion_set.filter(vecino=user).exists():
            return Response({"detail": "Ya estás inscrito en este taller."}, status=400)

        # Verifica disponibilidad de cupos (usando propiedad del modelo)
        if taller.cupos_disponibles <= 0:
            return Response({"detail": "No hay cupos disponibles."}, status=400)

        # Crea la inscripción
        Inscripcion.objects.create(vecino=user, taller=taller)
        taller.refresh_from_db()  # Recarga el objeto para actualizar contadores
        
        #  CORRECCIÓN: Pasar el contexto de la request al serializador para que 'esta_inscrito' se calcule bien.
        return Response(TallerSerializer(taller, context={'request': request}).data, status=status.HTTP_201_CREATED)

    # Endpoint para desinscribirse (POST /api/talleres/{id}/desinscribir/)
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def desinscribir(self, request, pk=None):
        taller = self.get_object()
        user = request.user
        # Borra la inscripción si existe
        Inscripcion.objects.filter(vecino=user, taller=taller).delete()
        taller.refresh_from_db()
        
        #  CORRECCIÓN: Pasar el contexto de la request al serializador.
        return Response(TallerSerializer(taller, context={'request': request}).data)