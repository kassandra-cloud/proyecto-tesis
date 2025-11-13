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
from .models import Reunion, Asistencia, Acta
from .forms import ReunionForm, ActaForm
from core.authz import role_required
from core.models import Perfil
import json

User = get_user_model()


# =========================
# Helpers
# =========================
def _pdf_bytes_desde_xhtml(template_path: str, context: dict) -> bytes:
    """
    Renderiza un template HTML a PDF (bytes) usando xhtml2pdf.
    Devuelve bytes del PDF listo para adjuntar.
    """
    template = get_template(template_path)
    html = template.render(context)

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), dest=result, encoding='UTF-8')

    if pdf.err:
        # En caso de error devolvemos bytes vacíos (el caller decide la respuesta)
        return b""
    return result.getvalue()


# =========================
# Reuniones
# =========================
@login_required
@role_required("reuniones", "view")
def reunion_list(request):
    estado = request.GET.get("estado", "programada")
    now = timezone.now()

    if estado == "realizada":
        qs = Reunion.objects.filter(fecha__lt=now - timedelta(hours=2))
        titulo = "Reuniones Realizadas"
    else:  # programada / en_curso
        qs = (Reunion.objects.filter(fecha__gt=now) |
              Reunion.objects.filter(fecha__lte=now, fecha__gte=now - timedelta(hours=2)))
        titulo = "Reuniones Programadas"

    reuniones = qs.order_by("-fecha")
    return render(request, "reuniones/reunion_list.html", {
        "reuniones": reuniones,
        "estado": estado,
        "titulo": titulo,
    })

@login_required
@role_required("reuniones", "view")
def reunion_detail(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)

    # Usuarios activos con correo (excluye superusuario si quieres)
    destinatarios = (
        User.objects
            .filter(is_active=True)
            .exclude(email__isnull=True)
            .exclude(email__exact="")
            .exclude(is_superuser=True)     # quita esta línea si quieres incluirlos
            .order_by("first_name", "last_name", "email")
    )

    context = {
        "reunion": reunion,
        "destinatarios": destinatarios,   
        "roles": Perfil.Roles.choices,
    }
    return render(request, "reuniones/reunion_detail.html", context)
@login_required
@role_required("reuniones", "create")
def reunion_create(request):
    if request.method == "POST":
        form = ReunionForm(request.POST)
        if form.is_valid():
            reunion = form.save(commit=False)
            reunion.creada_por = request.user
            reunion.save()
            messages.success(request, f"Reunión '{reunion.titulo}' creada correctamente.")
            return redirect('reuniones:lista_reuniones')
        else:
            messages.error(request, "Por favor, corrige los errores del formulario.")
    else:
        form = ReunionForm()

    context = {"form": form, "titulo": "Crear Nueva Reunión"}
    return render(request, "reuniones/reunion_form.html", context)


# =========================
# Asistencia
# =========================
@login_required
@role_required("reuniones", "asistencia")
def asistencia_list(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    vecinos = User.objects.filter(is_superuser=False)
    asistentes_pks = Asistencia.objects.filter(reunion=reunion, presente=True).values_list('vecino__pk', flat=True)

    if request.method == "POST":
        Asistencia.objects.filter(reunion=reunion).delete()
        vecinos_presentes_ids = request.POST.getlist('presentes')

        for vecino in vecinos:
            esta_presente = str(vecino.pk) in vecinos_presentes_ids
            Asistencia.objects.create(reunion=reunion, vecino=vecino, presente=esta_presente)

        messages.success(request, "Se ha guardado la lista de asistencia.")
        return redirect('reuniones:detalle_reunion', pk=reunion.pk)

    context = {
        "reunion": reunion,
        "vecinos": vecinos,
        "asistentes_pks": asistentes_pks,
        "titulo": f"Registro de Asistencia para '{reunion.titulo}'"
    }
    return render(request, "reuniones/asistencia_list.html", context)


# =========================
# Actas (editar / exportar / aprobar)
# =========================
@login_required
@role_required("actas", "edit")
def acta_edit(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    try:
        acta = reunion.acta
    except Acta.DoesNotExist:
        acta = Acta(reunion=reunion)

    if request.method == "POST":
        form = ActaForm(request.POST, instance=acta)
        if form.is_valid():
            form.save()
            messages.success(request, "El acta se ha guardado correctamente.")
            return redirect('reuniones:detalle_reunion', pk=reunion.pk)
    else:
        form = ActaForm(instance=acta)

    context = {"form": form, "reunion": reunion, "titulo": f"Editar Acta de '{reunion.titulo}'"}
    return render(request, "reuniones/acta_edit.html", context)


@login_required
@role_required("actas", "view")
def acta_export_pdf(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    try:
        acta = reunion.acta
    except Acta.DoesNotExist:
        messages.error(request, "Esta reunión aún no tiene un acta para exportar.")
        return redirect('reuniones:detalle_reunion', pk=reunion.pk)

    template_path = 'reuniones/acta_pdf_template.html'
    pdf_bytes = _pdf_bytes_desde_xhtml(template_path, {"reunion": reunion, "acta": acta})

    if pdf_bytes:
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="acta_reunion_{reunion.pk}.pdf"'
        return response

    return HttpResponse("Error al generar el PDF", status=500)


@login_required
@permission_required("reuniones.change_acta", raise_exception=True)
@require_POST
def aprobar_acta(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    acta = get_object_or_404(Acta, pk=reunion.pk)

    if not acta.aprobada:
        acta.aprobada = True
        acta.save(update_fields=["aprobada"])
        messages.success(request, "Acta aprobada correctamente.")
    else:
        messages.info(request, "El acta ya estaba aprobada.")

    next_url = request.POST.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("reuniones:detalle_reunion", pk=pk)


@login_required
@permission_required("reuniones.change_acta", raise_exception=True)
@require_POST
def rechazar_acta(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)
    acta = get_object_or_404(Acta, pk=reunion.pk)

    if acta.aprobada:
        acta.aprobada = False
        acta.save(update_fields=["aprobada"])
        messages.success(request, "Acta marcada como no aprobada.")
    else:
        messages.info(request, "El acta ya estaba como no aprobada.")

    next_url = request.POST.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("reuniones:detalle_reunion", pk=pk)


# =========================
# Borrador de Acta (transcripción)
# =========================
@login_required
@require_POST
def guardar_borrador_acta(request, pk):
    """
    Guarda texto en Acta.transcripcion_borrador de la reunión pk.
    Crea el Acta si no existe.
    Espera body JSON: {"contenido":"..."}
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("JSON inválido")

    contenido = (data.get("contenido") or "").strip()

    reunion = get_object_or_404(Reunion, pk=pk)
    acta, _ = Acta.objects.get_or_create(reunion=reunion)
    acta.transcripcion_borrador = contenido
    # Si tu modelo tiene timestamps específicos, ajusta los nombres:
    if hasattr(acta, "borrador_actualizado"):
        acta.borrador_actualizado = timezone.now()
        acta.save(update_fields=["transcripcion_borrador", "borrador_actualizado"])
    else:
        acta.save(update_fields=["transcripcion_borrador"])

    return JsonResponse({"ok": True, "updated": timezone.now().isoformat()})


@login_required
@require_POST
def aprobar_borrador_acta(request, pk):
    """
    Copia Acta.transcripcion_borrador -> Acta.contenido y limpia el borrador.
    """
    reunion = get_object_or_404(Reunion, pk=pk)
    acta, _ = Acta.objects.get_or_create(reunion=reunion)

    acta.contenido = acta.transcripcion_borrador or ""
    acta.transcripcion_borrador = ""
    if hasattr(acta, "aprobada"):
        acta.aprobada = True
    acta.save()

    return JsonResponse({"ok": True})


# =========================
# Enviar Acta por correo (PDF adjunto)
# =========================
@login_required
@role_required("actas", "view")
@require_POST
@csrf_protect
def enviar_acta_pdf_por_correo(request, pk):
    """
    Recibe pk de la REUNIÓN.
    POST:
      - 'correos' como string "a@b.com, c@d.com"  O  'correos[]' como lista
    Envía el PDF del acta como adjunto.
    """
    reunion = get_object_or_404(Reunion, pk=pk)
    try:
        acta = reunion.acta
    except Acta.DoesNotExist:
        return HttpResponseBadRequest("Esta reunión no tiene acta.")

    # 1) Parsear destinatarios
    correos = request.POST.getlist("correos[]")
    if not correos:
        correos_str = (request.POST.get("correos") or "").strip()
        if correos_str:
            correos = [c.strip() for c in correos_str.split(",") if c.strip()]

    if not correos:
        return HttpResponseBadRequest("Debes ingresar al menos un correo válido.")

    # 2) Generar PDF (mismo template que exportación)
    template_path = 'reuniones/acta_pdf_template.html'
    pdf_bytes = _pdf_bytes_desde_xhtml(template_path, {"reunion": reunion, "acta": acta})
    if not pdf_bytes:
        return HttpResponse("Error al generar el PDF", status=500)

    filename = f"Acta_{slugify(getattr(reunion, 'titulo', f'reunion-{reunion.pk}'))}.pdf"

    # 3) Enviar correo (from_email usa DEFAULT_FROM_EMAIL de settings con tus variables .env)
    asunto = f"Acta: {getattr(reunion, 'titulo', 'Reunión')}"
    cuerpo  = "Se adjunta el acta en formato PDF."
    email = EmailMessage(subject=asunto, body=cuerpo, to=correos)
    email.attach(filename, pdf_bytes, "application/pdf")
    email.send(fail_silently=False)

    return JsonResponse({"ok": True, "mensaje": "Acta enviada por correo correctamente."})
