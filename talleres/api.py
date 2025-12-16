from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication, SessionAuthentication

from .models import Taller, Inscripcion
from .serializers import TallerSerializer


class TallerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TallerSerializer

    # Lectura pública; acciones POST piden login (token)
    permission_classes = [AllowAny]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def get_queryset(self):
        return (
            Taller.objects.filter(estado=Taller.Estado.PROGRAMADO)
            .annotate(inscritos_count=Count("inscripcion"))
            .order_by("fecha_inicio")
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def inscribir(self, request, pk=None):
        taller = self.get_object()
        user = request.user

        if Inscripcion.objects.filter(vecino=user, taller=taller).exists():
            return Response({"detail": "Ya estás inscrito en este taller."}, status=400)

        # OJO: cupos_disponibles es un método del serializer, no un campo del modelo.
        inscritos = Inscripcion.objects.filter(taller=taller).count()
        if inscritos >= taller.cupos_totales:
            return Response({"detail": "No hay cupos disponibles."}, status=400)

        Inscripcion.objects.create(vecino=user, taller=taller)

        # ✅ Re-consulta desde el queryset con annotate (para que inscritos_count quede bien)
        taller = self.get_queryset().get(pk=taller.pk)

        # ✅ CLAVE: usar self.get_serializer -> incluye context={'request': request}
        serializer = self.get_serializer(taller)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def desinscribir(self, request, pk=None):
        taller = self.get_object()
        user = request.user

        Inscripcion.objects.filter(vecino=user, taller=taller).delete()

        taller = self.get_queryset().get(pk=taller.pk)
        serializer = self.get_serializer(taller)
        return Response(serializer.data, status=status.HTTP_200_OK)
