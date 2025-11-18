# proyecto_tesis/votaciones/api.py
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Votacion, Opcion, Voto
from django.shortcuts import get_object_or_404
from django.db.models import Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView  # ← IMPORTANTE
from rest_framework.authentication import TokenAuthentication, SessionAuthentication  # ← AÑADE ESTO
from .models import Votacion, Opcion, Voto
from django.db import transaction
from django.core.mail import send_mail 
from django.conf import settings
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
def solicitar_codigo_voto(request):
    user = request.user
    
    # Generar el código
    codigo = user.perfil.generar_mfa()
    
    # --- ACTIVACIÓN DEL ENVÍO DE CORREO REAL ---
    subject = f"Tu código de votación: {codigo}"
    message = f"""
    Hola {user.first_name},
    
    Estás a punto de emitir un voto en la plataforma vecinal.
    Tu código de seguridad es:
    
    {codigo}
    
    Este código expira en 5 minutos.
    Si no fuiste tú, por favor ignora este correo.
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL, # Remitente (ej: tu_correo@gmail.com)
            [user.email],                # Destinatario (correo del usuario registrado)
            fail_silently=False,
        )
        print(f"✅ Correo enviado a {user.email} con el código {codigo}") 
        return Response({"ok": True, "mensaje": f"Código enviado a {user.email}"})
        
    except Exception as e:
        print(f"❌ Error al intentar enviar correo: {e}")
        # Retorna 500 y un mensaje descriptivo para la App
        return Response({"ok": False, "mensaje": "Error en el servidor al enviar el correo. Revise la configuración SMTP."}, status=500)

@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@transaction.atomic
def votar(request, pk: int):
    """
    Ahora requiere 'opcion_id' Y 'codigo' para procesar el voto.
    """
    v = get_object_or_404(Votacion, pk=pk)
    user = request.user
    
    # 1. Validar datos de entrada
    opcion_id = request.data.get("opcion_id")
    codigo = request.data.get("codigo") # <--- NUEVO CAMPO
    
    if not opcion_id:
        return Response({"ok": False, "mensaje": "Falta seleccionar una opción"}, status=400)
    
    if not codigo:
        return Response({"ok": False, "mensaje": "Falta el código de verificación"}, status=400)

    # 2. VALIDAR EL CÓDIGO DE SEGURIDAD
    if not user.perfil.validar_mfa(codigo):
        return Response({"ok": False, "mensaje": "Código incorrecto o expirado"}, status=400)

    # 3. Validar votación abierta
    if not (v.activa and v.fecha_cierre > timezone.now()):
        return Response({"ok": False, "mensaje": "La votación ya cerró"}, status=400)

    # 4. Registrar el voto
    opcion = get_object_or_404(Opcion, pk=opcion_id, votacion=v)
    
    # Borrar voto anterior si existe (permite cambiar de opinión)
    Voto.objects.filter(votante=user, opcion__votacion=v).delete()
    Voto.objects.create(votante=user, opcion=opcion)
    
    # Quemar el código para que no se use de nuevo
    user.perfil.mfa_code = None
    user.perfil.save()

    return Response({"ok": True, "mensaje": "Voto registrado exitosamente"})
class ResultadosView(APIView):
    # Fuerza autenticación por Token (y opcionalmente sesión)
    authentication_classes = [TokenAuthentication, SessionAuthentication]  # ← CLAVE
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        v = get_object_or_404(Votacion, pk=pk)

        agregados = (
            Voto.objects.filter(opcion__votacion=v)
            .values("opcion_id")
            .annotate(c=Count("id"))
        )
        counts = {row["opcion_id"]: row["c"] for row in agregados}

        opciones = []
        total = 0
        for o in Opcion.objects.filter(votacion=v).values("id", "texto"):  # cambia "texto" si tu campo se llama distinto
            votos = counts.get(o["id"], 0)
            total += votos
            opciones.append({"id": o["id"], "texto": o["texto"], "votos": votos})

        return Response({"votacion_id": v.id, "total_votos": total, "opciones": opciones})