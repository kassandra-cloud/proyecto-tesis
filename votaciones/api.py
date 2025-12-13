from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.db.models import Count
from django.utils.html import strip_tags
from usuarios.utils import enviar_correo_via_webhook
from django.conf import settings
from django.template.loader import render_to_string  
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from core.api_fcm import enviar_correo_via_webhook
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Votacion, Opcion, Voto, LogIntentoVoto


def _dto_votacion(v, user):
    """
    Arma un DTO de votación incluyendo:
    - opciones
    - si el usuario ya votó
    - qué opción votó
    """
    voto = (
        Voto.objects.filter(votante=user, opcion__votacion=v)
        .select_related("opcion")
        .first()
    )
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
    """
    Lista de votaciones abiertas para la app móvil.
    """
    qs = (
        Votacion.objects.filter(
            activa=True,
            fecha_cierre__gt=timezone.now(),
        )
        .prefetch_related("opciones", "opciones__votos")
    )
    data = [_dto_votacion(v, request.user) for v in qs]
    return Response(data)

@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def solicitar_codigo_voto(request):
    """
    Genera un código MFA y lo envía al correo del usuario
    utilizando una plantilla HTML profesional.
    """
    user = request.user

    # Validaciones mínimas
    if not hasattr(user, "perfil"):
        return Response(
            {"ok": False, "mensaje": "El usuario no tiene perfil asociado."},
            status=400,
        )

    if not user.email:
        return Response(
            {"ok": False, "mensaje": "El usuario no tiene correo registrado."},
            status=400,
        )

    # Generar el código
    codigo = user.perfil.generar_mfa()

    subject = "Código de Seguridad para Votación"
    nombre = (user.first_name or user.username or "Vecino").strip()

    # --- CAMBIO PRINCIPAL: Renderizado de plantilla ---
    contexto = {
        'nombre': nombre,
        'codigo': codigo
    }
    
    # Renderizamos el archivo HTML a un string
    html_body = render_to_string('votaciones/email_codigo_voto.html', contexto)
    
    # Generamos la versión de texto plano automáticamente basada en el HTML
    text_body = strip_tags(html_body)

    # Enviar por webhook
    ok = enviar_correo_via_webhook(
        to_email=user.email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )

    if ok:
        return Response({"ok": True, "mensaje": f"Código enviado a {user.email}"})

    return Response(
        {
            "ok": False,
            "mensaje": (
                "No se pudo enviar el correo (webhook). "
                "Verifique la configuración del servicio de correos."
            ),
        },
        status=500,
    )

@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@transaction.atomic
def votar(request, pk: int):
    """
    Registra un voto desde la app móvil.
    Requiere:
      - opcion_id
      - codigo (MFA enviado al correo)

    Además:
      - Traza TODOS los intentos (exitosos y fallidos) en LogIntentoVoto
        para medir el KPI 'fallos_votacion' en BI.
    """
    v = get_object_or_404(Votacion, pk=pk)
    user = request.user

    opcion_id = request.data.get("opcion_id")
    codigo = request.data.get("codigo")

    # Helper interno para loguear fallos
    def log_fallo(motivo: str):
        try:
            LogIntentoVoto.objects.create(
                votacion=v,
                usuario=user,
                fue_exitoso=False,
                motivo_fallo=motivo,
                origen="APP_MOVIL",
            )
        except Exception:
            # Nunca romper el flujo por un log
            pass

    # 1. Validar datos de entrada
    if not opcion_id:
        log_fallo("Falta seleccionar una opción")
        return Response(
            {"ok": False, "mensaje": "Falta seleccionar una opción"}, status=400
        )

    if not codigo:
        log_fallo("Falta el código de verificación")
        return Response(
            {"ok": False, "mensaje": "Falta el código de verificación"}, status=400
        )

    # 2. Validar código MFA
    if not user.perfil.validar_mfa(codigo):
        log_fallo("Código incorrecto o expirado")
        return Response(
            {"ok": False, "mensaje": "Código incorrecto o expirado"}, status=400
        )

    # 3. Validar que la votación siga abierta
    if not (v.activa and v.fecha_cierre > timezone.now()):
        log_fallo("La votación ya cerró")
        return Response(
            {"ok": False, "mensaje": "La votación ya cerró"}, status=400
        )

    # 4. Registrar el voto
    opcion = get_object_or_404(Opcion, pk=opcion_id, votacion=v)

    # Permitir cambiar de opinión: borramos voto anterior
    Voto.objects.filter(votante=user, opcion__votacion=v).delete()
    Voto.objects.create(votante=user, opcion=opcion)

    # Quemar el código MFA
    user.perfil.mfa_code = None
    user.perfil.save()

    # Registrar intento exitoso
    try:
        LogIntentoVoto.objects.create(
            votacion=v,
            usuario=user,
            fue_exitoso=True,
            motivo_fallo="",
            origen="APP_MOVIL",
        )
    except Exception:
        pass

    return Response({"ok": True, "mensaje": "Voto registrado exitosamente"})


class ResultadosView(APIView):
    """
    Devuelve resultados agregados de una votación.
    Esta vista puede ser usada por la directiva o panel web.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
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
        for o in Opcion.objects.filter(votacion=v).values("id", "texto"):
            votos = counts.get(o["id"], 0)
            total += votos
            opciones.append(
                {
                    "id": o["id"],
                    "texto": o["texto"],
                    "votos": votos,
                }
            )

        return Response(
            {
                "votacion_id": v.id,
                "pregunta": v.pregunta,
                "total_votos": total,
                "opciones": opciones,
            }
        )
