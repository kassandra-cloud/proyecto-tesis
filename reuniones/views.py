# reuniones/views.py
from asgiref.sync import sync_to_async
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django.core.cache import cache
from datetime import timedelta
import logging

from .models import Reunion, Asistencia, Acta, EstadoReunion
from .forms import ReunionForm, ActaForm, CalificacionActaForm
from core.authz import role_required
from core.models import Perfil
from .tasks import procesar_audio_vosk, generar_y_enviar_acta_pdf_async
from .tasks import enviar_notificacion_acta_aprobada

User = get_user_model()
logger = logging.getLogger(__name__)

# ---------------------------
# HELPERS
# ---------------------------

def _pdf_bytes_desde_xhtml(template_path: str, context: dict) -> bytes:
    template = get_template(template_path)
    html = template.render(context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), dest=result, encoding="UTF-8")
    if not pdf.err:
        return result.getvalue()
    logger.error(f"Error al generar PDF: {pdf.err}")
    return b""


def _cache_key_total_vecinos() -> str:
    return "reuniones:total_vecinos"


def _get_total_vecinos_cached() -> int:
    val = cache.get(_cache_key_total_vecinos())
    if val is None:
        val = Perfil.objects.count()
        cache.set(_cache_key_total_vecinos(), val, 60)  # 60s
    return val


# ⚠️ Si quieres invalidar caché cuando cambie el estado:
def _invalidate_reunion_list_cache():
    # cache_page usa claves internas, esto no siempre sirve.
    # Lo ideal es usar cache a mano (cache.get/cache.set) o cacheops.
    # Lo dejo como “placeholder” por si implementas caché manual.
    cache.delete(_cache_key_total_vecinos())


# ---------------------------
# VISTAS
# ---------------------------

@cache_page(60)
@login_required
@role_required("reuniones", "view")
def reunion_list(request):
    estado_query = request.GET.get("estado", "programada")

    # ✅ only() para traer menos columnas (acelera listas)
    base_qs = (
        Reunion.objects.select_related("creada_por")
        .only("id", "titulo", "fecha", "estado", "tipo", "creada_por__id", "creada_por__username")
    )

    if estado_query == "realizada":
        reuniones = base_qs.filter(estado=EstadoReunion.REALIZADA).order_by("-fecha")
        titulo = "Reuniones Realizadas"
    elif estado_query == "en_curso":
        reuniones = base_qs.filter(estado=EstadoReunion.EN_CURSO).order_by("-fecha")
        titulo = "Reuniones En Curso"
    elif estado_query == "cancelada":
        reuniones = base_qs.filter(estado=EstadoReunion.CANCELADA).order_by("-fecha")
        titulo = "Reuniones Canceladas"
    else:
        estado_query = "programada"
        reuniones = base_qs.filter(estado=EstadoReunion.PROGRAMADA).order_by("fecha")
        titulo = "Reuniones Programadas"

    return render(request, "reuniones/reunion_list.html", {
        "reuniones": reuniones,
        "titulo": titulo,
        "estado_actual": estado_query,
    })


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
        form = ReunionForm(initial={"fecha": timezone.now() + timedelta(days=1)})

    return render(request, "reuniones/reunion_form.html", {"form": form})


@cache_page(10)
@login_required
@role_required("reuniones", "view")
def reunion_detail(request, pk):
    reunion = get_object_or_404(
        Reunion.objects.select_related("creada_por", "acta"),
        pk=pk
    )

    try:
        acta = reunion.acta
        acta_form = ActaForm(instance=acta)
    except Acta.DoesNotExist:
        acta = None
        acta_form = ActaForm(initial={"reunion": reunion})

    asistentes = (
        Asistencia.objects.filter(reunion=reunion, presente=True)
        .select_related("vecino")
        .only("id", "vecino__id", "vecino__username", "presente")
    )

    id_asistentes_usuarios = list(asistentes.values_list("vecino__id", flat=True))

    # ✅ total_vecinos cacheado
    total_vecinos = _get_total_vecinos_cached()

    # ✅ clave: NO traer a todos los vecinos (eso revienta el tiempo).
    # Limita a 200 para la UI (puedes aumentar/disminuir)
    vecinos_para_email = (
        Perfil.objects.exclude(usuario__id__in=id_asistentes_usuarios)
        .select_related("usuario")
        .only("id", "usuario__id", "usuario__username", "usuario__first_name", "usuario__last_name", "usuario__email")
        .order_by("usuario__username")[:200]
    )

    return render(request, "reuniones/reunion_detail.html", {
        "reunion": reunion,
        "acta": acta,
        "acta_form": acta_form,
        "asistentes": asistentes,
        "vecinos_para_email": vecinos_para_email,
        "total_vecinos": total_vecinos,
    })


@login_required
@role_required("actas", "edit")
def acta_edit(request, pk):
    return redirect("reuniones:detalle_reunion", pk=pk)


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
        acta.save(update_fields=["aprobada", "aprobado_por", "aprobado_en"])

        try:
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
        acta.save(update_fields=["aprobada", "aprobado_por", "aprobado_en"])
        messages.info(request, "Se ha quitado la aprobación del acta. Vuelve a estar en modo borrador.")
    except Acta.DoesNotExist:
        messages.error(request, "No se puede rechazar un acta que no existe.")
    return redirect("reuniones:detalle_reunion", pk=pk)


@login_required
@role_required("reuniones", "asistencia")
def asistencia_list(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)

    vecinos = (
        Perfil.objects.select_related("usuario")
        .only("id", "usuario__id", "usuario__username", "usuario__first_name", "usuario__last_name")
        .order_by("usuario__username")
    )

    if request.method == "POST":
        presentes_pks = set(request.POST.getlist("presentes"))
        presentes_ids = set(int(x) for x in presentes_pks if str(x).isdigit())

        # ✅ Cargar asistencias existentes de una vez
        existentes = {
            a.vecino_id: a
            for a in Asistencia.objects.filter(reunion=reunion).only("id", "vecino_id", "presente")
        }

        to_update = []
        to_create = []

        for perfil in vecinos:
            uid = perfil.usuario_id
            presente = uid in presentes_ids

            if uid in existentes:
                obj = existentes[uid]
                if obj.presente != presente:
                    obj.presente = presente
                    to_update.append(obj)
            else:
                to_create.append(Asistencia(reunion=reunion, vecino_id=uid, presente=presente))

        if to_update:
            Asistencia.objects.bulk_update(to_update, ["presente"], batch_size=1000)
        if to_create:
            Asistencia.objects.bulk_create(to_create, batch_size=1000)

        messages.success(request, "Asistencia guardada correctamente.")
        return redirect("reuniones:detalle_reunion", pk=pk)

    asistentes_presentes_pks = Asistencia.objects.filter(
        reunion=reunion,
        presente=True
    ).values_list("vecino__id", flat=True)

    perfiles_presentes_pks = Perfil.objects.filter(
        usuario__id__in=asistentes_presentes_pks
    ).values_list("id", flat=True)

    return render(request, "reuniones/asistencia_list.html", {
        "reunion": reunion,
        "titulo": f"Lista de Asistencia - {reunion.titulo}",
        "vecinos": vecinos,
        "asistentes_pks": set(perfiles_presentes_pks),
    })


@require_POST
@login_required
@role_required("reuniones", "asistencia")
def registrar_asistencia_manual(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    vecino_id = request.POST.get("vecino_id")
    if not vecino_id:
        messages.error(request, "No se seleccionó ningún vecino.")
        return redirect("reuniones:lista_asistencia", pk=pk)

    perfil_vecino = get_object_or_404(Perfil.objects.select_related("usuario"), id=vecino_id)
    usuario_vecino = perfil_vecino.usuario

    asistencia, created = Asistencia.objects.get_or_create(
        reunion=reunion,
        vecino=usuario_vecino,
        defaults={"presente": True}
    )
    if created:
        messages.success(request, f"Se registró la asistencia de {perfil_vecino.usuario.get_full_name()}.")
    else:
        if not asistencia.presente:
            asistencia.presente = True
            asistencia.save(update_fields=["presente"])
        messages.info(request, f"{perfil_vecino.usuario.get_full_name()} ya estaba en la lista, se marcó como presente.")

    return redirect("reuniones:detalle_reunion", pk=pk)


@login_required
@role_required("actas", "view")
def acta_export_pdf(request, pk):
    reunion = get_object_or_404(Reunion.objects.select_related("acta"), pk=pk)
    try:
        acta = reunion.acta
    except Acta.DoesNotExist:
        messages.error(request, "Esta reunión aún no tiene un acta guardada.")
        return redirect("reuniones:detalle_reunion", pk=pk)

    template_path = "reuniones/acta_pdf_template.html"
    context = {"reunion": reunion, "acta": acta}

    pdf_bytes = _pdf_bytes_desde_xhtml(template_path, context)
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
def enviar_acta_pdf_por_correo(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    correos = request.POST.getlist("correos[]")
    if not correos:
        return JsonResponse({"ok": False, "message": "No se recibieron correos"}, status=400)

    try:
        generar_y_enviar_acta_pdf_async.delay(reunion.pk, correos)
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
        reunion.save(update_fields=["estado"])
        _invalidate_reunion_list_cache()
        messages.success(request, f"La reunión '{reunion.titulo}' ha sido iniciada.")
    else:
        messages.warning(request, "Esta reunión no se puede iniciar.")
    return redirect("reuniones:detalle_reunion", pk=reunion.pk)


@require_POST
@login_required
@role_required("reuniones", "change_estado")
def finalizar_reunion(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    if reunion.estado == EstadoReunion.EN_CURSO:
        reunion.estado = EstadoReunion.REALIZADA
        reunion.save(update_fields=["estado"])
        _invalidate_reunion_list_cache()
        messages.success(request, f"La reunión '{reunion.titulo}' ha finalizado.")
    else:
        messages.warning(request, "Esta reunión no se puede finalizar.")
    return redirect("reuniones:detalle_reunion", pk=reunion.pk)


@require_POST
@login_required
@role_required("reuniones", "cancel")
def cancelar_reunion(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    if reunion.estado == EstadoReunion.PROGRAMADA:
        reunion.estado = EstadoReunion.CANCELADA
        reunion.save(update_fields=["estado"])
        _invalidate_reunion_list_cache()
        messages.warning(request, f"La reunión '{reunion.titulo}' ha sido cancelada.")
    else:
        messages.error(request, "Solo se pueden cancelar reuniones que están 'Programadas'.")
    return redirect("reuniones:detalle_reunion", pk=reunion.pk)


@login_required
@role_required("reuniones", "view")
def reuniones_json_feed(request):
    estado_query = request.GET.get("estado", "programada").upper()

    estados_validos = {
        "PROGRAMADA": EstadoReunion.PROGRAMADA,
        "EN_CURSO": EstadoReunion.EN_CURSO,
        "REALIZADA": EstadoReunion.REALIZADA,
        "CANCELADA": EstadoReunion.CANCELADA,
    }
    estado_filtro = estados_validos.get(estado_query, EstadoReunion.PROGRAMADA)

    reuniones = (
        Reunion.objects.filter(estado=estado_filtro)
        .only("id", "titulo", "fecha", "estado")
        .order_by("-fecha")
    )

    color_map = {
        "PROGRAMADA": "#0d6efd",
        "EN_CURSO": "#198754",
        "REALIZADA": "#6c757d",
        "CANCELADA": "#dc3545",
    }

    eventos = [{
        "title": r.titulo,
        "start": r.fecha.isoformat(),
        "url": redirect("reuniones:detalle_reunion", pk=r.pk).url,
        "color": color_map.get(r.estado),
    } for r in reuniones]

    return JsonResponse(eventos, safe=False)


@require_POST
@login_required
@role_required("actas", "edit")
def subir_audio_acta(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)

    if reunion.estado != EstadoReunion.REALIZADA:
        messages.error(request, "Solo se pueden subir audios a reuniones finalizadas.")
        return redirect("reuniones:detalle_reunion", pk=pk)

    try:
        acta = reunion.acta
    except Acta.DoesNotExist:
        messages.error(request, "La reunión no tiene un acta asociada. Cree un borrador primero.")
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
    acta.save(update_fields=["archivo_audio", "estado_transcripcion"])

    procesar_audio_vosk.delay(acta.pk)
    messages.success(request, "¡Audio subido! El procesamiento ha comenzado en segundo plano.")
    return redirect("reuniones:detalle_reunion", pk=pk)


@login_required
@role_required("actas", "edit")
def lista_grabaciones(request):
    reuniones_con_audio = (
        Reunion.objects.filter(acta__archivo_audio__isnull=False)
        .exclude(acta__archivo_audio="")
        .select_related("acta", "creada_por")
        .only("id", "titulo", "fecha", "creada_por__username", "acta__archivo_audio")
        .order_by("-fecha")
    )

    return render(request, "reuniones/grabaciones_list.html", {
        "reuniones": reuniones_con_audio,
        "titulo": "Repositorio de Grabaciones (Solo Directiva)",
    })


@login_required
def get_acta_estado(request, pk):
    acta = get_object_or_404(Acta, pk=pk)
    return JsonResponse({
        "estado": acta.estado_transcripcion,
        "estado_display": acta.get_estado_transcripcion_display(),
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
