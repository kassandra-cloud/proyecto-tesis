from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.authz import role_required
from .models import Recurso
from .forms import RecursoForm
from django.views.decorators.http import require_POST # <-- Importa esto

@login_required
@role_required("recursos", "view")
def lista_recursos(request):
    """
    Muestra listas separadas de recursos disponibles y no disponibles.
    """
    # --- LÓGICA MODIFICADA ---
    recursos_activos = Recurso.objects.filter(disponible=True).order_by('nombre')
    recursos_inactivos = Recurso.objects.filter(disponible=False).order_by('nombre')
    
    context = {
        'recursos_activos': recursos_activos,
        'recursos_inactivos': recursos_inactivos,
        'titulo': 'Gestión de Recursos'
    }
    return render(request, 'recursos/lista_recursos.html', context)

@login_required
@role_required("recursos", "create")
def crear_recurso(request):
    # ... (Esta vista sigue igual)
    if request.method == 'POST':
        form = RecursoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Recurso creado exitosamente.')
            return redirect('recursos:lista_recursos')
    else:
        form = RecursoForm()

    context = {
        'form': form,
        'titulo': 'Crear Nuevo Recurso'
    }
    return render(request, 'recursos/recurso_form.html', context)

@login_required
@role_required("recursos", "edit")
def editar_recurso(request, pk):
    # ... (Esta vista sigue igual)
    recurso = get_object_or_404(Recurso, pk=pk)
    
    if request.method == 'POST':
        form = RecursoForm(request.POST, instance=recurso)
        if form.is_valid():
            form.save()
            messages.success(request, 'Recurso actualizado exitosamente.')
            return redirect('recursos:lista_recursos')
    else:
        form = RecursoForm(instance=recurso)

    context = {
        'form': form,
        'recurso': recurso,
        'titulo': f'Editar Recurso: {recurso.nombre}'
    }
    return render(request, 'recursos/recurso_form.html', context)

# --- VISTA 'eliminar_recurso' ELIMINADA ---

# --- NUEVAS VISTAS (basadas en usuarios/views.py) ---

@login_required
@role_required("recursos", "edit") # Usamos el permiso de "edit"
@require_POST
def deshabilitar_recurso(request, pk):
    recurso = get_object_or_404(Recurso, pk=pk)
    if not recurso.disponible:
        messages.info(request, "El recurso ya estaba deshabilitado.")
    else:
        recurso.disponible = False
        recurso.save()
        messages.success(request, f"Recurso “{recurso.nombre}” deshabilitado.")
    return redirect('recursos:lista_recursos')


@login_required
@role_required("recursos", "edit") # Usamos el permiso de "edit"
@require_POST
def restaurar_recurso(request, pk):
    recurso = get_object_or_404(Recurso, pk=pk)
    if recurso.disponible:
        messages.info(request, "El recurso ya estaba disponible.")
    else:
        recurso.disponible = True
        recurso.save()
        messages.success(request, f"Recurso “{recurso.nombre}” restaurado.")
    return redirect('recursos:lista_recursos')