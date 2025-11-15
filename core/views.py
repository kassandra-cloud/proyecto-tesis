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

def home(request):
    return render(request, "core/home.html", {"titulo": "Proyecto de Tesis funcionando"})

# Create your views here.
def sin_permiso(request):
    return render(request, "core/sin_permiso.html", status=403)


@login_required  # <-- ¡Importante! Aseguramos que solo usuarios logueados vean el dashboard
def home(request):
    
    hoy = timezone.now()
    
    # --- 1. Tarjetas Superiores (Resumen) ---
    
    # Tarjeta 1: Total Vecinos (del modelo User)
    total_vecinos_registrados = User.objects.count()

    # Tarjeta 2: Reuniones Pendientes (usa 'fecha' de Reunion)
    # Obtenemos el último día del mes actual
    num_dias_mes = calendar.monthrange(hoy.year, hoy.month)[1]
    fin_mes = hoy.replace(day=num_dias_mes, hour=23, minute=59, second=59)
    reuniones_pendientes_mes = Reunion.objects.filter(
        fecha__gte=hoy,  # Reuniones desde hoy
        fecha__lte=fin_mes # hasta fin de mes
    ).count()

    # Tarjeta 3: Nuevas Publicaciones (Adaptado) (usa 'fecha_creacion' de Publicacion)
    hace_24h = hoy - timedelta(days=1)
    nuevas_publicaciones_24h = Publicacion.objects.filter(
        fecha_creacion__gte=hace_24h
    ).count()

    # Tarjeta 4: Votaciones Activas (usa 'activa' y 'fecha_cierre' de Votacion)
    votaciones_activas = Votacion.objects.filter(
        activa=True, 
        fecha_cierre__gt=hoy # y que la fecha de cierre sea mayor a hoy
    ).count()

    # Tarjeta 5: Talleres con Cupos (Adaptado) (usa Taller e Inscripcion)
    talleres_con_cupos = Taller.objects.annotate(
        num_inscritos=Count('inscripcion') # Contamos las inscripciones
    ).filter(
        cupos_totales__gt=F('num_inscritos') # Filtramos donde cupos > inscritos
    ).count()

    # Tarjeta 6: Solicitudes de Recursos Pendientes (NUEVA)
    solicitudes_pendientes = SolicitudReserva.objects.filter(
        estado="PENDIENTE"
    ).count()

    # --- 2. Secciones de Actividad ---
    
    # Actividad en el Foro (3 publicaciones más recientes)
    ultimas_publicaciones_foro = Publicacion.objects.order_by('-fecha_creacion')[:3]

    # Próximas Reuniones (3 próximas reuniones)
    proximas_reuniones = Reunion.objects.filter(fecha__gte=hoy).order_by('fecha')[:3]

    # Votaciones Activas (Lista de 3)
    votaciones_activas_list = Votacion.objects.filter(
        activa=True, 
        fecha_cierre__gt=hoy
    ).order_by('fecha_cierre')[:3]

    # Talleres con Cupos (Lista de 3)
    talleres_con_cupos_list = Taller.objects.annotate(
        num_inscritos=Count('inscripcion')
    ).filter(
        cupos_totales__gt=F('num_inscritos')
    ).order_by('nombre')[:3]
    
    
    context = {
        'nombre_usuario': request.user.first_name if request.user.first_name else request.user.username,
        
        # Datos para las tarjetas
        'total_vecinos_registrados': total_vecinos_registrados,
        'reuniones_pendientes_mes': reuniones_pendientes_mes,
        'nuevas_publicaciones_24h': nuevas_publicaciones_24h,
        'votaciones_activas': votaciones_activas,
        'talleres_con_cupos': talleres_con_cupos,
        

        # Datos para las secciones
        'ultimas_publicaciones_foro': ultimas_publicaciones_foro,
        'proximas_reuniones': proximas_reuniones,
        'votaciones_activas_list': votaciones_activas_list,
        'talleres_con_cupos_list': talleres_con_cupos_list,
        'solicitudes_pendientes': solicitudes_pendientes,
    }
    
    # Renderizamos tu plantilla original 'core/home.html' con el nuevo contexto
    return render(request, "core/home.html", context)


# Tu vista sin_permiso original (la mantenemos)
def sin_permiso(request):
    return render(request, "core/sin_permiso.html", status=403)