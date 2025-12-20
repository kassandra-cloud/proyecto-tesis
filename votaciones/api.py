"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Definición de endpoints API para el módulo de Votaciones. 
               Maneja el listado de votaciones abiertas, la solicitud de códigos 
               MFA por correo y el registro seguro de votos.
--------------------------------------------------------------------------------
"""
from django.shortcuts import get_object_or_404  # Helper para obtener objeto o 404
from django.utils import timezone  # Utilidades de fecha y hora
from django.db import transaction  # Manejo de transacciones atómicas
from django.db.models import Count  # Funciones de agregación
from django.utils.html import strip_tags  # Limpieza de HTML para textos planos
from usuarios.utils import enviar_correo_via_webhook  # Utilidad de envío de correos
from django.conf import settings  # Configuraciones del proyecto
from django.template.loader import render_to_string  # Renderizado de templates
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Votacion, Opcion, Voto, LogIntentoVoto

def _dto_votacion(v, user):
    """
    Función auxiliar para construir el objeto de datos (DTO) de una votación.
    Incluye: opciones, estado del voto del usuario y metadatos.
    """
    # Verifica si el usuario ya votó en esta votación específica
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
        "ya_vote": bool(voto),  # Booleano: True si ya votó
        "opcion_votada_id": voto.opcion_id if voto else None,  # ID de la opción elegida
    }


@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def abiertas(request):
    """
    Endpoint: Lista de votaciones activas y abiertas para la app móvil.
    """
    # Filtra votaciones activas y cuya fecha de cierre sea futura
    qs = (
        Votacion.objects.filter(
            activa=True,
            fecha_cierre__gt=timezone.now(),
        )
        .prefetch_related("opciones", "opciones__votos")  # Optimización de consulta
    )
    # Transforma los objetos a diccionarios usando el helper
    data = [_dto_votacion(v, request.user) for v in qs]
    return Response(data)

@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def solicitar_codigo_voto(request):
    """
    Endpoint: Genera un código de seguridad (MFA) y lo envía al correo del usuario.
    """
    user = request.user

    # Validación 1: El usuario debe tener un perfil asociado
    if not hasattr(user, "perfil"):
        return Response(
            {"ok": False, "mensaje": "El usuario no tiene perfil asociado."},
            status=400,
        )

    # Validación 2: El usuario debe tener correo
    if not user.email:
        return Response(
            {"ok": False, "mensaje": "El usuario no tiene correo registrado."},
            status=400,
        )

    # Genera el código en el perfil del usuario
    codigo = user.perfil.generar_mfa()

    subject = "Código de Seguridad para Votación"
    nombre = (user.first_name or user.username or "Vecino").strip()

    # Prepara el contexto para el correo
    contexto = {
        'nombre': nombre,
        'codigo': codigo
    }
    
    # Renderiza la plantilla HTML del correo
    html_body = render_to_string('votaciones/email_codigo_voto.html', contexto)
    
    # Genera versión en texto plano
    text_body = strip_tags(html_body)

    # Envía el correo usando el webhook configurado
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
@transaction.atomic  # Asegura integridad de la base de datos
def votar(request, pk: int):
    """
    Endpoint: Registra el voto del usuario.
    Requiere código MFA válido. Registra intentos fallidos para auditoría.
    """
    v = get_object_or_404(Votacion, pk=pk)
    user = request.user

    opcion_id = request.data.get("opcion_id")
    codigo = request.data.get("codigo")

    # Función interna para registrar fallos en el log
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
            pass  # Si falla el log, no interrumpir la respuesta

    # 1. Validaciones de entrada
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

    # 2. Validar código MFA contra el perfil del usuario
    if not user.perfil.validar_mfa(codigo):
        log_fallo("Código incorrecto o expirado")
        return Response(
            {"ok": False, "mensaje": "Código incorrecto o expirado"}, status=400
        )

    # 3. Validar estado de la votación
    if not (v.activa and v.fecha_cierre > timezone.now()):
        log_fallo("La votación ya cerró")
        return Response(
            {"ok": False, "mensaje": "La votación ya cerró"}, status=400
        )

    # 4. Registrar el voto
    opcion = get_object_or_404(Opcion, pk=opcion_id, votacion=v)

    # Elimina voto anterior si existía (permite cambio de opinión)
    Voto.objects.filter(votante=user, opcion__votacion=v).delete()
    # Crea el nuevo voto
    Voto.objects.create(votante=user, opcion=opcion)

    # Invalida el código MFA usado
    user.perfil.mfa_code = None
    user.perfil.save()

    # Registra intento exitoso en el log
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
    Vista API para consultar los resultados agregados de una votación.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        v = get_object_or_404(Votacion, pk=pk)

        # Agrupa y cuenta los votos por opción
        agregados = (
            Voto.objects.filter(opcion__votacion=v)
            .values("opcion_id")
            .annotate(c=Count("id"))
        )
        # Crea diccionario {opcion_id: cantidad}
        counts = {row["opcion_id"]: row["c"] for row in agregados}

        opciones = []
        total = 0
        # Construye la lista final de resultados
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