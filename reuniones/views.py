from asgiref.sync import sync_to_async
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from django.utils.text import slugify
from django.core.mail import EmailMessage
from django.contrib.auth import get_user_model
from datetime import timedelta
from .models import Reunion, Asistencia, Acta, EstadoReunion
from .forms import ReunionForm, ActaForm, CalificacionActaForm
from core.authz import role_required
from core.models import Perfil
import json
from .tasks import procesar_audio_vosk
from .tasks import enviar_notificacion_acta_aprobada
import logging
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from usuarios.utils import enviar_correo_via_webhook

User = get_user_model()

def _pdf_bytes_desde_xhtml(template_path: str, context: dict) -> bytes:
    """
    Renderiza un template HTML a PDF (bytes) usando xhtml2pdf.
    Devuelve bytes del PDF listo para adjuntar.
    """
    template = get_template(template_path)
    html = template.render(context)

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), dest=result, encoding='UTF-8')

    if not pdf.err:
        return result.getvalue()
    print(f"Error al generar PDF: {pdf.err}")
    return b""
#Vista de reuniones
@login_required
@role_required("reuniones", "view")
def reunion_list(request): 
    estado_query = request.GET.get('estado', 'programada')

    if estado_query == 'realizada':
        reuniones = Reunion.objects.filter(estado=EstadoReunion.REALIZADA).order_by('-fecha')
        titulo = "Reuniones Realizadas"
    elif estado_query == 'en_curso':
        reuniones = Reunion.objects.filter(estado=EstadoReunion.EN_CURSO).order_by('-fecha') # <- Corregido
        titulo = "Reuniones En Curso"
    elif estado_query == 'cancelada':
        reuniones = Reunion.objects.filter(estado=EstadoReunion.CANCELADA).order_by('-fecha')
        titulo = "Reuniones Canceladas"
    else:
        estado_query = 'programada'
        reuniones = Reunion.objects.filter(estado=EstadoReunion.PROGRAMADA).order_by('fecha')
        titulo = "Reuniones Programadas"

    context = {
        'reuniones': reuniones,
        'titulo': titulo,
        'estado_actual': estado_query
    }

    return render(request, "reuniones/reunion_list.html", context)

@login_required
@role_required("reuniones", "create")
def reunion_create(request):
    if request.method == "POST":
        form = ReunionForm(request.POST)
        if form.is_valid():
            reunion = form.save(commit=False)
            reunion.creada_por = request.user
            reunion.save()
            messages.success(request, "Reunión creada exitosamente.")
            return redirect("reuniones:lista_reuniones")
    else:
        form = ReunionForm(initial={'fecha': timezone.now() + timedelta(days=1)})
    
    return render(request, "reuniones/reunion_form.html", {"form": form})


@login_required
@role_required("reuniones", "view")
def reunion_detail(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    try:
        acta = reunion.acta
        acta_form = ActaForm(instance=acta)
    except Acta.DoesNotExist:
        acta = None
        acta_form = ActaForm(initial={'reunion': reunion})

    asistentes = Asistencia.objects.filter(reunion=reunion, presente=True)
    
    id_asistentes_usuarios = asistentes.values_list('vecino__id', flat=True)
    vecinos_para_email = Perfil.objects.all().exclude(
        usuario__id__in=id_asistentes_usuarios
    ).select_related('usuario')
   

    context = {
        "reunion": reunion,
        "acta": acta,
        "acta_form": acta_form,
        "asistentes": asistentes,
        "vecinos_para_email": vecinos_para_email,
        "total_vecinos": Perfil.objects.all().count(), # Contamos a todos
    }
    return render(request, "reuniones/reunion_detail.html", context)

# Vistas de Acta

@login_required
@role_required("actas", "edit")
def acta_edit(request, pk):
    return redirect('reuniones:detalle_reunion', pk=pk)


@require_POST
@login_required
@role_required("actas", "edit")
def guardar_borrador_acta(request, pk):
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
def aprobar_borrador_acta(request, pk):
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

        # Aqui se envia la notificacion 
        try:
            enviar_notificacion_acta_aprobada.delay(acta.pk)
        except Exception as e:
            logger.error(f"Error al encolar notif acta aprobada: {e}")

        messages.success(request, "El acta ha sido aprobada oficialmente.")
    except Acta.DoesNotExist:
        messages.error(request, "No se puede aprobar un acta que no existe.")
        
    return redirect("reuniones:detalle_reunion", pk=pk)


@require_POST
@login_required
@role_required("actas", "edit")
def rechazar_acta(request, pk):
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


# Vistas de Asistencia

@login_required
@role_required("reuniones", "asistencia")
def asistencia_list(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    vecinos = Perfil.objects.all().select_related('usuario').order_by('usuario__username')
    if request.method == "POST":
        presentes_pks = request.POST.getlist('presentes') 
        presentes_pks_set = set(str(pk) for pk in presentes_pks)
        for perfil in vecinos:
            esta_presente = str(perfil.pk) in presentes_pks_set
            Asistencia.objects.update_or_create(
                reunion=reunion,
                vecino=perfil.usuario,
                defaults={'presente': esta_presente} 
            )    
        messages.success(request, "Asistencia guardada correctamente.")
        return redirect('reuniones:detalle_reunion', pk=pk)

    else:
        # Lógica para mostrar la página (GET)
        asistentes_presentes_pks = Asistencia.objects.filter(
            reunion=reunion, 
            presente=True
        ).values_list('vecino__id', flat=True)
        
        perfiles_presentes_pks = Perfil.objects.filter(
            usuario__id__in=asistentes_presentes_pks
        ).values_list('id', flat=True)

        context = {
            'reunion': reunion,
            'titulo': f'Lista de Asistencia - {reunion.titulo}',
            'vecinos': vecinos, 
            'asistentes_pks': set(perfiles_presentes_pks)
        }
        return render(request, "reuniones/asistencia_list.html", context)


@require_POST
@login_required
@role_required("reuniones", "asistencia")
def registrar_asistencia_manual(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    vecino_id = request.POST.get('vecino_id') 
    if not vecino_id:
        messages.error(request, "No se seleccionó ningún vecino.")
        return redirect('reuniones:lista_asistencia', pk=pk)
    perfil_vecino = get_object_or_404(Perfil, id=vecino_id)
    usuario_vecino = perfil_vecino.usuario
    asistencia, created = Asistencia.objects.get_or_create(
        reunion=reunion,
        vecino=usuario_vecino, 
        defaults={'presente': True} 
    )
    if created:
        messages.success(request, f"Se registró la asistencia de {perfil_vecino.usuario.get_full_name()}.")
    else:
        asistencia.presente = True
        asistencia.save()
        messages.info(request, f"{perfil_vecino.usuario.get_full_name()} ya estaba en la lista, se marcó como presente.")
        
    return redirect('reuniones:lista_asistencia', pk=pk)


# Vistas de PDF y Correos

@login_required
@role_required("actas", "view")
def acta_export_pdf(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    try:
        acta = reunion.acta
    except Acta.DoesNotExist:
        messages.error(request, "Esta reunión aún no tiene un acta guardada.")
        return redirect("reuniones:detalle_reunion", pk=pk)

    template_path = 'reuniones/acta_pdf_template.html'
    context = {"reunion": reunion, "acta": acta}
    
    pdf_bytes = _pdf_bytes_desde_xhtml(template_path, context)
    
    if not pdf_bytes:
        messages.error(request, "Error al generar el PDF.")
        return redirect("reuniones:detalle_reunion", pk=pk)

    filename = f"Acta_{slugify(getattr(reunion, 'titulo', f'reunion-{reunion.pk}'))}.pdf"
    
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response

@require_POST
@login_required
@role_required("actas", "send")
@csrf_protect
def enviar_acta_pdf_por_correo(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    try:
        acta = reunion.acta
    except Acta.DoesNotExist:
        return HttpResponseBadRequest("Esta reunión no tiene acta.")

    # ✅ ENVIAR A TODOS (presentes + no presentes)
    correos = list(
        Perfil.objects.select_related("usuario")
        .filter(usuario__is_active=True)
        .exclude(usuario__email__isnull=True)
        .exclude(usuario__email__exact="")
        .values_list("usuario__email", flat=True)
    )

    # Quitar duplicados + orden
    correos = sorted(set([c.strip() for c in correos if c and c.strip()]))

    if not correos:
        return HttpResponseBadRequest("No hay correos disponibles para enviar.")

    # Generar PDF
    template_path = "reuniones/acta_pdf_template.html"
    pdf_bytes = _pdf_bytes_desde_xhtml(template_path, {"reunion": reunion, "acta": acta})
    if not pdf_bytes:
        return HttpResponse("Error al generar el PDF", status=500)

    filename = f"Acta_{slugify(getattr(reunion, 'titulo', f'reunion-{reunion.pk}'))}.pdf"

    asunto = f"Acta de Reunión: {reunion.titulo}"
    cuerpo = (
        f"Estimado(a) vecino(a),\n\n"
        f"Adjuntamos el acta oficial de la reunión \"{reunion.titulo}\", "
        f"realizada el {reunion.fecha.strftime('%d/%m/%Y')}.\n\n"
        f"Saludos cordiales,\n"
        f"La Directiva\n"
    )

    try:
        email = EmailMessage(
            subject=asunto,
            body=cuerpo,
            to=correos,
        )
        email.attach(filename, pdf_bytes, "application/pdf")
        email.send(fail_silently=False)

        return JsonResponse({
            "ok": True,
            "message": f"Correo enviado a {len(correos)} destinatario(s)."
        })

    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return HttpResponseBadRequest(f"Error al enviar correo: {e}")


@require_POST
@login_required
@role_required("reuniones", "change_estado")
def iniciar_reunion(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    
    if reunion.estado == EstadoReunion.PROGRAMADA:
        reunion.estado = EstadoReunion.EN_CURSO
        reunion.save()
        messages.success(request, f"La reunión '{reunion.titulo}' ha sido iniciada.")
    else:
        messages.warning(request, "Esta reunión no se puede iniciar.")
        
    return redirect('reuniones:detalle_reunion', pk=reunion.pk)


@require_POST
@login_required
@role_required("reuniones", "change_estado")
def finalizar_reunion(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    
    if reunion.estado == EstadoReunion.EN_CURSO:
        reunion.estado = EstadoReunion.REALIZADA
        reunion.save()
        messages.success(request, f"La reunión '{reunion.titulo}' ha finalizado.")
    else:
        messages.warning(request, "Esta reunión no se puede finalizar.")
        
    return redirect('reuniones:detalle_reunion', pk=reunion.pk)


@require_POST
@login_required
@role_required("reuniones", "cancel")
def cancelar_reunion(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    
    if reunion.estado == EstadoReunion.PROGRAMADA:
        reunion.estado = EstadoReunion.CANCELADA
        reunion.save()
        messages.warning(request, f"La reunión '{reunion.titulo}' ha sido cancelada.")
    else:
        messages.error(request, "Solo se pueden cancelar reuniones que están 'Programadas'.")
        
    return redirect('reuniones:detalle_reunion', pk=reunion.pk)


# NUEVA VISTA DE API PARA EL CALENDARIO 
@login_required
@role_required("reuniones", "view")
def reuniones_json_feed(request):
    """
    Esta vista genera el JSON que FullCalendar necesita.
    Filtra por estado (programada, en_curso, realizada, cancelada).
    """
    estado_query = request.GET.get('estado', 'programada').upper()
    
    # Mapeo de estados a valores del modelo
    estados_validos = {
        'PROGRAMADA': EstadoReunion.PROGRAMADA,
        'EN_CURSO': EstadoReunion.EN_CURSO,
        'REALIZADA': EstadoReunion.REALIZADA,
        'CANCELADA': EstadoReunion.CANCELADA,
    }
    # Si el estado no es válido, usa PROGRAMADA por defecto
    estado_filtro = estados_validos.get(estado_query, EstadoReunion.PROGRAMADA)
    reuniones = Reunion.objects.filter(estado=estado_filtro)
    # Mapeo de colores para el calendario
    color_map = {
        'PROGRAMADA': '#0d6efd', 
        'EN_CURSO': '#198754',   
        'REALIZADA': '#6c757d',  
        'CANCELADA': '#dc3545',  
    }
    
    # Formateamos los eventos para FullCalendar
    eventos = []
    for reunion in reuniones:
        eventos.append({
            'title': reunion.titulo,
            'start': reunion.fecha.isoformat(), # Formato ISO (ej. 2025-11-13T21:00:00)
            'url': redirect('reuniones:detalle_reunion', pk=reunion.pk).url,
            'color': color_map.get(reunion.estado),
        })
        
    return JsonResponse(eventos, safe=False)



@require_POST  # Solo permite peticiones POST
@login_required
@role_required("actas", "edit") # Asegura que solo quien puede editar actas, pueda subir
def subir_audio_acta(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    
    # Validaciones de seguridad
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

    # Validación del archivo
    archivo = request.FILES.get("archivo_audio")
    if not archivo:
        messages.error(request, "No se seleccionó ningún archivo de audio.")
        return redirect("reuniones:detalle_reunion", pk=pk)
    if acta.estado_transcripcion == Acta.ESTADO_PENDIENTE or acta.estado_transcripcion == Acta.ESTADO_PROCESANDO:
        messages.warning(request, "Ya hay un audio procesándose para esta acta.")
        return redirect("reuniones:detalle_reunion", pk=pk)
    acta.archivo_audio = archivo
    acta.estado_transcripcion = Acta.ESTADO_PENDIENTE
    acta.save()
    procesar_audio_vosk.delay(acta.pk)

    messages.success(request, f"¡Audio subido! El procesamiento ha comenzado en segundo plano. El acta se actualizará al finalizar.")
    return redirect("reuniones:detalle_reunion", pk=pk)

@login_required
@role_required("actas", "edit") 
def lista_grabaciones(request):
    reuniones_con_audio = Reunion.objects.filter(
        acta__archivo_audio__isnull=False
    ).exclude(
        acta__archivo_audio=''
    ).select_related('acta').order_by('-fecha')

    context = {
        'reuniones': reuniones_con_audio,
        'titulo': 'Repositorio de Grabaciones (Solo Directiva)'
    }
    return render(request, "reuniones/grabaciones_list.html", context)


@login_required
def get_acta_estado(request, pk):
    acta = get_object_or_404(Acta, pk=pk)
    return JsonResponse({
        'estado': acta.estado_transcripcion,
        'estado_display': acta.get_estado_transcripcion_display()
    })

@require_POST
@login_required
@role_required("actas", "edit")
def calificar_acta(request, pk):
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