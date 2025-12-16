import json
import re
from datetime import timedelta

from django.core.cache import cache
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

from datamart.tasks import tarea_actualizar_bi_async

from datamart.models import (
    FactInscripcionTaller,
    DimTaller,
    FactConsultaActa,
    FactParticipacionVotacion,
    DimVecino,
    FactAsistenciaReunion,
    DimActa,
    FactMetricasDiarias,
    LogRendimiento,
)

MESES_ES = [
    "",
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]


def es_usuario_directiva(user):
    # Por ahora: cualquier usuario autenticado puede ver el BI.
    # Si quieres restringir a grupo "Directiva", puedes usar:
    # return user.is_authenticated and (user.is_staff or user.groups.filter(name="Directiva").exists())
    return user.is_authenticated


def construir_datos_panel_bi(mes=None, anio=None):
    """
    Construye los datasets para el panel BI.
    Si se indican mes y/o año, se filtra TODA la información temporal
    (inscripciones, consultas de actas, votaciones, asistencia, logs y actas).
    """

    # Helper para reutilizar filtro de fecha en distintos modelos/campos
    def filtrar_por_fecha(qs, campo_fecha: str):
        if anio:
            qs = qs.filter(**{f"{campo_fecha}__year": anio})
        if mes:
            qs = qs.filter(**{f"{campo_fecha}__month": mes})
        return qs

    # 1) OCUPACIÓN DE TALLERES (filtrado por fecha_inscripcion)
    inscritos_qs = FactInscripcionTaller.objects.all()
    inscritos_qs = filtrar_por_fecha(inscritos_qs, "fecha_inscripcion")

    inscritos_qs = (
        inscritos_qs
        .values("taller__id")
        .annotate(total_inscritos=Count("id"))
    )
    inscritos_por_id = {
        item["taller__id"]: item["total_inscritos"]
        for item in inscritos_qs
    }

    data_ocupacion_talleres = []
    for taller in DimTaller.objects.all().order_by("nombre"):
        data_ocupacion_talleres.append({
            "nombre": taller.nombre,
            "inscritos": inscritos_por_id.get(taller.id, 0),
            "cupos": taller.cupos_totales,
        })

    # 2) CONSULTA DE ACTAS (Top 10) filtrado por fecha_consulta
    consulta_qs = FactConsultaActa.objects.all()
    consulta_qs = filtrar_por_fecha(consulta_qs, "fecha_consulta")

    data_consulta_actas = list(
        consulta_qs
        .values("acta__titulo")
        .annotate(consultas=Count("id"))
        .order_by("-consultas")[:10]
    )

    # 3) PARTICIPACIÓN EN VOTACIONES (porcentaje en el período)
    voto_qs = FactParticipacionVotacion.objects.all()
    voto_qs = filtrar_por_fecha(voto_qs, "fecha_voto")

    total_vecinos = DimVecino.objects.count() or 1  # universo total
    total_part = (
        voto_qs
        .values("vecino_id")
        .distinct()
        .count()
    )
    porcentaje_actual = (
        float(total_part) / float(total_vecinos) * 100.0
        if total_vecinos > 0 else 0.0
    )

    data_participacion = {
        "total_vecinos": total_vecinos,
        "total_participantes": total_part,
        "porcentaje_actual": round(porcentaje_actual, 1),
        "porcentaje_meta": 50.0,
    }

    # 4) DEMOGRAFÍA POR SECTOR filtrada POR ACTIVIDAD en el período
    vecinos_ids_actividad = set()

    # Inscripciones
    ins_qs = FactInscripcionTaller.objects.all()
    ins_qs = filtrar_por_fecha(ins_qs, "fecha_inscripcion")
    vecinos_ids_actividad.update(ins_qs.values_list("vecino_id", flat=True))

    # Asistencia
    asis_qs = FactAsistenciaReunion.objects.all()
    asis_qs = filtrar_por_fecha(asis_qs, "reunion__fecha")
    vecinos_ids_actividad.update(asis_qs.values_list("vecino_id", flat=True))

    # Votaciones
    voto_qs_ids = FactParticipacionVotacion.objects.all()
    voto_qs_ids = filtrar_por_fecha(voto_qs_ids, "fecha_voto")
    vecinos_ids_actividad.update(voto_qs_ids.values_list("vecino_id", flat=True))

    # Consultas de actas
    cons_qs_ids = FactConsultaActa.objects.all()
    cons_qs_ids = filtrar_por_fecha(cons_qs_ids, "fecha_consulta")
    vecinos_ids_actividad.update(cons_qs_ids.values_list("vecino_id", flat=True))

    if vecinos_ids_actividad:
        vecinos_demografia = DimVecino.objects.filter(id__in=vecinos_ids_actividad)
    else:
        vecinos_demografia = DimVecino.objects.none()

    # ✅ IMPORTANTE: ya NO sobrescribimos con DimVecino.objects.all() (eso rompía el filtro)

    data_demografia_sector = list(
        vecinos_demografia
        .values("direccion_sector")
        .annotate(total_vecinos=Count("id"))
        .order_by("-total_vecinos")
    )

    # Limpiar números de las direcciones para agrupar mejor (Ej: "Pasaje 1 #123" -> "Pasaje 1")
    for row in data_demografia_sector:
        original = row["direccion_sector"] or ""
        solo_texto = re.sub(r"\d+$", "", original).strip()
        row["direccion_sector"] = solo_texto if len(solo_texto) > 2 else (original or "Sin Dirección")

    # 5) ASISTENCIA A REUNIONES
    asistencia_qs = FactAsistenciaReunion.objects.all()
    asistencia_qs = filtrar_por_fecha(asistencia_qs, "reunion__fecha")

    asist_agrupada = (
        asistencia_qs
        .values("reunion__fecha", "reunion__titulo")
        .annotate(total=Count("id"))
        .order_by("reunion__fecha")
    )
    data_asistencia = [
        {
            "fecha": item["reunion__fecha"].strftime("%Y-%m-%d"),
            "titulo": item["reunion__titulo"],
            "total": item["total"],
        }
        for item in asist_agrupada
    ]

    # 6) MÉTRICAS TÉCNICAS (último registro)
    # ⚠️ Esto NO se filtra por mes/año. Si quieres filtrarlo por periodo, dime el campo fecha de FactMetricasDiarias.
    metricas = FactMetricasDiarias.objects.last()

    # 7) PRECISIÓN PROMEDIO (solo actas del periodo)
    calidad_qs = DimActa.objects.all()
    calidad_qs = filtrar_por_fecha(calidad_qs, "fecha_reunion")

    precision_avg_dict = calidad_qs.aggregate(promedio=Avg("precision_transcripcion"))
    precision_avg = precision_avg_dict["promedio"] or 0

    detalle_precision_qs = DimActa.objects.all()
    detalle_precision_qs = filtrar_por_fecha(detalle_precision_qs, "fecha_reunion")

    detalle_precision = list(
        detalle_precision_qs
        .values("titulo", "fecha_reunion", "precision_transcripcion")
        .order_by("-fecha_reunion")
    )

    # 8) TIEMPO DE RESPUESTA GLOBAL
    tiempo_segundos = 0.0
    if metricas and metricas.tiempo_respuesta_ms:
        tiempo_segundos = round(metricas.tiempo_respuesta_ms / 1000.0, 2)

    # 9) LOGS DE RENDIMIENTO (solo sitio web, filtrados por fecha)
    logs_db = LogRendimiento.objects.exclude(path__startswith="/api/")
    logs_db = filtrar_por_fecha(logs_db, "fecha")
    logs_db = logs_db.order_by("-fecha")[:50]

    detalle_rendimiento = []
    for log in logs_db:
        detalle_rendimiento.append({
            "path": log.path,
            "usuario": log.usuario,
            "tiempo_ms": log.tiempo_ms,
            "tiempo_s": round(log.tiempo_ms / 1000.0, 2),
        })

    detalle_disponibilidad = []
    for log in logs_db:
        es_error = log.status_code >= 500
        detalle_disponibilidad.append({
            "path": log.path,
            "fecha": log.fecha,
            "status": log.status_code,
            "es_error": es_error,
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
    # --- Cooldown ETL (Celery) ---
    CACHE_KEY_COOLDOWN = "cooldown_etl_bi"
    TIEMPO_COOLDOWN_SEGUNDOS = 300  # 5 minutos

    if not cache.get(CACHE_KEY_COOLDOWN):
        tarea_actualizar_bi_async.delay()
        cache.set(CACHE_KEY_COOLDOWN, True, TIEMPO_COOLDOWN_SEGUNDOS)
        messages.info(request, "Actualizando datos en segundo plano... Recarga en unos instantes.")

    # --- Filtros ---
    mes = request.GET.get("mes")
    anio = request.GET.get("anio")
    try:
        mes = int(mes) if mes else None
        anio = int(anio) if anio else None
    except Exception:
        mes = None
        anio = None

    anios_opciones = list(
        FactAsistenciaReunion.objects
        .annotate(anio=ExtractYear("reunion__fecha"))
        .values_list("anio", flat=True)
        .distinct()
        .order_by("anio")
    )
    if not anios_opciones:
        anios_opciones = [timezone.now().year]

    datos = construir_datos_panel_bi(mes, anio)
    meses_opciones = [{"num": i, "nombre": MESES_ES[i]} for i in range(1, 13)]

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
    if request.method == "POST":
        try:
            call_command("procesar_etl")
            messages.success(request, "Datos actualizados.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
    return redirect("panel_bi")


@login_required
def generar_pdf_view(request):
    """
    Genera un PDF con la MISMA información que alimenta los gráficos del panel BI:
    - Demografía
    - Ocupación de talleres
    - Actas consultadas
    - Asistencia (con nombre de la reunión)
    - Precisión de transcripciones
    - Rendimiento y disponibilidad SOLO del sitio web
    """
    datos = construir_datos_panel_bi()

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
    }

    template = get_template("datamart/reporte_pdf.html")
    html = template.render(context, request=request)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="Informe.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Error PDF")
    return response
