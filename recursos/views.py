from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.authz import role_required
from .models import Recurso, Reserva 
from .forms import RecursoForm
from django.views.decorators.http import require_POST
from django.utils import timezone

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

@login_required
@role_required("reservas", "manage_all")
def gestionar_reservas(request):
    """
    Panel para la Directiva: Ver todas las solicitudes y filtrarlas.
    """
    # Obtenemos el filtro de la URL (ej: ?estado=PENDIENTE)
    # Por defecto, mostramos las PENDIENTES
    filtro_estado = request.GET.get('estado', 'PENDIENTE').upper()

    if filtro_estado not in Reserva.Estado.values:
        filtro_estado = 'PENDIENTE'

    # Filtramos las reservas según el estado
    reservas_list = Reserva.objects.filter(
        estado=filtro_estado
    ).select_related('recurso', 'vecino', 'vecino__perfil').order_by('fecha_inicio')
    
    # Conteo para la insignia en la pestaña
    conteo_pendientes = Reserva.objects.filter(estado=Reserva.Estado.PENDIENTE).count()

    context = {
        'reservas': reservas_list,
        'filtro_actual': filtro_estado,
        'estados_posibles': Reserva.Estado.choices,
        'conteo_pendientes': conteo_pendientes,
        'titulo': 'Gestión de Solicitudes de Reserva'
    }
    return render(request, 'recursos/gestionar_reservas.html', context)


@login_required
@role_required("reservas", "manage_all")
@require_POST
def actualizar_estado_reserva(request, pk):
    """
    Acción POST para Aprobar o Rechazar una reserva.
    """
    reserva = get_object_or_404(Reserva, pk=pk)
    
    # El valor del botón 'submit' será 'APROBADA' o 'RECHAZADA'
    nueva_accion = request.POST.get('accion')

    if nueva_accion == 'APROBADA':
        reserva.estado = Reserva.Estado.APROBADA
        reserva.save()
        messages.success(request, f'Reserva de {reserva.recurso.nombre} para {reserva.vecino.username} APROBADA.')
        
        # (Aquí irá la lógica de notificación push a la app)
    
    elif nueva_accion == 'RECHAZADA':
        reserva.estado = Reserva.Estado.RECHAZADA
        reserva.save()
        messages.warning(request, f'Reserva de {reserva.recurso.nombre} para {reserva.vecino.username} RECHAZADA.')
        
        # (Aquí irá la lógica de notificación push a la app)
    else:
        messages.error(request, 'Acción no válida.')

    # Redirigir de vuelta a la lista de pendientes (o de donde vino)
    return redirect(request.POST.get('next', 'recursos:gestionar_reservas'))