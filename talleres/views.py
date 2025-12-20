"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Vistas de Django para la gestión web. Maneja listados optimizados 
               con caché, creación/edición de talleres, inscripciones y 
               cancelaciones.
--------------------------------------------------------------------------------
"""
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
# --- IMPORTACIONES PARA OPTIMIZACIÓN ---
from django.views.decorators.cache import cache_page # IMPORTACIÓN PARA CACHÉ
from django.db.models import Count # Ya estaba, mantenemos
# -------------------------------------
from core.authz import role_required
from django.utils import timezone

# Asegúrate de que todos los modelos y forms estén importados
from .models import Taller, Inscripcion
from .forms import TallerForm, InscripcionForm, CancelacionTallerForm 

# OPTIMIZACIÓN 1: Caching para vistas de listado (60 segundos)
@cache_page(60)
@login_required
@role_required("talleres", "view")
def lista_talleres(request):
    """
    Muestra solo los talleres PROGRAMADOS.
    
    NOTA: La lógica de actualización de estado ha sido removida 
    y DEBE ser gestionada por una tarea asíncrona de Celery 
    para permitir el caching y un tiempo de respuesta rápido.
    """
    
    # --- LÓGICA DE ACTUALIZACIÓN AUTOMÁTICA (ELIMINADA PARA OPTIMIZACIÓN) ---
    # Mueva este tipo de lógica a una tarea periódica de Celery (CronJob)
    # ------------------------------------------------------------------------

    # Optimización de consulta: Cargar el conteo de inscritos y el creador en una sola consulta.
    talleres = Taller.objects.filter(
        estado=Taller.Estado.PROGRAMADO
    ).annotate(
        inscritos_count=Count('inscripcion')
    ).select_related('creado_por').order_by('fecha_inicio') # <-- select_related AGREGADO para evitar N+1 queries
    
    context = {
        'talleres': talleres,
        'titulo': 'Talleres Programados'
    }
    return render(request, 'talleres/lista_talleres.html', context)

# --- NUEVA VISTA: HISTORIAL ---
# OPTIMIZACIÓN 2: Caching para listado de archivados (5 minutos / 300 segundos)
@cache_page(300)
@login_required
@role_required("talleres", "view")
def lista_talleres_archivados(request):
    """
    Muestra el historial de talleres Finalizados y Cancelados.
    Optimizado con caching y select_related.
    """
    # Optimización: Precargar el usuario que creó el taller.
    talleres_archivados = Taller.objects.filter(
        estado__in=[Taller.Estado.FINALIZADO, Taller.Estado.CANCELADO]
    ).select_related('creado_por').order_by('-fecha_termino') # <-- select_related AGREGADO
    
    context = {
        'talleres': talleres_archivados,
        'titulo': 'Historial de Talleres (Finalizados y Cancelados)'
    }
    # Reutilizamos la plantilla del historial que creamos
    return render(request, 'talleres/lista_talleres_archivados.html', context)

@login_required
@role_required("talleres", "create")
def crear_taller(request):
    if request.method == 'POST':
        # Usa el TallerForm actualizado (que pide cupos_totales)
        form = TallerForm(request.POST) 
        if form.is_valid():
            taller = form.save(commit=False)
            taller.creado_por = request.user
            taller.save()
            messages.success(request, 'Taller programado exitosamente.')
            return redirect('talleres:lista_talleres')
    else:
        form = TallerForm()
    
    context = {
        'form': form,
        'titulo': 'Programar Nuevo Taller'
    }
    # Reutilizamos la plantilla original de crear_taller
    return render(request, 'talleres/crear_taller.html', context)


@login_required
@role_required("talleres", "view")
def detalle_taller(request, pk):
    # Optimización: Usamos select_related('creado_por') para precargar el autor
    try:
        taller = Taller.objects.annotate(
            inscritos_count=Count('inscripcion')
        ).select_related('creado_por').get(pk=pk) # <-- select_related AGREGADO
    except Taller.DoesNotExist:
        raise Http404("Taller no encontrado")

    # Comprobamos si el usuario ya está inscrito (query eficiente con .exists())
    esta_inscrito = Inscripcion.objects.filter(taller=taller, vecino=request.user).exists()
    
    context = {
        'taller': taller,
        'esta_inscrito': esta_inscrito,
        'titulo': taller.nombre,
    }
    return render(request, 'talleres/detalle_taller.html', context)

@login_required
@role_required("talleres", "edit")
def editar_taller(request, pk):
    taller = get_object_or_404(Taller, pk=pk)
    
    # VALIDACIÓN DE ESTADO
    # No dejamos editar talleres que no estén programados
    if taller.estado != Taller.Estado.PROGRAMADO:
        messages.error(request, 'No se puede editar un taller que ya ha finalizado o ha sido cancelado.')
        return redirect('talleres:lista_talleres')

    if request.method == 'POST':
        form = TallerForm(request.POST, instance=taller) # Usa TallerForm actualizado
        if form.is_valid():
            form.save()
            messages.success(request, 'Taller actualizado exitosamente.')
            return redirect('talleres:lista_talleres')
    else:
        form = TallerForm(instance=taller)
    
    context = {
        'form': form,
        'taller': taller,
        'titulo': f'Editar Taller: {taller.nombre}'
    }
    # Reutiliza la plantilla de crear
    return render(request, 'talleres/crear_taller.html', context)


@login_required
@role_required("talleres", "delete")
def eliminar_taller(request, pk):
    taller = get_object_or_404(Taller, pk=pk)
    if request.method == 'POST':
        titulo_taller = taller.nombre
        taller.delete()
        messages.success(request, f'Taller "{titulo_taller}" eliminado exitosamente.')
        return redirect('talleres:lista_talleres')
    
    context = {
        'taller': taller,
        'titulo': f'Eliminar Taller: {taller.nombre}'
    }
    return render(request, 'talleres/confirmar_eliminar.html', context)

# --- NUEVA VISTA: CANCELAR ---
@login_required
@role_required("talleres", "delete") # Usamos el permiso "delete" para cancelar
def cancelar_taller(request, pk):
    # Solo podemos cancelar talleres que estén programados
    taller = get_object_or_404(Taller, pk=pk, estado=Taller.Estado.PROGRAMADO)
    
    if request.method == 'POST':
        form = CancelacionTallerForm(request.POST, instance=taller)
        if form.is_valid():
            taller.estado = Taller.Estado.CANCELADO
            form.save() # Guarda el motivo
            
            messages.warning(request, f'El taller "{taller.nombre}" ha sido cancelado exitosamente.')
            return redirect('talleres:lista_talleres')
    else:
        form = CancelacionTallerForm(instance=taller)

    context = {
        'form': form,
        'taller': taller,
        'titulo': f'Cancelar Taller: {taller.nombre}'
    }
    # Reutilizamos la plantilla de cancelar que creamos
    return render(request, 'talleres/cancelar_taller.html', context)

@login_required
@role_required("talleres", "inscribir")
def inscribir_taller(request, pk):
    taller = get_object_or_404(Taller, pk=pk)
    
    # Lógica de inscripción (simple)
    Inscripcion.objects.get_or_create(taller=taller, vecino=request.user)
    messages.success(request, f'Te has inscrito exitosamente en {taller.nombre}.')
    return redirect('talleres:detalle_taller', pk=taller.pk)

@login_required
def mis_inscripciones(request):
    # Esta consulta ya estaba optimizada con select_related('taller')
    inscripciones = Inscripcion.objects.filter(vecino=request.user).select_related('taller')
    context = {
        'inscripciones': inscripciones,
        'titulo': 'Mis Inscripciones a Talleres'
    }
    return render(request, 'talleres/mis_inscripciones.html', context)