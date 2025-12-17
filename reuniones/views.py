from asgiref.sync import sync_to_async
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
# --- IMPORTACIÓN CRÍTICA PARA CACHÉ ---
from django.views.decorators.cache import cache_page 
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
# Importamos las tareas de Celery (Asíncrono)
from .tasks import procesar_audio_vosk, generar_y_enviar_acta_pdf_async # <-- MODIFICACIÓN: Nueva tarea
from .tasks import enviar_notificacion_acta_aprobada
import logging
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from usuarios.utils import enviar_correo_via_webhook

User = get_user_model()
logger = logging.getLogger(__name__) # Usamos el logger

# La generación de PDF (I/O pesada) la mantenemos como helper, pero no se usa en el hilo principal HTTP si es para enviar correos.
def _pdf_bytes_desde_xhtml(template_path: str, context: dict) -> bytes:
    """
    Renderiza un template HTML a PDF (bytes) usando xhtml2pdf.
    Devuelve bytes del PDF listo para adjuntar.
    """
    template = get_template(template_path)
    html = template.render(context)

    result = BytesIO()
    # xhtml2pdf es un proceso intensivo de CPU
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), dest=result, encoding='UTF-8')

    if not pdf.err:
        return result.getvalue()
    logger.error(f"Error al generar PDF: {pdf.err}") # Usamos el logger
    return b""

# Vista de reuniones
# OPTIMIZACIÓN 2: Aplicamos caché de 60 segundos a la lista
@cache_page(60)
@login_required
@role_required("reuniones", "view")
def reunion_list(request): 
    estado_query = request.GET.get('estado', 'programada')

    # Base Query con Optimización N+1: precargar 'creada_por'
    base_qs = Reunion.objects.select_related('creada_por')

    if estado_query == 'realizada':
        reuniones = base_qs.filter(estado=EstadoReunion.REALIZADA).order_by('-fecha')
        titulo = "Reuniones Realizadas"
    elif estado_query == 'en_curso':
        reuniones = base_qs.filter(estado=EstadoReunion.EN_CURSO).order_by('-fecha')
        titulo = "Reuniones En Curso"
    elif estado_query == 'cancelada':
        reuniones = base_qs.filter(estado=EstadoReunion.CANCELADA).order_by('-fecha')
        titulo = "Reuniones Canceladas"
    else:
        estado_query = 'programada'
        reuniones = base_qs.filter(estado=EstadoReunion.PROGRAMADA).order_by('fecha')
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
    # Sin caché, es una vista de escritura
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


# OPTIMIZACIÓN 3: Aplicamos caché de 10 segundos al detalle (para evitar que múltiples usuarios lo recarguen)
@cache_page(10)
@login_required
@role_required("reuniones", "view")
def reunion_detail(request, pk):
    # Optimización N+1: precargar 'creada_por' y 'acta'
    reunion = get_object_or_404(
        Reunion.objects.select_related('creada_por', 'acta'), # <-- OPTIMIZACIÓN N+1
        pk=pk
    )
    
    try:
        acta = reunion.acta
        acta_form = ActaForm(instance=acta)
    except Acta.DoesNotExist:
        acta = None
        acta_form = ActaForm(initial={'reunion': reunion})

    # Consulta de asistentes (prefetch_related para acceso a Perfil.usuario)
    asistentes = Asistencia.objects.filter(reunion=reunion, presente=True).select_related('vecino') 
    
    # Optimización N+1: Evitar consulta lenta de exclusión. Usar Subquery o exclude(id__in=...)
    id_asistentes_usuarios = asistentes.values_list('vecino__id', flat=True)
    
    # Optimización: Perfil.objects.all().count() también puede ser lento si la tabla es grande. 
    # Usamos .count() pero si es muy lento, se podría cachear este valor.
    total_vecinos = Perfil.objects.count()

    # Optimización N+1: precargar 'usuario' en vecinos_para_email
    vecinos_para_email = Perfil.objects.all().exclude(
        usuario__id__in=id_asistentes_usuarios
    ).select_related('usuario') # <-- OPTIMIZACIÓN N+1
    

    context = {
        "reunion": reunion,
        "acta": acta,
        "acta_form": acta_form,
        "asistentes": asistentes,
        "vecinos_para_email": vecinos_para_email,
        "total_vecinos": total_vecinos, # Contamos a todos
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
    # Se recomienda usar get_object_or_404(Acta, reunion=reunion) para consistencia
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

        # El encolamiento de notificación ya usa Celery (.delay), lo cual es correcto (Offloading)
        try:
            # Reemplace logger.error por la importación de logging
            logger.info(f"Encolando notificación para acta PK {acta.pk}")
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
    # Optimización N+1: precargar 'usuario'
    vecinos = Perfil.objects.all().select_related('usuario').order_by('usuario__username') # <-- OPTIMIZACIÓN N+1
    
    if request.method == "POST":
        presentes_pks = request.POST.getlist('presentes') 
        presentes_pks_set = set(str(pk) for pk in presentes_pks)
        
        # Operaciones de BD dentro de un loop. Considerar transaction.atomic o bulk_update/create si la lista es grande.
        # Por ahora, se mantiene la lógica original, pero se advierte que puede ser lenta si hay muchos vecinos.
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
        # Consulta eficiente usando values_list (se mantiene)
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
    
    # Optimización: Usar select_related('usuario') en el get_object_or_404 para evitar N+1 si se accede a usuario
    perfil_vecino = get_object_or_404(Perfil.objects.select_related('usuario'), id=vecino_id) 
    usuario_vecino = perfil_vecino.usuario
    
    # get_or_create es una consulta eficiente (se mantiene)
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
    # Optimización N+1: precargar 'acta' en la reunión
    reunion = get_object_or_404(Reunion.objects.select_related('acta'), pk=pk)
    try:
        acta = reunion.acta
    except Acta.DoesNotExist:
        messages.error(request, "Esta reunión aún no tiene un acta guardada.")
        return redirect("reuniones:detalle_reunion", pk=pk)

    template_path = 'reuniones/acta_pdf_template.html'
    context = {"reunion": reunion, "acta": acta}
    
    # La generación del PDF es síncrona aquí, lo cual es aceptable ya que el usuario está esperando la descarga.
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
    """
    OPTIMIZACIÓN CRÍTICA: La generación de PDF y el envío de correos
    se mueven al background (Celery) para un tiempo de respuesta HTTP inmediato.
    """
    reunion = get_object_or_404(Reunion, pk=pk)

    correos = request.POST.getlist("correos[]")
    if not correos:
        return JsonResponse({"ok": False, "message": "No se recibieron correos"}, status=400)

    # 1. Encolar la tarea de generación de PDF y envío de correos
    try:
        generar_y_enviar_acta_pdf_async.delay(reunion.pk, correos)
        
        # 2. Devolver respuesta inmediata
        return JsonResponse({
            "ok": True,
            "message": f"Procesando envío de acta por correo a {len(correos)} destinatarios. Recibirán los correos en breve."
        })
    except Acta.DoesNotExist:
        return JsonResponse({"ok": False, "message": "La reunión no tiene acta"}, status=400)
    except Exception as e:
        logger.error(f"Error al encolar el envío de acta por correo: {e}")
        return JsonResponse({"ok": False, "message": "Error interno al iniciar el envío de correo."}, status=500)


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
    Optimizado con select_related para evitar N+1 si el modelo Reunion tuviera relaciones.
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
    
    # Optimización N+1: precargar 'creada_por' si fuera necesario en el loop (aquí no lo es, pero buena práctica)
    reuniones = Reunion.objects.filter(estado=estado_filtro).select_related('creada_por') 
    
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


@require_POST # Solo permite peticiones POST
@login_required
@role_required("actas", "edit") # Asegura que solo quien puede editar actas, pueda subir
def subir_audio_acta(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    
    # Validaciones de seguridad (se mantienen)
    if reunion.estado != EstadoReunion.REALIZADA:
        messages.error(request, "Solo se pueden subir audios a reuniones finalizadas.")
        return redirect("reuniones:detalle_reunion", pk=pk)
        
    try:
        acta = reunion.acta
    except Acta.DoesNotExist:
        # Recomendación: Crear el acta si no existe, en lugar de dar error, para una UX más suave
        messages.error(request, "La reunión no tiene un acta asociada. Cree un borrador primero.")
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
        
    # La subida del archivo a S3/Cellar es SÍNCRONA aquí (Acta.archivo_audio = archivo).
    # Para optimización extrema, esta subida también debería ser delegada a un Celery Task (junto con el procesamiento).
    # Pero por la forma en que está el modelo, la guardamos aquí y luego encolamos el procesamiento.
    acta.archivo_audio = archivo
    acta.estado_transcripcion = Acta.ESTADO_PENDIENTE
    acta.save()
    
    # Offloading: La tarea de procesamiento VOSK está correctamente encolada
    procesar_audio_vosk.delay(acta.pk)

    messages.success(request, f"¡Audio subido! El procesamiento ha comenzado en segundo plano. El acta se actualizará al finalizar.")
    return redirect("reuniones:detalle_reunion", pk=pk)

@login_required
@role_required("actas", "edit") 
def lista_grabaciones(request):
    # Optimización N+1: precargar 'acta' y 'creada_por'
    reuniones_con_audio = Reunion.objects.filter(
        acta__archivo_audio__isnull=False
    ).exclude(
        acta__archivo_audio=''
    ).select_related('acta', 'creada_por').order_by('-fecha') # <-- OPTIMIZACIÓN N+1

    context = {
        'reuniones': reuniones_con_audio,
        'titulo': 'Repositorio de Grabaciones (Solo Directiva)'
    }
    return render(request, "reuniones/grabaciones_list.html", context)


@login_required
def get_acta_estado(request, pk):
    # Consulta simple por PK (es rápida)
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