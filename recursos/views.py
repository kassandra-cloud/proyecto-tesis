from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.authz import role_required
from .forms import RecursoForm
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Recurso, SolicitudReserva, Reserva
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
    # Estados y filtro
    estados_posibles = SolicitudReserva.ESTADOS
    filtro_actual = request.GET.get('estado', 'PENDIENTE').upper()
    if filtro_actual not in dict(estados_posibles):
        filtro_actual = 'PENDIENTE'

    # Cargamos SOLICITUDES, pero las exponemos como "reservas" al template
    qs = (SolicitudReserva.objects
          .filter(estado=filtro_actual)
          .select_related('recurso','solicitante','solicitante__perfil')
          .order_by('fecha_inicio'))

    conteo_pendientes = SolicitudReserva.objects.filter(estado="PENDIENTE").count()

    ctx = {
        "titulo": "Gestión de Solicitudes de Reserva",
        "estados_posibles": estados_posibles,
        "filtro_actual": filtro_actual,
        "conteo_pendientes": conteo_pendientes,
        "reservas": qs,  # <- mismo nombre que espera el template
    }
    return render(request, "recursos/gestionar_reservas.html", ctx)
@login_required
@role_required("reservas", "manage_all")
@require_POST
def actualizar_estado_reserva(request, pk):
    # Ahora opera sobre SOLICITUD
    sol = get_object_or_404(SolicitudReserva, pk=pk)
    accion = request.POST.get('accion')
    estado_anterior = sol.estado
    if accion == 'APROBADA':
        sol.estado = "APROBADA"
        sol.save(update_fields=["estado"])
        # Crear la Reserva “espejo”
        Reserva.objects.create(
            recurso=sol.recurso,
            vecino=sol.solicitante,
            fecha_inicio=sol.fecha_inicio,
            fecha_fin=sol.fecha_fin,
            motivo=sol.motivo,
            estado=Reserva.Estado.APROBADA,
        )
        messages.success(request, f"Solicitud #{sol.id} APROBADA. Reserva creada.")
    elif accion == 'RECHAZADA':
        sol.estado = "RECHAZADA"
        sol.save(update_fields=["estado"])
        messages.warning(request, f"Solicitud #{sol.id} RECHAZADA.")
    elif accion == 'PENDIENTE':
        sol.estado = "PENDIENTE"
        sol.save(update_fields=["estado"])
        
        # Si la estábamos "deshaciendo" desde APROBADA, debemos borrar la Reserva espejo
        if estado_anterior == 'APROBADA':
            # Buscamos la reserva espejo que coincida
            Reserva.objects.filter(
                recurso=sol.recurso,
                vecino=sol.solicitante,
                fecha_inicio=sol.fecha_inicio,
                fecha_fin=sol.fecha_fin,
                estado=Reserva.Estado.APROBADA # Por seguridad
            ).delete()
            messages.info(request, f"Solicitud #{sol.id} devuelta a Pendiente. La reserva aprobada fue eliminada.")
        else:
            # Si era RECHAZADA, solo la movemos a pendiente
            messages.info(request, f"Solicitud #{sol.id} devuelta a Pendiente.")
    # --- FIN NUEVA LÓGICA ---
    else:
        messages.error(request, "Acción no válida.")

    return redirect(request.POST.get('next', 'recursos:gestionar_reservas'))