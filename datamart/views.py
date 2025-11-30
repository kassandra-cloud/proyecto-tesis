# datamart/views.py

import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.management import call_command
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.utils import timezone

from xhtml2pdf import pisa

from datamart.models import (
    FactInscripcionTaller,
    DimTaller,
    FactConsultaActa,
    FactParticipacionVotacion,
    DimVecino,
)


# ============================================================
# Helper de permisos
# ============================================================

def es_usuario_directiva(user):
    """
    Versión relajada para que puedas entrar con cualquier usuario autenticado.
    Más adelante se puede volver a restringir solo a la directiva.
    """
    return user.is_authenticated

    # Si luego quieres restringir solo a la directiva, puedes usar esto:
    #
    # if not user.is_authenticated:
    #     return False
    #
    # perfil = getattr(user, "perfil", None)
    # if perfil is None:
    #     return False
    #
    # rol_actual = str(perfil.rol).strip().lower()
    # roles_permitidos = ["presidente", "secretaria", "tesorero", "suplente"]
    # return rol_actual in roles_permitidos


# ============================================================
# Construcción de datos para el Panel BI (reutilizable)
# ============================================================

def construir_datos_panel_bi():
    """
    Construye los datos crudos para el panel BI.
    Se reutiliza tanto para la vista HTML como para el PDF.
    """

    # 1) Ocupación de talleres: inscritos vs cupos (FIX: Incluir talleres con 0 inscritos)
    
    # Obtener el conteo de inscritos por taller eficientemente
    inscritos_qs = (
        FactInscripcionTaller.objects
        .values("taller__id")
        .annotate(total_inscritos=Count("id"))
    )
    # Mapear conteos a un diccionario para búsqueda rápida: {taller_id: total_inscritos}
    inscritos_por_id = {item['taller__id']: item['total_inscritos'] for item in inscritos_qs}

    data_ocupacion_talleres = []
    # Iterar sobre TODOS los talleres (DimTaller) para incluir los que tienen 0 inscritos
    for taller in DimTaller.objects.all().order_by('nombre'):
        taller_id = taller.id
        # Obtener los inscritos, por defecto 0 si no hay registros en FactInscripcionTaller
        inscritos = inscritos_por_id.get(taller_id, 0) 
        
        data_ocupacion_talleres.append(
            {
                "nombre": taller.nombre,
                "inscritos": inscritos,
                "cupos": taller.cupos_totales,
            }
        )

    # 2) Consultas de actas (top 10) - Lógica correcta, el problema de visualización estaba en el JS.
    data_consulta_actas = list(
        FactConsultaActa.objects
        .values("acta__titulo")
        .annotate(consultas=Count("id"))
        .order_by("-consultas")[:10]
    )

    # 3) Participación en votaciones
    total_vecinos = DimVecino.objects.count()
    total_participantes = (
        FactParticipacionVotacion.objects
        .values("vecino_id")
        .distinct()
        .count()
    )

    meta_participacion = 0.5  # meta del 50 %

    if total_vecinos > 0:
        porcentaje_actual = float(total_participantes) / float(total_vecinos) * 100.0
    else:
        porcentaje_actual = 0.0

    data_participacion = {
        "total_vecinos": total_vecinos,
        "total_participantes": total_participantes,
        "porcentaje_actual": porcentaje_actual,
        "porcentaje_meta": meta_participacion * 100.0,
    }

    # 4) Demografía por sector
    data_demografia_sector = list(
        DimVecino.objects
        .values("direccion_sector")
        .annotate(total_vecinos=Count("id"))
        .order_by("-total_vecinos")
    )

    return {
        "ocupacion_talleres": data_ocupacion_talleres,
        "consulta_actas": data_consulta_actas,
        "participacion": data_participacion,
        "demografia_sector": data_demografia_sector,
    }


# ============================================================
# Vista Panel BI (HTML + Chart.js)
# URL: /analitica/panel-bi/  name='panel_bi'
# ============================================================

@login_required
@user_passes_test(es_usuario_directiva)
def panel_bi_view(request):
    """
    Renderiza el panel de Business Intelligence con gráficos en Chart.js.
    """

    datos = construir_datos_panel_bi()

    context = {
        "data_ocupacion_talleres": json.dumps(datos["ocupacion_talleres"]),
        "data_consulta_actas": json.dumps(datos["consulta_actas"]),
        "data_participacion": json.dumps(datos["participacion"]),
        "data_demografia_sector": json.dumps(datos["demografia_sector"]),
    }

    return render(request, "datamart/panel_bi.html", context)


# ============================================================
# Vista para ejecutar la ETL del datamart
# URL: /analitica/ejecutar-etl/  name='ejecutar_etl'
# ============================================================

@login_required
@user_passes_test(es_usuario_directiva)
def ejecutar_etl_view(request):
    """
    Ejecuta el comando de gestión 'procesar_etl' que carga y actualiza el datamart.
    Se muestra un mensaje de éxito o error y se redirige al panel BI.
    """
    if request.method == 'POST':
        try:
            call_command("procesar_etl")
            messages.success(
                request,
                "La actualización de datos del panel BI se ejecutó correctamente."
            )
        except Exception as e:
            messages.error(
                request,
                f"Ocurrió un error al ejecutar la ETL del datamart: {e}"
            )

    # Nota: Si se llama a esta vista sin POST, simplemente redirige.
    return redirect("panel_bi")


# ============================================================
# Generación de informe PDF con xhtml2pdf
# URL: /analitica/descargar-informe/  name='descargar_pdf'
# ============================================================

@login_required
@user_passes_test(es_usuario_directiva)
def generar_pdf_view(request):
    """
    Genera un informe en PDF con un resumen de la gestión,
    reutilizando los mismos datos del panel BI.
    """
    fecha_actual = timezone.localtime()
    # Se añade un periodo de 30 días para contexto en el PDF
    hace_30_dias = fecha_actual - timedelta(days=30) 

    # Datos principales (mismos que el panel)
    datos = construir_datos_panel_bi()

    context = {
        "fecha_generacion": fecha_actual,
        "periodo_desde": hace_30_dias,
        "periodo_hasta": fecha_actual,
        "ocupacion_talleres": datos["ocupacion_talleres"],
        "consulta_actas": datos["consulta_actas"],
        "participacion": datos["participacion"],
        "demografia_sector": datos["demografia_sector"],
    }

    template_path = "datamart/reporte_pdf.html"
    template = get_template(template_path)
    html = template.render(context, request=request)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="Informe_Gestion_VillaVistaAlMar.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        # Se incluye el HTML en la respuesta de error para facilitar el debugging del PDF
        return HttpResponse('Hubo un error al generar el PDF <pre>' + html + '</pre>')

    return response