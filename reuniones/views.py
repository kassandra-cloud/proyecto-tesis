from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required,permission_required
from .models import Reunion, Asistencia, Acta # <--- MODIFICAR ESTA LÍNEA
from .forms import ReunionForm, ActaForm 
from core.authz import role_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Reunion, Acta

User = get_user_model()



@login_required
@role_required("reuniones", "view")
def reunion_list(request):
    reuniones = Reunion.objects.all().order_by('-fecha')
    context = {
        "reuniones": reuniones,
        "titulo": "Próximas Reuniones"
    }
    return render(request, "reuniones/reunion_list.html", context)

@login_required
@role_required("reuniones", "view")
def reunion_detail(request, pk):
    """
    Muestra todos los detalles de una reunión específica.
    """
    reunion = get_object_or_404(Reunion, pk=pk) # Busca la reunión por su ID
    context = {
        "reunion": reunion
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

    context = {
        "form": form,
        "titulo": "Crear Nueva Reunión"
    }
    return render(request, "reuniones/reunion_form.html", context)


@login_required
@role_required("reuniones", "asistencia")
def asistencia_list(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)

    # Obtener todos los usuarios que no son superusuarios para la lista
    vecinos = User.objects.filter(is_superuser=False)

    # Obtener los IDs de los vecinos que ya están marcados como presentes
    asistentes_pks = Asistencia.objects.filter(reunion=reunion, presente=True).values_list('vecino__pk', flat=True)

    if request.method == "POST":
        # Borramos la lista de asistencia anterior para esta reunión
        Asistencia.objects.filter(reunion=reunion).delete()

        # Obtenemos la lista de los vecinos que fueron marcados en el formulario
        vecinos_presentes_ids = request.POST.getlist('presentes')

        # Creamos los nuevos registros de asistencia
        for vecino in vecinos:
            esta_presente = str(vecino.pk) in vecinos_presentes_ids
            Asistencia.objects.create(
                reunion=reunion,
                vecino=vecino,
                presente=esta_presente
            )

        messages.success(request, "Se ha guardado la lista de asistencia.")
        return redirect('reuniones:detalle_reunion', pk=reunion.pk)

    context = {
        "reunion": reunion,
        "vecinos": vecinos,
        "asistentes_pks": asistentes_pks, # Pasamos los IDs a la plantilla
        "titulo": f"Registro de Asistencia para '{reunion.titulo}'"
    }
    return render(request, "reuniones/asistencia_list.html", context)


@login_required
@role_required("actas", "edit")
def acta_edit(request, pk):
    reunion = get_object_or_404(Reunion, pk=pk)

    # Intentamos obtener el acta existente. Si no existe, creamos una nueva instancia.
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

    context = {
        "form": form,
        "reunion": reunion,
        "titulo": f"Editar Acta de '{reunion.titulo}'"
    }
    return render(request, "reuniones/acta_edit.html", context)



# En reuniones/views.py

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
    template = get_template(template_path)

    context = {'reunion': reunion, 'acta': acta}
    html = template.render(context)

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)

    if not pdf.err:
        # --- ESTA ES LA PARTE CORREGIDA ---
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="acta_reunion_{reunion.pk}.pdf"'
        return response
        # ----------------------------------

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