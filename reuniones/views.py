"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Controladores (vistas) para la interfaz web. Maneja la lógica de 
               negocio para crear reuniones, gestionar actas, cambiar estados, 
               generar PDFs y procesar subida de audios.
--------------------------------------------------------------------------------
"""
from asgiref.sync import sync_to_async
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from datetime import timedelta

from .models import Reunion, Asistencia, Acta, EstadoReunion
from .forms import ReunionForm, ActaForm, CalificacionActaForm
from core.authz import role_required
from core.models import Perfil

from .tasks import procesar_audio_vosk
from .tasks import enviar_notificacion_acta_aprobada

import logging
from usuarios.utils import enviar_correo_via_webhook

logger = logging.getLogger(__name__)
User = get_user_model()


def _pdf_bytes_desde_xhtml(template_path: str, context: dict) -> bytes:
    """
    Renderiza un template HTML a PDF (bytes) usando xhtml2pdf.
    Devuelve bytes del PDF listo para adjuntar.
    """
    template = get_template(template_path)
    html = template.render(context)

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), dest=result, encoding="UTF-8")

    if not pdf.err:
        return result.getvalue()

    logger.error(f"Error al generar PDF: {pdf.err}")
    return b""


# ---------------------------
# Vistas de Reuniones
# ---------------------------

@login_required
@role_required("reuniones", "view")
def reunion_list(request): # Vista de lista de reuniones con filtros
    estado_query = request.GET.get("estado", "programada")

    if estado_query == "realizada":
        reuniones = Reunion.objects.filter(estado=EstadoReunion.REALIZADA).order_by("-fecha")
        titulo = "Reuniones Realizadas"
    elif estado_query == "en_curso":
        reuniones = Reunion.objects.filter(estado=EstadoReunion.EN_CURSO).order_by("-fecha")
        titulo = "Reuniones En Curso"
    elif estado_query == "cancelada":
        reuniones = Reunion.objects.filter(estado=EstadoReunion.CANCELADA).order_by("-fecha")
        titulo = "Reuniones Canceladas"
    else:
        estado_query = "programada"
        reuniones = Reunion.objects.filter(estado=EstadoReunion.PROGRAMADA).order_by("fecha")
        titulo = "Reuniones Programadas"

    context = {
        "reuniones": reuniones,
        "titulo": titulo,
        "estado_actual": estado_query
    }
    return render(request, "reuniones/reunion_list.html", context)


@login_required
@role_required("reuniones", "create")
def reunion_create(request): # Vista para crear reunión
    if request.method == "POST":
        form = ReunionForm(request.POST)
        if form.is_valid():
            reunion = form.save(commit=False)
            reunion.creada_por = request.user
            reunion.save()
            messages.success(request, "Reunión creada exitosamente.")
            return redirect("reuniones:lista_reuniones")
    else:
        form = ReunionForm(initial={"fecha": timezone.now() + timedelta(days=1)})

    return render(request, "reuniones/reunion_form.html", {"form": form})


@login_required
@role_required("reuniones", "view")
def reunion_detail(request, pk): # Vista de detalle de reunión
    reunion = get_object_or_404(Reunion, pk=pk)

    try:
        acta = reunion.acta
        acta_form = ActaForm(instance=acta)
    except Acta.DoesNotExist:
        acta = None
        acta_form = ActaForm(initial={"reunion": reunion})

    asistentes = Asistencia.objects.filter(reunion=reunion, presente=True)

    id_asistentes_usuarios = asistentes.values_list("vecino__id", flat=True)
    vecinos_para_email = Perfil.objects.all().exclude(
        usuario__id__in=id_asistentes_usuarios
    ).select_related("usuario")

    context = {
        "reunion": reunion,
        "acta": acta,
        "acta_form": acta_form,
        "asistentes": asistentes,
        "vecinos_para_email": vecinos_para_email,
        "total_vecinos": Perfil.objects.all().count(),
    }
    return render(request, "reuniones/reunion_detail.html", context)


# ---------------------------
# Vistas de Acta
# ---------------------------

@login_required
@role_required("actas", "edit")
def acta_edit(request, pk): # Redirección a detalle para editar acta
    return redirect("reuniones:detalle_reunion", pk=pk)


@require_POST
@login_required
@role_required("actas", "edit")
def guardar_borrador_acta(request, pk): # Guardar borrador de acta
    reunion = get_object_or_404(Reunion, pk=pk)

    try:
        acta = reunion.acta
        form = ActaForm(request.POST, instance=acta)
    except Acta.DoesNotExist:
        form = ActaForm(request.POST)

    if form.is_valid():
        acta_guardada = form.save(commit=False)
        acta_guardada.reunion = reunion
        acta_guardada.save()
        messages.success(request, "Borrador del acta guardado.")
    else:
        messages.error(request, "Error al guardar el borrador.")

    return redirect("reuniones:detalle_reunion", pk=pk)


@require_POST
@login_required
@role_required("actas", "approve")
def aprobar_borrador_acta(request, pk): # Aprobar acta (finalizar edición)
    reunion = get_object_or_404(Reunion, pk=pk)

    if reunion.estado != EstadoReunion.REALIZADA:
        messages.error(request, "No se puede aprobar un acta de una reunión que no ha finalizado.")
        return redirect("reuniones:detalle_reunion", pk=pk)

    try:
        acta = reunion.acta
        acta.aprobada = True
        acta.aprobado_por = request.user
        acta.aprobado_en = timezone.now()
        acta.save()

        # Notificación async (si Celery está activo)
        try:
            enviar_notificacion_acta_aprobada.delay(acta.pk)
        except Exception as e:
            logger.error(f"Error al encolar notificación acta aprobada: {e}")

        messages.success(request, "El acta ha sido aprobada oficialmente.")
    except Acta.DoesNotExist:
        messages.error(request, "No se puede aprobar un acta que no existe.")

    return redirect("reuniones:detalle_reunion", pk=pk)


@require_POST
@login_required
@role_required("actas", "edit")
def rechazar_acta(request, pk): # Rechazar acta (volver a borrador)
    reunion = get_object_or_404(Reunion, pk=pk)

    try:
        acta = reunion.acta
        acta.aprobada = False
        acta.aprobado_por = None
        acta.aprobado_en = None
        acta.save()
        messages.info(request, "Se ha quitado la aprobación del acta. Vuelve a estar en modo borrador.")
    except Acta.DoesNotExist:
        messages.error(request, "No se puede rechazar un acta que no existe.")

    return redirect("reuniones:detalle_reunion", pk=pk)


# ---------------------------
# Vistas de Asistencia
# ---------------------------

@login_required
@role_required("reuniones", "asistencia")
def asistencia_list(request, pk): # Gestión masiva de asistencia
    reunion = get_object_or_404(Reunion, pk=pk)
    vecinos = Perfil.objects.all().select_related("usuario").order_by("usuario__username")

    if request.method == "POST":
        presentes_pks = request.POST.getlist("presentes")
        presentes_set = set(str(pk) for pk in presentes_pks)

        for perfil in vecinos:
            esta_presente = str(perfil.pk) in presentes_set
            Asistencia.objects.update_or_create(
                reunion=reunion,
                vecino=perfil.usuario,
                defaults={"presente": esta_presente}
            )

        messages.success(request, "Asistencia guardada correctamente.")
        return redirect("reuniones:detalle_reunion", pk=pk)

    asistentes_presentes_pks = Asistencia.objects.filter(
        reunion=reunion,
        presente=True
    ).values_list("vecino__id", flat=True)

    perfiles_presentes_pks = Perfil.objects.filter(
        usuario__id__in=asistentes_presentes_pks
    ).values_list("id", flat=True)

    context = {
        "reunion": reunion,
        "titulo": f"Lista de Asistencia - {reunion.titulo}",
        "vecinos": vecinos,
        "asistentes_pks": set(perfiles_presentes_pks)
    }
    return render(request, "reuniones/asistencia_list.html", context)


@require_POST
@login_required
@role_required("reuniones", "asistencia")
def registrar_asistencia_manual(request, pk): # Asistencia individual manual
    reunion = get_object_or_404(Reunion, pk=pk)
    vecino_id = request.POST.get("vecino_id")

    if not vecino_id:
        messages.error(request, "No se seleccionó ningún vecino.")
        return redirect("reuniones:lista_asistencia", pk=pk)

    perfil_vecino = get_object_or_404(Perfil, id=vecino_id)
    usuario_vecino = perfil_vecino.usuario

    asistencia, created = Asistencia.objects.get_or_create(
        reunion=reunion,
        vecino=usuario_vecino,
        defaults={"presente": True}
    )

    if created:
        messages.success(request, f"Se registró la asistencia de {perfil_vecino.usuario.get_full_name()}.")
    else:
        asistencia.presente = True
        asistencia.save()
        messages.info(request, f"{perfil_vecino.usuario.get_full_name()} ya estaba en la lista, se marcó como presente.")

    return redirect("reuniones:lista_asistencia", pk=pk)


# ---------------------------
# PDF y Correos
# ---------------------------

@login_required
@role_required("actas", "view")
def acta_export_pdf(request, pk): # Exportar acta a PDF
    reunion = get_object_or_404(Reunion, pk=pk)

    try:
        acta = reunion.acta
    except Acta.DoesNotExist:
        messages.error(request, "Esta reunión aún no tiene un acta guardada.")
        return redirect("reuniones:detalle_reunion", pk=pk)

    pdf_bytes = _pdf_bytes_desde_xhtml(
        "reuniones/acta_pdf_template.html",
        {"reunion": reunion, "acta": acta}
    )

    if not pdf_bytes:
        messages.error(request, "Error al generar el PDF.")
        return redirect("reuniones:detalle_reunion", pk=pk)

    filename = f"Acta_{slugify(getattr(reunion, 'titulo', f'reunion-{reunion.pk}'))}.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


@require_POST
@login_required
@role_required("actas", "send")
@csrf_protect
def enviar_acta_pdf_por_correo(request, pk): # Enviar acta PDF por email
    reunion = get_object_or_404(Reunion, pk=pk)

    try:
        acta = reunion.acta
    except Acta.DoesNotExist:
        return JsonResponse({"ok": False, "message": "La reunión no tiene acta"}, status=400)

    correos = request.POST.getlist("correos[]")
    if not correos:
        return JsonResponse({"ok": False, "message": "No se recibieron correos"}, status=400)

    # 1) Generar PDF
    pdf_bytes = _pdf_bytes_desde_xhtml(
        "reuniones/acta_pdf_template.html",
        {"reunion": reunion, "acta": acta}
    )
    if not pdf_bytes:
        return JsonResponse({"ok": False, "message": "Error al generar el PDF"}, status=500)

    filename = f"Acta_{slugify(getattr(reunion, 'titulo', f'reunion-{reunion.pk}'))}.pdf"

    # ✅ DEBUG: confirma que el PDF existe y tiene peso
    logger.warning(f"[ACTA EMAIL] PDF generado: {filename} | bytes={len(pdf_bytes)}")

    enviados = 0
    for correo in correos:
        ok = enviar_correo_via_webhook(
            to_email=correo,
            subject=f"Acta de Reunión: {reunion.titulo}",
            html_body=f"""
                <p>Estimado/a vecino/a,</p>
                <p>Se adjunta el acta oficial de la reunión <strong>{reunion.titulo}</strong>.</p>
                <p>Saludos cordiales,<br>La Directiva</p>
            """,
            text_body="Se adjunta acta de reunión.",
            attachment_bytes=pdf_bytes,   
            filename=filename,            
            content_type="application/pdf"
        )

        if ok:
            enviados += 1
        else:
            logger.warning(f"[ACTA EMAIL] No se pudo enviar acta a: {correo}")

    return JsonResponse({
        "ok": True,
        "message": f"Acta enviada correctamente a {enviados} destinatarios."
    })


# ---------------------------
# Cambios de estado de reunión
# ---------------------------

@require_POST
@login_required
@role_required("reuniones", "change_estado")
def iniciar_reunion(request, pk): # Iniciar reunión (cambio de estado)
    reunion = get_object_or_404(Reunion, pk=pk)

    if reunion.estado == EstadoReunion.PROGRAMADA:
        reunion.estado = EstadoReunion.EN_CURSO
        reunion.save()
        messages.success(request, f"La reunión '{reunion.titulo}' ha sido iniciada.")
    else:
        messages.warning(request, "Esta reunión no se puede iniciar.")

    return redirect("reuniones:detalle_reunion", pk=reunion.pk)


@require_POST
@login_required
@role_required("reuniones", "change_estado")
def finalizar_reunion(request, pk): # Finalizar reunión
    reunion = get_object_or_404(Reunion, pk=pk)

    if reunion.estado == EstadoReunion.EN_CURSO:
        reunion.estado = EstadoReunion.REALIZADA
        reunion.save()
        messages.success(request, f"La reunión '{reunion.titulo}' ha finalizado.")
    else:
        messages.warning(request, "Esta reunión no se puede finalizar.")

    return redirect("reuniones:detalle_reunion", pk=reunion.pk)


@require_POST
@login_required
@role_required("reuniones", "cancel")
def cancelar_reunion(request, pk): # Cancelar reunión
    reunion = get_object_or_404(Reunion, pk=pk)

    if reunion.estado == EstadoReunion.PROGRAMADA:
        reunion.estado = EstadoReunion.CANCELADA
        reunion.save()
        messages.warning(request, f"La reunión '{reunion.titulo}' ha sido cancelada.")
    else:
        messages.error(request, "Solo se pueden cancelar reuniones que están 'Programadas'.")

    return redirect("reuniones:detalle_reunion", pk=reunion.pk)


# ---------------------------
# API JSON para FullCalendar
# ---------------------------

@login_required
@role_required("reuniones", "view")
def reuniones_json_feed(request): # Feed JSON para calendario frontend
    estado_query = request.GET.get("estado", "programada").upper()

    estados_validos = {
        "PROGRAMADA": EstadoReunion.PROGRAMADA,
        "EN_CURSO": EstadoReunion.EN_CURSO,
        "REALIZADA": EstadoReunion.REALIZADA,
        "CANCELADA": EstadoReunion.CANCELADA,
    }
    estado_filtro = estados_validos.get(estado_query, EstadoReunion.PROGRAMADA)
    reuniones = Reunion.objects.filter(estado=estado_filtro)

    color_map = {
        "PROGRAMADA": "#0d6efd",
        "EN_CURSO": "#198754",
        "REALIZADA": "#6c757d",
        "CANCELADA": "#dc3545",
    }

    eventos = []
    for reunion in reuniones:
        eventos.append({
            "title": reunion.titulo,
            "start": reunion.fecha.isoformat(),
            "url": redirect("reuniones:detalle_reunion", pk=reunion.pk).url,
            "color": color_map.get(reunion.estado),
        })

    return JsonResponse(eventos, safe=False)


# ---------------------------
# Subida y procesamiento de audio (Vosk)
# ---------------------------

@require_POST
@login_required
@role_required("actas", "edit")
def subir_audio_acta(request, pk): # Subir audio para transcripción automática
    reunion = get_object_or_404(Reunion, pk=pk)

    if reunion.estado != EstadoReunion.REALIZADA:
        messages.error(request, "Solo se pueden subir audios a reuniones finalizadas.")
        return redirect("reuniones:detalle_reunion", pk=pk)

    try:
        acta = reunion.acta
    except Acta.DoesNotExist:
        messages.error(request, "La reunión no tiene un acta asociada.")
        return redirect("reuniones:detalle_reunion", pk=pk)

    if acta.aprobada:
        messages.error(request, "No se puede procesar un audio para un acta que ya está aprobada.")
        return redirect("reuniones:detalle_reunion", pk=pk)

    archivo = request.FILES.get("archivo_audio")
    if not archivo:
        messages.error(request, "No se seleccionó ningún archivo de audio.")
        return redirect("reuniones:detalle_reunion", pk=pk)

    if acta.estado_transcripcion in (Acta.ESTADO_PENDIENTE, Acta.ESTADO_PROCESANDO):
        messages.warning(request, "Ya hay un audio procesándose para esta acta.")
        return redirect("reuniones:detalle_reunion", pk=pk)

    acta.archivo_audio = archivo
    acta.estado_transcripcion = Acta.ESTADO_PENDIENTE
    acta.save()

    procesar_audio_vosk.delay(acta.pk)

    messages.success(
        request,
        "¡Audio subido! El procesamiento ha comenzado en segundo plano. "
        "El acta se actualizará al finalizar."
    )
    return redirect("reuniones:detalle_reunion", pk=pk)


@login_required
@role_required("actas", "edit")
def lista_grabaciones(request): # Listado de grabaciones disponibles
    reuniones_con_audio = Reunion.objects.filter(
        acta__archivo_audio__isnull=False
    ).exclude(
        acta__archivo_audio=""
    ).select_related("acta").order_by("-fecha")

    context = {
        "reuniones": reuniones_con_audio,
        "titulo": "Repositorio de Grabaciones (Solo Directiva)"
    }
    return render(request, "reuniones/grabaciones_list.html", context)


@login_required
def get_acta_estado(request, pk): # API para consultar estado de transcripción
    acta = get_object_or_404(Acta, pk=pk)
    return JsonResponse({
        "estado": acta.estado_transcripcion,
        "estado_display": acta.get_estado_transcripcion_display()
    })


@require_POST
@login_required
@role_required("actas", "edit")
def calificar_acta(request, pk): # Guardar calificación de precisión
    reunion = get_object_or_404(Reunion, pk=pk)

    try:
        acta = reunion.acta
        form = CalificacionActaForm(request.POST, instance=acta)
        if form.is_valid():
            form.save()
            messages.success(request, "Calificación de precisión guardada correctamente.")
        else:
            messages.error(request, "Error al guardar la calificación. Debe ser un número entre 0 y 100.")
    except Acta.DoesNotExist:
        messages.error(request, "No existe acta para calificar.")

    return redirect("reuniones:detalle_reunion", pk=pk)