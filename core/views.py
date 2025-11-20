from django.shortcuts import render
from reuniones.models import Reunion
from foro.models import Publicacion
from votaciones.models import Votacion
from talleres.models import Taller, Inscripcion
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count, F
from datetime import timedelta
import calendar
from recursos.models import SolicitudReserva

def sin_permiso(request):
    return render(request, "core/sin_permiso.html", status=403)

@login_required
def home(request):
    
    hoy = timezone.now()
    
    # --- 1. Tarjetas Superiores (Resumen) ---
    total_vecinos_registrados = User.objects.count()

    # Reuniones mes
    num_dias_mes = calendar.monthrange(hoy.year, hoy.month)[1]
    fin_mes = hoy.replace(day=num_dias_mes, hour=23, minute=59, second=59)
    
    reuniones_pendientes_mes = Reunion.objects.filter(
        fecha__gte=hoy,       # Desde hoy
        fecha__lte=fin_mes,   # Hasta fin de mes
        estado='PROGRAMADA'   # <--- EL FILTRO QUE FALTABA
    ).count()

    # Publicaciones 24h
    hace_24h = hoy - timedelta(days=1)
    nuevas_publicaciones_24h = Publicacion.objects.filter(fecha_creacion__gte=hace_24h).count()

    # Votaciones
    votaciones_activas = Votacion.objects.filter(activa=True, fecha_cierre__gt=hoy).count()

    # --- LÓGICA CORREGIDA TALLERES ---
    ESTADOS_A_EXCLUIR = ['CANCELADO', 'FINALIZADO', 'REALIZADO', 'SUSPENDIDO']

    talleres_con_cupos_query = Taller.objects.annotate(
        # 1. Usamos 'inscritos_count' (así tu property del modelo también funcionará si la llamas)
        inscritos_count=Count('inscripcion')
    ).annotate(
        # 2. CAMBIO DE NOMBRE: Usamos 'cupos_remanentes' para evitar el conflicto
        cupos_remanentes=F('cupos_totales') - F('inscritos_count')
    ).filter(
        fecha_termino__gte=hoy,
        # 3. Filtramos usando el nuevo nombre
        cupos_remanentes__gt=0
    ).exclude(
        estado__in=ESTADOS_A_EXCLUIR
    ).order_by('fecha_termino')

    talleres_con_cupos_list_completa = list(talleres_con_cupos_query)
    # Solicitudes
    solicitudes_pendientes = SolicitudReserva.objects.filter(estado="PENDIENTE").count()

    # --- 2. Secciones de Actividad ---
    ultimas_publicaciones_foro = Publicacion.objects.order_by('-fecha_creacion')[:3]
    proximas_reuniones = Reunion.objects.filter(
        fecha__gte=hoy, 
        estado='PROGRAMADA'  # <--- EL FILTRO CLAVE
    ).order_by('fecha')[:3]
    votaciones_activas_list = Votacion.objects.filter(activa=True, fecha_cierre__gt=hoy).order_by('fecha_cierre')[:3]

    context = {
        'nombre_usuario': request.user.first_name if request.user.first_name else request.user.username,
        
        'total_vecinos_registrados': total_vecinos_registrados,
        'reuniones_pendientes_mes': reuniones_pendientes_mes,
        'nuevas_publicaciones_24h': nuevas_publicaciones_24h,
        'votaciones_activas': votaciones_activas,
        'talleres_con_cupos': len(talleres_con_cupos_list_completa),
        'solicitudes_pendientes': solicitudes_pendientes,

        'ultimas_publicaciones_foro': ultimas_publicaciones_foro,
        'proximas_reuniones': proximas_reuniones,
        'votaciones_activas_list': votaciones_activas_list,
        # Pasamos la lista que YA TIENE el campo .cupos_disponibles calculado
        'talleres_con_cupos_list': talleres_con_cupos_list_completa[:3],
    }
    
    return render(request, "core/home.html", context)