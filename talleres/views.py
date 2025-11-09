# talleres/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Taller, Inscripcion
from .forms import TallerForm

@login_required
def lista_talleres(request):
    """
    Muestra todos los talleres. 
    """
    talleres = Taller.objects.all()

    # --- LÍNEAS AÑADIDAS ---
    form = TallerForm() # Formulario vacío para el modal

    context = {
        'talleres': talleres,
        'form': form, # Pasamos el form al template
    }
    return render(request, 'talleres/lista_talleres.html', context)

@login_required
def detalle_taller(request, taller_id):
    """
    Muestra la info de un taller y la lista de inscritos.
    """
    taller = get_object_or_404(Taller, id=taller_id)
    inscritos = Inscripcion.objects.filter(taller=taller).order_by('fecha_inscripcion')
    
    context = {
        'taller': taller,
        'inscritos': inscritos,
    }
    return render(request, 'talleres/detalle_taller.html', context)

@login_required
def crear_taller(request):
    """
    Formulario para crear un nuevo taller.
    """
    if request.method == 'POST':
        form = TallerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Taller creado exitosamente.')
            return redirect('lista_talleres')
    else:
        form = TallerForm()

    context = {
        'form': form,
        'taller': None # Para que la plantilla sepa que estamos creando
    }
    return render(request, 'talleres/crear_taller.html', context)

@login_required
def editar_taller(request, taller_id):
    """
    Formulario para editar un taller existente.
    """
    taller = get_object_or_404(Taller, id=taller_id)
    
    if request.method == 'POST':
        form = TallerForm(request.POST, instance=taller)
        if form.is_valid():
            form.save()
            messages.success(request, 'Taller actualizado exitosamente.')
            return redirect('detalle_taller', taller_id=taller.id)
    else:
        form = TallerForm(instance=taller)

    context = {
        'form': form,
        'taller': taller # Para que la plantilla sepa que estamos editando
    }
    return render(request, 'talleres/crear_taller.html', context)

@login_required
def eliminar_taller(request, taller_id):
    """
    Elimina un taller.
    """
    taller = get_object_or_404(Taller, id=taller_id)
    
    if request.method == 'POST':
        taller.delete()
        messages.success(request, f'El taller "{taller.nombre}" ha sido eliminado.')
        return redirect('lista_talleres')
    
    context = {
        'taller': taller
    }
    return render(request, 'talleres/confirmar_eliminar.html', context)