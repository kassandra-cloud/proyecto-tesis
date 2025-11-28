# talleres/api.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from django.shortcuts import get_object_or_404
from django.db.models import Count # <-- Importación necesaria para optimización
from .models import Taller, Inscripcion
from .serializers import TallerSerializer

class TallerViewSet(viewsets.ReadOnlyModelViewSet):
    # Eliminamos el atributo 'queryset' de clase
    serializer_class = TallerSerializer

    # Lectura pública; acciones POST piden login (token)
    permission_classes = [AllowAny]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    
    def get_queryset(self):
        """
        Sobrescribe el queryset para:
        1. Solo mostrar talleres con estado 'PROGRAMADO'.
        2. Optimizar contando los inscritos en la misma consulta (annotate).
        """
        # Filtra por el estado PROGRAMADO (que son los disponibles)
        return Taller.objects.filter(
            estado=Taller.Estado.PROGRAMADO
        ).annotate(
            inscritos_count=Count('inscripcion')
        ).order_by("fecha_inicio") # Ordenamos por fecha de inicio para mejor UX
    
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def inscribir(self, request, pk=None):
        taller = self.get_object()
        user = request.user

        if taller.inscripcion_set.filter(vecino=user).exists():
            return Response({"detail": "Ya estás inscrito en este taller."}, status=400)

        if taller.cupos_disponibles <= 0:
            return Response({"detail": "No hay cupos disponibles."}, status=400)

        Inscripcion.objects.create(vecino=user, taller=taller)
        taller.refresh_from_db()
        return Response(TallerSerializer(taller).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def desinscribir(self, request, pk=None):
        taller = self.get_object()
        user = request.user
        Inscripcion.objects.filter(vecino=user, taller=taller).delete()
        taller.refresh_from_db()
        return Response(TallerSerializer(taller).data)