# datamart/views.py
from django.shortcuts import render, redirect
from django.core.management import call_command
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from datamart.models import FactInscripcionTaller, DimTaller, FactConsultaActa, FactParticipacionVotacion, DimVecino
import json

def es_directiva(user):
    return user.is_staff

@login_required(login_url='/') 
@user_passes_test(es_directiva, login_url='/')
def panel_bi_view(request):
    
    # --- 1. Gráfico Ocupación de Talleres ---
    cupos_talleres = {taller.id: taller.cupos_totales for taller in DimTaller.objects.all()}
    inscritos_talleres = FactInscripcionTaller.objects \
        .values('taller__id', 'taller__nombre') \
        .annotate(total_inscritos=Count('id')) \
        .order_by('taller__nombre')
    
    data_ocupacion_talleres = []
    for taller in inscritos_talleres:
        taller_id = taller['taller__id']
        cupos = cupos_talleres.get(taller_id, 0)
        data_ocupacion_talleres.append({
            'nombre': taller['taller__nombre'],
            'inscritos': taller['total_inscritos'],
            'cupos': cupos,
        })

    # --- 2. Gráfico Tasa de Consulta de Actas ---
    data_consulta_actas = list(FactConsultaActa.objects
        .values('acta__titulo')
        .annotate(consultas=Count('id'))
        .order_by('-consultas')[:10]) # Top 10 más vistas

    # --- 3. Gráfico Participación (Gauge) ---
    total_vecinos = DimVecino.objects.count()
    total_participantes = FactParticipacionVotacion.objects.values('vecino_id').distinct().count()
    meta_participacion = 0.5 # 50%
    
    data_participacion = {
        'total_vecinos': total_vecinos,
        'total_participantes': total_participantes,
        'porcentaje_actual': (total_participantes / total_vecinos * 100) if total_vecinos > 0 else 0,
        'porcentaje_meta': meta_participacion * 100
    }

    # --- 4. NUEVO GRÁFICO: Distribución Demográfica (Sector) ---
    data_demografia_sector = list(DimVecino.objects
        .values('direccion_sector')
        .annotate(total_vecinos=Count('id'))
        .order_by('-total_vecinos'))

    # --- Preparamos el contexto para la plantilla ---
    context = {
        'data_ocupacion_talleres': json.dumps(data_ocupacion_talleres),
        'data_consulta_actas': json.dumps(data_consulta_actas),
        'data_participacion': json.dumps(data_participacion),
        'data_demografia_sector': json.dumps(data_demografia_sector), # <-- ¡Nueva línea!
    }
    
    return render(request, 'datamart/panel_bi.html', context)

# --- VISTA PARA EL BOTÓN DE ACTUALIZAR ---
@login_required(login_url='/')
@user_passes_test(es_directiva, login_url='/')
def ejecutar_etl_view(request):
    
    if request.method == 'POST':
        try:
            # NOTA: call_command() puede ser lento. 
            # Considera mover esto a Celery/Redis en el futuro
            call_command('procesar_etl') 
            messages.success(request, '¡Datos del panel actualizados con éxito!')
        
        except Exception as e:
            messages.error(request, f'Error al actualizar los datos: {e}')
    
    return redirect('panel_bi')