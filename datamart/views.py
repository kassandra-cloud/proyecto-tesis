import json
import re  # para limpiar números en las direcciones
import calendar  # (ya casi no lo usamos, pero lo puedes dejar)
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

from datamart.models import (
    FactInscripcionTaller, DimTaller, FactConsultaActa,
    FactParticipacionVotacion, DimVecino, FactAsistenciaReunion,
    DimActa, FactMetricasDiarias
)

# 🔹 Meses en español
MESES_ES = [
    "",  # índice 0 vacío
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]


def es_usuario_directiva(user):
    return user.is_authenticated


def construir_datos_panel_bi(mes=None, anio=None):
    # 1. Ocupación Talleres
    inscritos_qs = (
        FactInscripcionTaller.objects
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

    # 2. Consulta Actas
    data_consulta_actas = list(
        FactConsultaActa.objects
        .values("acta__titulo")
        .annotate(consultas=Count("id"))
        .order_by("-consultas")[:10]
    )

    # 3. Participación Votaciones
    total_vecinos = DimVecino.objects.count()
    total_participantes = (
        FactParticipacionVotacion.objects
        .values("vecino_id").distinct()
        .count()
    )
    porcentaje_actual = (
        float(total_participantes) / float(total_vecinos) * 100.0
        if total_vecinos > 0 else 0.0
    )
    data_participacion = {
        "total_vecinos": total_vecinos,
        "total_participantes": total_participantes,
        "porcentaje_actual": porcentaje_actual,
        "porcentaje_meta": 50.0,
    }

    # 4. Demografía por sector
    data_demografia_sector = list(
        DimVecino.objects
        .values("direccion_sector")
        .annotate(total_vecinos=Count("id"))
        .order_by("-total_vecinos")
    )

    for row in data_demografia_sector:
        original = row["direccion_sector"] or ""
        solo_texto = re.sub(r"\d+", "", original).strip()
        row["direccion_sector"] = solo_texto or "Sin Dirección"

    # 5. Asistencia Reuniones (filtro mes/año opcional)
    asistencia_qs = FactAsistenciaReunion.objects.all()

    if mes and anio:
        asistencia_qs = asistencia_qs.filter(
            reunion__fecha__year=anio,
            reunion__fecha__month=mes,
        )

    asistencia_qs = (
        asistencia_qs
        .values("reunion__fecha")
        .annotate(total=Count("id"))
        .order_by("reunion__fecha")
    )

    data_asistencia = [
        {
            "fecha": item["reunion__fecha"].strftime("%Y-%m-%d"),
            "total": item["total"],
        }
        for item in asistencia_qs
    ]

    # 6. Uso App Móvil
    usuarios_app = DimVecino.objects.filter(usa_app_movil=True).count()
    data_uso_app = {
        "app": usuarios_app,
        "web": total_vecinos - usuarios_app,
    }

    # 7. Métricas Técnicas
    metricas = FactMetricasDiarias.objects.last()
    precision_avg = (
        DimActa.objects.aggregate(Avg("precision_transcripcion"))[
            "precision_transcripcion__avg"
        ] or 0
    )

    return {
        "ocupacion_talleres": data_ocupacion_talleres,
        "consulta_actas": data_consulta_actas,
        "participacion": data_participacion,
        "demografia_sector": data_demografia_sector,
        "data_asistencia": data_asistencia,
        "data_uso_app": data_uso_app,
        "metricas": metricas,
        "precision": round(precision_avg, 1),
    }


@login_required
@user_passes_test(es_usuario_directiva)
def panel_bi_view(request):
    # Filtros
    mes_str = (request.GET.get("mes") or "").strip()
    anio_str = (request.GET.get("anio") or "").strip()

    mes = int(mes_str) if mes_str.isdigit() else None
    anio = int(anio_str) if anio_str.isdigit() else None

    # Años disponibles desde la BD
    anios_opciones = list(
        FactAsistenciaReunion.objects
        .annotate(anio=ExtractYear("reunion__fecha"))
        .values_list("anio", flat=True)
        .distinct()
        .order_by("anio")
    )

    # Si no hay años, rango por defecto
    now = timezone.now()
    if not anios_opciones:
        anio_actual = now.year
        anios_opciones = list(range(anio_actual - 2, anio_actual + 1))

    # Datos del panel
    datos = construir_datos_panel_bi(mes=mes, anio=anio)

    # Meses en español
    meses_opciones = [
        {"numero": i, "nombre": MESES_ES[i]}
        for i in range(1, 13)
    ]

    context = {
        "data_ocupacion_talleres": json.dumps(datos["ocupacion_talleres"]),
        "data_consulta_actas": json.dumps(datos["consulta_actas"]),
        "data_participacion": json.dumps(datos["participacion"]),
        "data_demografia_sector": json.dumps(datos["demografia_sector"]),
        "data_asistencia": json.dumps(datos["data_asistencia"]),
        "data_uso_app": json.dumps(datos["data_uso_app"]),
        "metricas": datos["metricas"],
        "precision": datos["precision"],
        "meses_opciones": meses_opciones,
        "anios_opciones": anios_opciones,
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
            messages.success(request, "Datos actualizados correctamente.")
        except Exception as e:
            messages.error(request, f"Error en ETL: {e}")
    return redirect("panel_bi")


@login_required
@user_passes_test(es_usuario_directiva)
def generar_pdf_view(request):
    datos = construir_datos_panel_bi()
    context = {
        "fecha_generacion": timezone.localtime(),
        "ocupacion_talleres": datos["ocupacion_talleres"],
        "consulta_actas": datos["consulta_actas"],
        "participacion": datos["participacion"],
        "demografia_sector": datos["demografia_sector"],
        "data_asistencia": datos["data_asistencia"],
        "metricas": datos["metricas"],
        "precision": datos["precision"],
    }
    template = get_template("datamart/reporte_pdf.html")
    html = template.render(context, request=request)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="Informe_Gestion.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Error PDF")
    return response
