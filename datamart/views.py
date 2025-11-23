from django.shortcuts import render, redirect
from django.core.management import call_command
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from datamart.models import FactInscripcionTaller, DimTaller, FactConsultaActa, FactParticipacionVotacion, DimVecino
import json

# --- IMPORTACIONES PARA PDF ---
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.utils import timezone

# --- FUNCIÓN DE SEGURIDAD CORREGIDA ---
# Esta función decide quién puede entrar.
def es_directiva(user):
    # 1. Si no ha iniciado sesión, rechazado.
    if not user.is_authenticated:
        return False
    
    # 2. El superusuario (tú) siempre entra.
    if user.is_superuser:
        return True

    # 3. VERIFICAR EL ROL DEL PERFIL
    # Buscamos en la tabla 'Perfil' si el usuario es Directiva.
    try:
        # Estos son los roles definidos en tu core/models.py
        roles_permitidos = ['presidente', 'secretaria', 'tesorero', 'suplente']
        return user.perfil.rol in roles_permitidos
    except:
        # Si el usuario no tiene perfil o ocurre un error, no entra.
        return False

# --- VISTA DEL PANEL BI ---
@login_required(login_url='/') 
@user_passes_test(es_directiva, login_url='/') # Si no pasa la prueba 'es_directiva', lo manda al login
def panel_bi_view(request):
    
    # 1. Gráfico Ocupación de Talleres
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

    # 2. Gráfico Tasa de Consulta de Actas
    data_consulta_actas = list(FactConsultaActa.objects
        .values('acta__titulo')
        .annotate(consultas=Count('id'))
        .order_by('-consultas')[:10]) 

    # 3. Gráfico Participación (Gauge)
    total_vecinos = DimVecino.objects.count()
    total_participantes = FactParticipacionVotacion.objects.values('vecino_id').distinct().count()
    meta_participacion = 0.5 
    
    data_participacion = {
        'total_vecinos': total_vecinos,
        'total_participantes': total_participantes,
        'porcentaje_actual': (total_participantes / total_vecinos * 100) if total_vecinos > 0 else 0,
        'porcentaje_meta': meta_participacion * 100
    }

    # 4. Gráfico Distribución Demográfica
    data_demografia_sector = list(DimVecino.objects
        .values('direccion_sector')
        .annotate(total_vecinos=Count('id'))
        .order_by('-total_vecinos'))

    context = {
        'data_ocupacion_talleres': json.dumps(data_ocupacion_talleres),
        'data_consulta_actas': json.dumps(data_consulta_actas),
        'data_participacion': json.dumps(data_participacion),
        'data_demografia_sector': json.dumps(data_demografia_sector),
    }
    
    return render(request, 'datamart/panel_bi.html', context)

# --- VISTA PARA EL BOTÓN DE ACTUALIZAR ---
@login_required(login_url='/')
@user_passes_test(es_directiva, login_url='/') # Usamos la misma seguridad corregida
def ejecutar_etl_view(request):
    
    if request.method == 'POST':
        try:
            call_command('procesar_etl') 
            messages.success(request, '¡Datos del panel actualizados con éxito!')
        
        except Exception as e:
            messages.error(request, f'Error al actualizar los datos: {e}')
    
    return redirect('panel_bi')

# --- VISTA PARA EL PDF ---
@login_required(login_url='/')
@user_passes_test(es_directiva, login_url='/') # Usamos la misma seguridad corregida
def generar_pdf_view(request):
    # Recopilar Datos (Similar al panel)
    data_demografia = list(DimVecino.objects.values('direccion_sector').annotate(total_vecinos=Count('id')).order_by('-total_vecinos'))
    
    inscritos_talleres = FactInscripcionTaller.objects.values('taller__nombre', 'taller__cupos_totales').annotate(total_inscritos=Count('id')).order_by('taller__nombre')
    
    data_actas = list(FactConsultaActa.objects.values('acta__titulo', 'acta__fecha_reunion').annotate(consultas=Count('id')).order_by('-consultas')[:20])

    total_vecinos = DimVecino.objects.count()
    total_participantes = FactParticipacionVotacion.objects.values('vecino_id').distinct().count()
    
    context = {
        'fecha_reporte': timezone.now(),
        'usuario': request.user,
        'data_demografia': data_demografia,
        'data_talleres': inscritos_talleres,
        'data_actas': data_actas,
        'total_vecinos': total_vecinos,
        'total_participantes': total_participantes,
        'tasa_participacion': (total_participantes / total_vecinos * 100) if total_vecinos > 0 else 0,
    }

    template_path = 'datamart/reporte_pdf.html'
    template = get_template(template_path)
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Informe_Gestion_VillaVistaAlMar.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('Hubo un error al generar el PDF <pre>' + html + '</pre>')
    
    return response