# proyecto_tesis/votaciones/api.py
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Votacion, Opcion, Voto

def _dto_votacion(v, user):
    # ¿ya votó este usuario?
    voto = Voto.objects.filter(votante=user, opcion__votacion=v).select_related('opcion').first()
    return {
        "id": v.id,
        "pregunta": v.pregunta,
        "fecha_cierre": v.fecha_cierre.isoformat(),
        "activa": v.activa,
        "esta_abierta": v.activa and v.fecha_cierre > timezone.now(),
        "opciones": [{"id": o.id, "texto": o.texto} for o in v.opciones.all()],
        "ya_vote": bool(voto),
        "opcion_votada_id": voto.opcion_id if voto else None,
    }

@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def abiertas(request):
    qs = (Votacion.objects
          .filter(activa=True, fecha_cierre__gt=timezone.now())
          .prefetch_related("opciones", "opciones__votos"))
    data = [_dto_votacion(v, request.user) for v in qs]
    return Response(data)

@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def votar(request, pk: int):
    v = get_object_or_404(Votacion, pk=pk)
    if not (v.activa and v.fecha_cierre > timezone.now()):
        return Response({"ok": False, "mensaje": "Votación cerrada"}, status=400)

    opcion_id = request.data.get("opcion_id")
    if not opcion_id:
        return Response({"ok": False, "mensaje": "Falta opcion_id"}, status=400)

    opcion = get_object_or_404(Opcion, pk=opcion_id, votacion=v)

    # Asegurar 1 voto por usuario en la votación:
    Voto.objects.filter(votante=request.user, opcion__votacion=v).delete()
    Voto.objects.create(votante=request.user, opcion=opcion)

    return Response({"ok": True, "mensaje": "Voto registrado"})

@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def resultados(request, pk: int):
    v = get_object_or_404(Votacion, pk=pk)
    filas = Opcion.objects.filter(votacion=v).annotate(votos=Count("votos"))
    total = sum(f.votos for f in filas)
    data = {
        "votacion": {"id": v.id, "pregunta": v.pregunta},
        "total_votos": total,
        "opciones": [{"opcion_id": f.id, "texto": f.texto, "votos": f.votos} for f in filas],
    }
    return Response(data)
