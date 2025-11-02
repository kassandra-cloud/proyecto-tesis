from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Votacion, Opcion, Voto
from .forms import VotacionForm  
from core.authz import role_required
from django.db.models import Count, OuterRef, Subquery, Value, IntegerField
from core.authz import can
from .forms import VotacionForm, VotacionEditForm
from .models import Votacion, Opcion, Voto
from django.db.models import Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models.functions import Coalesce
from rest_framework.views import APIView
from django.db.models import Q
@login_required
@role_required("votaciones", "view")
def lista_votaciones(request):
    # 1) Marcar como cerradas todas las que ya vencieron
    Votacion.objects.filter(
        activa=True,
        fecha_cierre__lte=timezone.now()
    ).update(activa=False)

    # 2) Listar separadas para la plantilla
    votaciones_abiertas = (
        Votacion.objects
        .filter(activa=True, fecha_cierre__gt=timezone.now())
        .order_by('-fecha_cierre')
    )

    votaciones_cerradas = (
        Votacion.objects
        .filter(Q(activa=False) | Q(fecha_cierre__lte=timezone.now()))
        .order_by('-fecha_cierre')
    )

    context = {
        'votaciones_abiertas': votaciones_abiertas,
        'votaciones_cerradas': votaciones_cerradas,
    }
    return render(request, 'votaciones/lista_votaciones.html', context)

@login_required
@role_required("votaciones", "create")
def crear_votacion(request):
    if request.method == 'POST':
        form = VotacionForm(request.POST)
        if form.is_valid():
            votacion = form.save(commit=False)
            votacion.creada_por = request.user
            # --- LÍNEA MODIFICADA ---
            # El campo combinado 'fecha_cierre' ahora viene del método clean() del formulario
            votacion.fecha_cierre = form.cleaned_data['fecha_cierre']
            votacion.save()

            opciones = form.cleaned_data['opciones']
            for texto_opcion in opciones:
                Opcion.objects.create(votacion=votacion, texto=texto_opcion)
            
            messages.success(request, f'Votación "{votacion.pregunta}" creada con éxito.')
            return redirect('votaciones:lista_votaciones')
    else:
        form = VotacionForm()
    
    return render(request, 'votaciones/votacion_form.html', {'form': form, 'titulo': 'Crear Nueva Votación'})

@login_required
@role_required("votaciones", "view")
def detalle_votacion(request, pk):
    votacion = get_object_or_404(Votacion.objects.prefetch_related('opciones__votos'), pk=pk)
    
    # --- LÓGICA MODIFICADA ---
    
    # Verificamos si el usuario tiene permiso para previsualizar
    puede_previsualizar = can(request.user, "votaciones", "preview")

    resultados = []
    total_votos = 0

    # Si la votación está cerrada O si el usuario puede previsualizar, calculamos los votos
    if not votacion.esta_abierta() or puede_previsualizar:
        opciones_con_votos = votacion.opciones.annotate(num_votos=Count('votos'))
        total_votos = sum(opcion.num_votos for opcion in opciones_con_votos)
        
        for opcion in opciones_con_votos:
            porcentaje = (opcion.num_votos / total_votos * 100) if total_votos > 0 else 0
            resultados.append({
                'texto': opcion.texto,
                'votos': opcion.num_votos,
                'porcentaje': round(porcentaje, 1)
            })

    context = {
        'votacion': votacion,
        'resultados': resultados,
        'total_votos': total_votos,
        'puede_previsualizar': puede_previsualizar,
    }
    return render(request, 'votaciones/detalle_votacion.html', context)

@login_required
@role_required("votaciones", "vote")
def emitir_voto(request, pk):
    if request.method == 'POST':
        votacion = get_object_or_404(Votacion, pk=pk)
        if not votacion.esta_abierta():
            messages.error(request, 'Esta votación está cerrada.')
            return redirect('votaciones:detalle_votacion', pk=pk)
        
        opcion_id = request.POST.get('opcion')
        if not opcion_id:
            messages.error(request, 'Debes seleccionar una opción.')
            return redirect('votaciones:detalle_votacion', pk=pk)

        opcion = get_object_or_404(Opcion, pk=opcion_id)
        
        voto_previo = Voto.objects.filter(opcion__votacion=votacion, votante=request.user).first()
        if voto_previo:
            messages.warning(request, 'Ya has votado en esta elección.')
        else:
            Voto.objects.create(opcion=opcion, votante=request.user)
            messages.success(request, 'Tu voto ha sido registrado.')
        
        return redirect('votaciones:lista_votaciones')
    return redirect('votaciones:lista_votaciones')

@login_required
@role_required("votaciones", "close")
def cerrar_votacion(request, pk):
    votacion = get_object_or_404(Votacion, pk=pk)
    
    if request.method == 'POST':
        votacion.activa = False
        votacion.save()
        messages.success(request, f'La votación "{votacion.pregunta}" ha sido cerrada manualmente.')
    else:
        messages.error(request, 'Acción no permitida.')

    return redirect('votaciones:lista_votaciones')

@login_required
@role_required("votaciones", "edit")
def editar_votacion(request, pk):
    votacion = get_object_or_404(Votacion, pk=pk)

    # Si la votación ya cerró, no se puede editar
    if not votacion.activa:
        messages.error(request, 'No se pueden editar votaciones que ya han sido cerradas.')
        return redirect('votaciones:lista_votaciones')

    if request.method == 'POST':
        form = VotacionEditForm(request.POST, instance=votacion)
        if form.is_valid():
            votacion_editada = form.save(commit=False)
            votacion_editada.fecha_cierre = form.cleaned_data['fecha_cierre']
            votacion_editada.save()
            
            messages.success(request, f'La votación "{votacion.pregunta}" ha sido actualizada.')
            return redirect('votaciones:lista_votaciones')
    else:
        # Pre-cargamos el formulario con la fecha y hora existentes
        initial_data = {
            'fecha_cierre_date': votacion.fecha_cierre.date(),
            'fecha_cierre_time': votacion.fecha_cierre.time(),
        }
        form = VotacionEditForm(instance=votacion, initial=initial_data)

    return render(request, 'votaciones/votacion_edit_form.html', {
        'form': form, 
        'votacion': votacion
    })

@login_required
@role_required("votaciones", "delete")
def eliminar_votacion(request, pk):
    votacion = get_object_or_404(Votacion, pk=pk)

    # Si la votación NO está activa (es decir, está cerrada), no se puede borrar.
    if not votacion.activa:
        messages.error(request, 'No se pueden eliminar votaciones que ya han sido cerradas.')
        return redirect('votaciones:lista_votaciones')

    if request.method == 'POST':
        nombre_votacion = votacion.pregunta
        votacion.delete()
        messages.success(request, f'La votación "{nombre_votacion}" ha sido eliminada.')
        return redirect('votaciones:lista_votaciones')
    
    # Si no es POST, mostramos la página de confirmación como antes.
    return render(request, 'votaciones/votacion_confirm_delete.html', {'votacion': votacion})


