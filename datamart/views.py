import json
import re
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.management import call_command
from django.db.models import Count, Avg
from django.db.models.functions import ExtractYear
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.utils import timezone
from xhtml2pdf import pisa
from datamart.models import LogRendimiento

from datamart.models import (
    FactInscripcionTaller, DimTaller, FactConsultaActa,
    FactParticipacionVotacion, DimVecino, FactAsistenciaReunion,
    DimActa, FactMetricasDiarias, LogRendimiento, 
)

MESES_ES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

def es_usuario_directiva(user):
    return user.is_authenticated

def construir_datos_panel_bi(mes=None, anio=None):
    # 1. Ocupación Talleres
    inscritos_qs = FactInscripcionTaller.objects.values("taller__id").annotate(total_inscritos=Count("id"))
    inscritos_por_id = {item['taller__id']: item['total_inscritos'] for item in inscritos_qs}
    data_ocupacion_talleres = []
    for taller in DimTaller.objects.all().order_by('nombre'):
        data_ocupacion_talleres.append({
            "nombre": taller.nombre,
            "inscritos": inscritos_por_id.get(taller.id, 0),
            "cupos": taller.cupos_totales,
        })

    # 2. Consulta Actas
    data_consulta_actas = list(FactConsultaActa.objects.values("acta__titulo").annotate(consultas=Count("id")).order_by("-consultas")[:10])

    # 3. Participación
    total_vecinos = DimVecino.objects.count() or 1
    total_part = FactParticipacionVotacion.objects.values("vecino_id").distinct().count()
    porcentaje_actual = (float(total_part) / float(total_vecinos) * 100.0) if total_vecinos > 0 else 0.0
    
    data_participacion = {
        "total_vecinos": total_vecinos,
        "total_participantes": total_part,
        "porcentaje_actual": porcentaje_actual,
        "porcentaje_meta": 50.0,
    }

    # 4. Demografía
    data_demografia_sector = list(DimVecino.objects.values("direccion_sector").annotate(total_vecinos=Count("id")).order_by("-total_vecinos"))
    for row in data_demografia_sector:
        original = row['direccion_sector'] or ""
        solo_texto = re.sub(r'\d+', '', original).strip()
        row['direccion_sector'] = solo_texto or "Sin Dirección"

    # 5. Asistencia (CON FILTRO)
    asistencia_qs = FactAsistenciaReunion.objects.all()
    if anio: asistencia_qs = asistencia_qs.filter(reunion__fecha__year=anio)
    if mes: asistencia_qs = asistencia_qs.filter(reunion__fecha__month=mes)
    
    asist_agrupada = asistencia_qs.values('reunion__fecha').annotate(total=Count('id')).order_by('reunion__fecha')
    data_asistencia = [{'fecha': item['reunion__fecha'].strftime("%Y-%m-%d"), 'total': item['total']} for item in asist_agrupada]

    # 6. Métricas Técnicas
    metricas = FactMetricasDiarias.objects.last()
    
    # 7. Precisión
    calidad = DimActa.objects.aggregate(promedio=Avg('precision_transcripcion'))
    precision_avg = calidad['promedio'] or 0
    
    # Detalle (Modal)
    qs_detalle = DimActa.objects.all()
    if anio: qs_detalle = qs_detalle.filter(fecha_reunion__year=anio)
    if mes: qs_detalle = qs_detalle.filter(fecha_reunion__month=mes)
    detalle_precision = list(qs_detalle.values('titulo', 'fecha_reunion', 'precision_transcripcion').order_by('-fecha_reunion'))

    # --- CÁLCULO DE TIEMPO GLOBAL (Tarjeta Azul) ---
    tiempo_segundos = 0.0
    if metricas and metricas.tiempo_respuesta_ms:
        # Dividimos por 1000 para pasar de ms a segundos
        tiempo_segundos = round(metricas.tiempo_respuesta_ms / 1000.0, 2)

    # --- DETALLE DE RENDIMIENTO (Tabla del Modal) ---
    # 1. Traemos los últimos 50 logs de la base de datos
    logs_db = LogRendimiento.objects.all().order_by('-fecha')[:50]
    
    # 2. Creamos la lista final convirtiendo ms a s fila por fila
    detalle_rendimiento = []
    for log in logs_db:
        detalle_rendimiento.append({
            'path': log.path,
            'usuario': log.usuario,
            'tiempo_ms': log.tiempo_ms,
            'tiempo_s': round(log.tiempo_ms / 1000.0, 2) # <--- Tu cálculo correcto
        })

    # --- DETALLE PARA EL MODAL (Últimos 50 registros) ---
    detalle_disponibilidad = [] # Lista nueva para el modal
    for log in logs_db:
        # Determinamos si fue éxito o error para mostrarlo bonito
        es_error = log.status_code >= 500
        detalle_disponibilidad.append({
            'path': log.path,
            'fecha': log.fecha,
            'status': log.status_code,
            'es_error': es_error
        })

    return {
        "ocupacion_talleres": data_ocupacion_talleres,
        "consulta_actas": data_consulta_actas,
        "participacion": data_participacion,
        "demografia_sector": data_demografia_sector,
        "data_asistencia": data_asistencia,
        "metricas": metricas,
        "precision": round(precision_avg, 1),
        "detalle_precision": detalle_precision,
        "detalle_rendimiento": detalle_rendimiento,
        "tiempo_segundos": tiempo_segundos,
        "detalle_disponibilidad": detalle_disponibilidad,
    }

@login_required
@user_passes_test(es_usuario_directiva)
def panel_bi_view(request):
    mes = request.GET.get('mes'); anio = request.GET.get('anio')
    try: mes = int(mes) if mes else None; anio = int(anio) if anio else None
    except: mes = None; anio = None

    anios_opciones = list(FactAsistenciaReunion.objects.annotate(anio=ExtractYear('reunion__fecha')).values_list('anio', flat=True).distinct().order_by('anio'))
    if not anios_opciones: anios_opciones = [timezone.now().year]

    datos = construir_datos_panel_bi(mes, anio)
    meses_opciones = [{'num': i, 'nombre': MESES_ES[i]} for i in range(1, 13)]

    context = {
        "data_ocupacion_talleres": json.dumps(datos["ocupacion_talleres"]),
        "data_consulta_actas": json.dumps(datos["consulta_actas"]),
        "data_participacion": json.dumps(datos["participacion"]),
        "data_demografia_sector": json.dumps(datos["demografia_sector"]),
        "data_asistencia": json.dumps(datos["data_asistencia"]),

        "detalle_rendimiento": datos["detalle_rendimiento"],
        "tiempo_segundos": datos["tiempo_segundos"],
        "metricas": datos["metricas"],
        "precision": datos["precision"],
        "detalle_precision": datos["detalle_precision"],
        "detalle_disponibilidad": datos["detalle_disponibilidad"],
        
        "anios_opciones": anios_opciones,
        "meses_opciones": meses_opciones,
        "mes_seleccionado": mes,
        "anio_seleccionado": anio,
    }
    return render(request, "datamart/panel_bi.html", context)

@login_required
@user_passes_test(es_usuario_directiva)
def ejecutar_etl_view(request):
    if request.method == 'POST':
        try:
            call_command("procesar_etl")
            messages.success(request, "Datos actualizados.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
    return redirect("panel_bi")

@login_required
def generar_pdf_view(request):
    datos = construir_datos_panel_bi()
    context = {
        "fecha_generacion": timezone.localtime(),
        "usuario_generador": request.user,
        "ocupacion_talleres": datos["ocupacion_talleres"],
        "consulta_actas": datos["consulta_actas"],
        "participacion": datos["participacion"],
        "demografia_sector": datos["demografia_sector"],
        "data_asistencia": datos["data_asistencia"],
        # ⚠️ ELIMINADO: data_uso_app
        "metricas": datos["metricas"],
        "precision": datos["precision"],
        "detalle_precision": datos["detalle_precision"],
    }
    template = get_template("datamart/reporte_pdf.html")
    html = template.render(context, request=request)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="Informe.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err: return HttpResponse('Error PDF')
    return response