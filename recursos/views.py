"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Vistas de Django para la interfaz web.
               - Gestión CRUD de Recursos.
               - Gestión de Solicitudes (Aprobar/Rechazar) con lógica de 
                 rechazo automático por conflictos de horario.
--------------------------------------------------------------------------------
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.authz import role_required
from .forms import RecursoForm
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Recurso, SolicitudReserva, Reserva
from datetime import datetime, time

@login_required
@role_required("recursos", "view")
def lista_recursos(request):
    """
    Muestra el listado de recursos, separados por Activos e Inactivos.
    """
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
    """Vista para crear un nuevo recurso"""
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
    """Vista para editar un recurso existente"""
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

@login_required
@role_required("recursos", "edit")
@require_POST
def deshabilitar_recurso(request, pk):
    """Marca un recurso como no disponible (borrado lógico)"""
    recurso = get_object_or_404(Recurso, pk=pk)
    if not recurso.disponible:
        messages.info(request, "El recurso ya estaba deshabilitado.")
    else:
        recurso.disponible = False
        recurso.save()
        messages.success(request, f"Recurso “{recurso.nombre}” deshabilitado.")
    return redirect('recursos:lista_recursos')

@login_required
@role_required("recursos", "edit")
@require_POST
def restaurar_recurso(request, pk):
    """Restaura un recurso a disponible"""
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
    Panel para que la directiva gestione las solicitudes.
    Permite filtrar por estado (PENDIENTE, APROBADA, etc).
    """
    estados_posibles = SolicitudReserva.ESTADOS
    filtro_actual = request.GET.get('estado', 'PENDIENTE').upper()
    
    # Validar que el filtro sea un estado válido
    if filtro_actual not in dict(estados_posibles):
        filtro_actual = 'PENDIENTE'

    # Obtener solicitudes filtradas
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
        "reservas": qs, 
    }
    return render(request, "recursos/gestionar_reservas.html", ctx)

@login_required
@role_required("reservas", "manage_all")
@require_POST
def actualizar_estado_reserva(request, pk):
    """
    Procesa la aprobación o rechazo de una reserva.
    Incluye lógica crítica para evitar solapamiento de reservas aprobadas.
    """
    sol = get_object_or_404(SolicitudReserva, pk=pk)
    accion = request.POST.get('accion')
    estado_anterior = sol.estado

    if accion == 'APROBADA':
        # 1. Aprobar la solicitud
        sol.estado = "APROBADA"
        sol.save(update_fields=["estado"])

        # 2. Crear la Reserva espejo para compatibilidad con lógica antigua
        Reserva.objects.create(
            recurso=sol.recurso,
            vecino=sol.solicitante,
            fecha_inicio=sol.fecha_inicio,
            fecha_fin=sol.fecha_fin,
            motivo=sol.motivo,
            estado=Reserva.Estado.APROBADA,
        )

        # 3. RECHAZO AUTOMÁTICO DE CONFLICTOS
        # Busca otras solicitudes PENDIENTES que coincidan en fechas y recurso
        conflictos = SolicitudReserva.objects.filter(
            recurso=sol.recurso,
            estado="PENDIENTE"
        ).filter(
            fecha_inicio__lt=sol.fecha_fin,
            fecha_fin__gt=sol.fecha_inicio
        ).exclude(pk=sol.pk)

        cantidad_rechazada = conflictos.count()
        
        if cantidad_rechazada > 0:
            # Rechaza masivamente las conflictivas
            conflictos.update(estado="RECHAZADA")
            messages.warning(
                request, 
                f"⚠️ Se han rechazado automáticamente otras {cantidad_rechazada} solicitudes por conflicto de fechas."
            )

        messages.success(request, f"Solicitud #{sol.id} APROBADA exitosamente.")

    elif accion == 'RECHAZADA':
        sol.estado = "RECHAZADA"
        sol.save(update_fields=["estado"])
        messages.warning(request, f"Solicitud #{sol.id} RECHAZADA.")

    elif accion == 'PENDIENTE':
        sol.estado = "PENDIENTE"
        sol.save(update_fields=["estado"])
        
        # Si venía de APROBADA, se debe borrar la reserva espejo
        if estado_anterior == 'APROBADA':
            Reserva.objects.filter(
                recurso=sol.recurso,
                vecino=sol.solicitante,
                fecha_inicio=sol.fecha_inicio,
                fecha_fin=sol.fecha_fin,
                estado=Reserva.Estado.APROBADA
            ).delete()
            messages.info(request, f"Solicitud #{sol.id} devuelta a Pendiente. Reserva eliminada.")
        else:
            messages.info(request, f"Solicitud #{sol.id} devuelta a Pendiente.")

    else:
        messages.error(request, "Acción no válida.")

    return redirect(request.POST.get('next', 'recursos:gestionar_reservas'))