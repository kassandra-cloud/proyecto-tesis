# talleres/api.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from django.shortcuts import get_object_or_404
from .models import Taller, Inscripcion
from .serializers import TallerSerializer

class TallerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Taller.objects.all().order_by("nombre")
    serializer_class = TallerSerializer

    # Lectura pública; acciones POST piden login (token)
    permission_classes = [AllowAny]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

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
