from django.shortcuts import render, redirect
from django.core.management import call_command
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
import json

# --- IMPORTACIONES PARA EL FIX DE FECHAS (MySQL en la Nube/Windows) ---
from collections import defaultdict
from django.utils import timezone
from datetime import timedelta

# --- IMPORTACIONES DE MODELOS ---
from datamart.models import FactInscripcionTaller, DimTaller, FactConsultaActa, FactParticipacionVotacion, DimVecino

# --- IMPORTACIONES PARA PDF ---
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

# ==============================================================================
# FUNCIÓN DE SEGURIDAD MEJORADA (CON DEBUGGING)
# ==============================================================================
def es_directiva(user):
    """
    Verifica si el usuario pertenece a la directiva.
    Imprime mensajes en la consola para detectar por qué falla.
    """
    # 1. Rechazar anónimos
    if not user.is_authenticated:
        return False
    
    # 2. Superusuario siempre entra
    if user.is_superuser:
        return True

    # 3. Verificar Perfil y Rol
    try:
        # Usamos getattr para evitar que el código explote si 'perfil' no existe
        perfil = getattr(user, 'perfil', None)
        
        if perfil is None:
            print(f" DEBUG ACCESS: El usuario '{user.username}' NO tiene un perfil asociado.")
            return False
            
        # Convertimos el rol a texto, quitamos espacios y pasamos a minúsculas
        # Esto hace que 'Presidente', 'PRESIDENTE ' y 'presidente' sean iguales.
        rol_actual = str(perfil.rol).lower().strip()
        
        roles_permitidos = ['presidente', 'secretaria', 'tesorero', 'suplente']
        
        if rol_actual in roles_permitidos:
            print(f" DEBUG ACCESS: Acceso CONCEDIDO a '{user.username}' (Rol: {rol_actual})")
            return True
        else:
            print(f" DEBUG ACCESS: Acceso DENEGADO a '{user.username}'. Su rol '{rol_actual}' no está en la lista permitida.")
            return False
            
    except Exception as e:
        print(f" DEBUG ACCESS: Error verificando permisos: {e}")
        return False

# ==============================================================================
# VISTAS
# ==============================================================================

@login_required(login_url='/') 
@user_passes_test(es_directiva, login_url='/') 
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

    # 2. Gráfico Tasa de Consulta de Actas (Top 10)
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

    # Contexto (Nota: Eliminamos data_tendencia_actas para simplificar si no se usa)
    context = {
        'data_ocupacion_talleres': json.dumps(data_ocupacion_talleres),
        'data_consulta_actas': json.dumps(data_consulta_actas),
        'data_participacion': json.dumps(data_participacion),
        'data_demografia_sector': json.dumps(data_demografia_sector),
    }
    
    return render(request, 'datamart/panel_bi.html', context)

# --- VISTA PARA EL BOTÓN DE ACTUALIZAR ---
@login_required(login_url='/')
@user_passes_test(es_directiva, login_url='/')
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
@user_passes_test(es_directiva, login_url='/')
def generar_pdf_view(request):
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