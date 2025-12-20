"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Vistas encargadas de construir los datos para el dashboard de BI, 
               manejar el caché, ejecutar el ETL asíncrono y generar reportes PDF.
--------------------------------------------------------------------------------
"""
import json
import re
from datetime import datetime

from django.core.cache import cache  # Sistema de caché de Django
from django.contrib import messages  # Framework de mensajes flash
from django.contrib.auth.decorators import login_required, user_passes_test  # Decoradores de seguridad
from django.db.models import Count, Avg  # Funciones de agregación SQL
from django.db.models.functions import ExtractYear  # Función para extraer año
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.utils import timezone
from xhtml2pdf import pisa  # Librería para generar PDF desde HTML

from datamart.tasks import tarea_actualizar_bi_async  # Importa tarea de Celery
from datamart.models import (
    FactInscripcionTaller, DimTaller, FactConsultaActa, FactParticipacionVotacion,
    DimVecino, FactAsistenciaReunion, DimActa, FactMetricasDiarias, LogRendimiento,
)

# Lista de nombres de meses en español para visualización
MESES_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

# Verifica si el usuario tiene permiso para ver el BI (en este caso, solo estar logueado)
def es_usuario_directiva(user):
    return user.is_authenticated

def construir_datos_panel_bi(mes=None, anio=None):
    """
    Función auxiliar que construye los datasets para el BI.
    Filtra Facts y Logs según el mes y año proporcionados.
    """

    # Helper para aplicar filtros de fecha dinámicos a querysets
    def filtrar_por_fecha(qs, campo_fecha: str):
        if anio:
            qs = qs.filter(**{f"{campo_fecha}__year": anio})
        if mes:
            qs = qs.filter(**{f"{campo_fecha}__month": mes})
        return qs

    # Calcula rangos de fecha precisos (inicio y fin de mes) con timezone aware
    def rango_mes_datetime(anio_in=None, mes_in=None):
        hoy = timezone.localdate()
        y = anio_in or hoy.year
        m = mes_in or hoy.month
        inicio = timezone.make_aware(datetime(y, m, 1))
        if m == 12:
            fin = timezone.make_aware(datetime(y + 1, 1, 1))
        else:
            fin = timezone.make_aware(datetime(y, m + 1, 1))
        return inicio, fin

    # 1) KPI: Ocupación de Talleres
    inscritos_qs = filtrar_por_fecha(FactInscripcionTaller.objects.all(), "fecha_inscripcion")
    inscritos_qs = inscritos_qs.values("taller__id").annotate(total=Count("id"))
    inscritos_por_id = {i["taller__id"]: i["total"] for i in inscritos_qs}

    data_ocupacion_talleres = [
        {"nombre": t.nombre, "inscritos": inscritos_por_id.get(t.id, 0), "cupos": t.cupos_totales}
        for t in DimTaller.objects.all().order_by("nombre")
    ]

    # 2) KPI: Top 10 Actas más consultadas
    consulta_qs = filtrar_por_fecha(FactConsultaActa.objects.all(), "fecha_consulta")
    data_consulta_actas = list(
        consulta_qs.values("acta__titulo")
        .annotate(consultas=Count("id"))
        .order_by("-consultas")[:10]
    )

    # 3) KPI: Participación en Votaciones (Vecinos activos vs Votantes)
    voto_qs = filtrar_por_fecha(FactParticipacionVotacion.objects.all(), "fecha_voto")
    total_vecinos = DimVecino.objects.count() or 1
    total_part = voto_qs.values("vecino_id").distinct().count()
    porcentaje_actual = (total_part / total_vecinos) * 100 if total_vecinos else 0

    data_participacion = {
        "total_vecinos": total_vecinos,
        "total_participantes": total_part,
        "porcentaje_actual": round(porcentaje_actual, 1),
        "porcentaje_meta": 50.0,
    }

    # 4) KPI: Demografía por sector basada en actividad
    vecinos_ids = set()
    # Recolecta IDs de vecinos activos en cualquier módulo
    ins_qs = filtrar_por_fecha(FactInscripcionTaller.objects.all(), "fecha_inscripcion")
    vecinos_ids.update(ins_qs.values_list("vecino_id", flat=True))
    asis_qs = filtrar_por_fecha(FactAsistenciaReunion.objects.all(), "reunion__fecha")
    vecinos_ids.update(asis_qs.values_list("vecino_id", flat=True))
    voto_qs_ids = filtrar_por_fecha(FactParticipacionVotacion.objects.all(), "fecha_voto")
    vecinos_ids.update(voto_qs_ids.values_list("vecino_id", flat=True))
    cons_qs_ids = filtrar_por_fecha(FactConsultaActa.objects.all(), "fecha_consulta")
    vecinos_ids.update(cons_qs_ids.values_list("vecino_id", flat=True))

    vecinos = DimVecino.objects.filter(id__in=vecinos_ids) if vecinos_ids else DimVecino.objects.none()
    
    # Agrupa por dirección
    data_demografia_sector = list(
        vecinos.values("direccion_sector")
        .annotate(total_vecinos=Count("id"))
        .order_by("-total_vecinos")
    )

    # Limpia las direcciones (quita números) para agrupar mejor
    for row in data_demografia_sector:
        original = row["direccion_sector"] or ""
        solo_texto = re.sub(r"\d+$", "", original).strip()
        row["direccion_sector"] = solo_texto if solo_texto else "Sin Dirección"

    # 5) KPI: Asistencia a reuniones
    asistencia_qs = filtrar_por_fecha(FactAsistenciaReunion.objects.all(), "reunion__fecha")
    asist_agrupada = (
        asistencia_qs.values("reunion__fecha", "reunion__titulo")
        .annotate(total=Count("id"))
        .order_by("reunion__fecha")
    )
    data_asistencia = [
        {"fecha": i["reunion__fecha"].strftime("%Y-%m-%d"), "titulo": i["reunion__titulo"], "total": i["total"]}
        for i in asist_agrupada
    ]

    # 6) Obtiene últimas métricas técnicas guardadas
    metricas = FactMetricasDiarias.objects.last()

    # 7) KPI: Calidad de Transcripción (Promedio)
    calidad_qs = filtrar_por_fecha(DimActa.objects.all(), "fecha_reunion")
    precision_avg = calidad_qs.aggregate(p=Avg("precision_transcripcion"))["p"] or 0
    detalle_precision = list(
        calidad_qs.values("titulo", "fecha_reunion", "precision_transcripcion")
        .order_by("-fecha_reunion")
    )

    # 8) KPI: Rendimiento del sistema (Logs en tiempo real)
    inicio, fin = rango_mes_datetime(anio, mes)
    logs_base = LogRendimiento.objects.filter(fecha__gte=inicio, fecha__lt=fin)

    # Limpieza de logs irrelevantes (favicon, root, anónimos)
    logs_base = logs_base.exclude(path="/").exclude(path="/favicon.ico")
    logs_base = logs_base.exclude(usuario__isnull=True).exclude(usuario__iexact="anónimo").exclude(usuario__exact="")

    # Tiempo promedio global
    avg_ms = logs_base.aggregate(p=Avg("tiempo_ms"))["p"] or 0
    tiempo_prom = round(float(avg_ms) / 1000.0, 2)

    # Tiempo Percentil 95 (P95)
    qs_ms = logs_base.order_by("tiempo_ms").values_list("tiempo_ms", flat=True)
    n = qs_ms.count()
    p95_ms = 0
    if n:
        idx = max(0, int(n * 0.95) - 1)
        p95_ms = qs_ms[idx]
    tiempo_p95 = round(float(p95_ms) / 1000.0, 2)

    # Obtiene detalles limitados para visualización rápida en tablas
    logs_db = logs_base.order_by("-fecha")[:50]
    detalle_rendimiento = [
        {"path": l.path, "usuario": l.usuario, "tiempo_ms": l.tiempo_ms, "tiempo_s": round(l.tiempo_ms / 1000.0, 2)}
        for l in logs_db
    ]
    detalle_disponibilidad = [
        {"path": l.path, "fecha": l.fecha, "status": l.status_code, "es_error": l.status_code >= 500}
        for l in logs_db
    ]

    return {
        "ocupacion_talleres": data_ocupacion_talleres,
        "consulta_actas": data_consulta_actas,
        "participacion": data_participacion,
        "demografia_sector": data_demografia_sector,
        "data_asistencia": data_asistencia,
        "metricas": metricas,
        "precision": round(precision_avg, 1),
        "detalle_precision": detalle_precision,
        "tiempo_segundos": tiempo_prom,
        "tiempo_p95_seg": tiempo_p95,
        "detalle_rendimiento": detalle_rendimiento,
        "detalle_disponibilidad": detalle_disponibilidad,
    }

# Vista principal del panel BI
@login_required
@user_passes_test(es_usuario_directiva)
def panel_bi_view(request):
    # Procesa filtros de mes y año desde la URL
    mes = request.GET.get("mes")
    anio = request.GET.get("anio")
    try:
        mes = int(mes) if mes else None
        anio = int(anio) if anio else None
    except Exception:
        mes = None
        anio = None

    # Obtiene lista de años disponibles en base a asistencia
    anios_opciones = list(
        FactAsistenciaReunion.objects
        .annotate(anio=ExtractYear("reunion__fecha"))
        .values_list("anio", flat=True)
        .distinct()
        .order_by("anio")
    ) or [timezone.localdate().year]

    # Gestión de Caché para optimizar carga (clave única por filtro)
    cache_key = f"bi_panel_ctx_{anio or 'now'}_{mes or 'now'}"
    context = cache.get(cache_key)

    if not context:
        # Si no está en caché, calcula todo
        datos = construir_datos_panel_bi(mes, anio)
        meses_opciones = [{"num": i, "nombre": MESES_ES[i]} for i in range(1, 13)]

        context = {
            # Serializa a JSON los datos complejos para usarlos en gráficos JS
            "data_ocupacion_talleres": json.dumps(datos["ocupacion_talleres"]),
            "data_consulta_actas": json.dumps(datos["consulta_actas"]),
            "data_participacion": json.dumps(datos["participacion"]),
            "data_demografia_sector": json.dumps(datos["demografia_sector"]),
            "data_asistencia": json.dumps(datos["data_asistencia"]),
            
            # Datos directos para tablas HTML
            "detalle_rendimiento": datos["detalle_rendimiento"],
            "detalle_disponibilidad": datos["detalle_disponibilidad"],
            "tiempo_segundos": datos["tiempo_segundos"],
            "tiempo_p95_seg": datos["tiempo_p95_seg"],
            "metricas": datos["metricas"],
            "precision": datos["precision"],
            "detalle_precision": datos["detalle_precision"],

            # Opciones de filtrado
            "anios_opciones": anios_opciones,
            "meses_opciones": meses_opciones,
            "mes_seleccionado": mes,
            "anio_seleccionado": anio,
        }

        # Guarda en caché por 90 segundos
        cache.set(cache_key, context, 90)

    return render(request, "datamart/panel_bi.html", context)


# Vista para ejecutar el ETL manualmente
@login_required
@user_passes_test(es_usuario_directiva)
def ejecutar_etl_view(request):
    """
    Botón 'Actualizar Datos' dispara tarea Celery y limpia la caché.
    """
    if request.method == "POST":
        # Lanza tarea asíncrona
        tarea_actualizar_bi_async.delay()

        # Invalida caché para forzar recálculo en próximas visitas
        cache.delete("bi_panel_ctx_now_now")
        for m in range(1, 13):
            cache.delete(f"bi_panel_ctx_now_{m}")

        messages.success(request, "Actualización iniciada. Recarga el panel en 10–30 segundos.")
    return redirect("panel_bi")


# Vista para generar y descargar informe PDF
@login_required
def generar_pdf_view(request):
    datos = construir_datos_panel_bi()

    # Prepara contexto exclusivo para la plantilla PDF
    context = {
        "fecha_generacion": timezone.localtime(),
        "usuario": request.user.get_full_name() or request.user.username,
        "ocupacion_talleres": datos["ocupacion_talleres"],
        "consulta_actas": datos["consulta_actas"],
        "participacion": datos["participacion"],
        "demografia_sector": datos["demografia_sector"],
        "data_asistencia": datos["data_asistencia"],
        "metricas": datos["metricas"],
        "precision": datos["precision"],
        "detalle_precision": datos["detalle_precision"],
        "detalle_rendimiento": datos["detalle_rendimiento"],
        "detalle_disponibilidad": datos["detalle_disponibilidad"],
        "tiempo_segundos": datos["tiempo_segundos"],
        "tiempo_p95_seg": datos["tiempo_p95_seg"],
    }

    # Renderiza plantilla HTML
    template = get_template("datamart/reporte_pdf.html")
    html = template.render(context, request=request)

    # Convierte HTML a PDF usando xhtml2pdf
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="Informe.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse("Error PDF")
    return response