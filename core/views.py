"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Contiene las vistas principales del sistema (Dashboard),
                       vistas de manejo de errores (403) y la API para la 
                       recuperación de contraseñas desde la App Móvil. 
                       Implementa caché para optimizar la carga del inicio.
--------------------------------------------------------------------------------
"""

# Importa la función para renderizar plantillas HTML.
from django.shortcuts import render
# Importa el decorador para restringir acceso solo a usuarios logueados.
from django.contrib.auth.decorators import login_required
# --- IMPORTACIONES PARA OPTIMIZACIÓN ---
# Importa el decorador de caché para guardar la respuesta de la vista en memoria.
from django.views.decorators.cache import cache_page 
# Importa herramientas para conteo y operaciones con campos de modelos (F expressions).
from django.db.models import Count, F
# ----------------------------------------
# Importa el modelo de Usuario estándar de Django.
from django.contrib.auth.models import User
# Importa utilidades para manejo de zonas horarias.
from django.utils import timezone
# Importa timedelta para calcular diferencias de tiempo (ej. hace 24 horas).
from datetime import timedelta
# Importa el módulo de calendario para cálculos de fechas.
import calendar
# Importa la función para convertir un template HTML a string (para emails).
from django.template.loader import render_to_string
# Importa la función para quitar etiquetas HTML del texto (versión texto plano del email).
from django.utils.html import strip_tags
# Importa la utilidad personalizada para enviar correos (posiblemente asíncrono).
from usuarios.utils import enviar_correo_via_webhook
# --- IMPORTACIONES DE TUS MODELOS ---
# Importa modelos de otras apps para mostrar estadísticas en el dashboard.
from reuniones.models import Reunion
from foro.models import Publicacion
from votaciones.models import Votacion
from talleres.models import Taller, Inscripcion
from recursos.models import SolicitudReserva

# --- IMPORTACIONES PARA LA API DE RECUPERACIÓN (DRF) ---
# Importa la clase base para vistas de API REST.
from rest_framework.views import APIView
# Importa el objeto Response para devolver datos JSON.
from rest_framework.response import Response
# Importa los códigos de estado HTTP (200, 400, 500, etc.).
from rest_framework import status
# Importa el permiso que permite acceso a cualquier usuario (incluso anónimos).
from rest_framework.permissions import AllowAny
# Importa función estándar de envío de correos (aunque se usa webhook abajo).
from django.core.mail import send_mail
# Importa generador de cadenas aleatorias seguras.
from django.utils.crypto import get_random_string

# ---------------------------------------------------------
# VISTAS DE ERROR Y UTILIDAD
# ---------------------------------------------------------
def sin_permiso(request):
    """Renderiza una página de error 403 personalizada cuando falta acceso."""
    return render(request, "core/sin_permiso.html", status=403)

# ---------------------------------------------------------
# API: RECUPERACIÓN DE CONTRASEÑA (APP MÓVIL)
# ---------------------------------------------------------

class RequestRecoveryCodeAPI(APIView):
    """
    API para solicitar un código de recuperación.
    Esta API utiliza un Webhook para el envío de correo, 
    minimizando el bloqueo del hilo de respuesta (offloading).
    """
    # Permite que usuarios no autenticados soliciten código (olvidaron su clave).
    permission_classes = [AllowAny]

    def post(self, request):
        """Maneja la petición POST para generar y enviar el código."""
        # Obtiene el email del cuerpo de la petición JSON.
        email = request.data.get('email')
        # Si no se envía email, retorna error 400.
        if not email:
            return Response({'error': 'El correo es obligatorio'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Busca al usuario por su correo.
            user = User.objects.get(email=email)
            
            # 1. Generar código numérico de 6 dígitos.
            code = get_random_string(length=6, allowed_chars='0123456789')
            
            # 2. Guardar en perfil (si existe el perfil extendido).
            if hasattr(user, 'perfil'):
                user.perfil.recovery_code = code
                # El código expira en 15 minutos.
                user.perfil.recovery_code_expires = timezone.now() + timedelta(minutes=15)
                user.perfil.save()
            else:
                # Si no tiene perfil, simulamos éxito por seguridad (evita enumeración de usuarios).
                return Response({'message': 'Código enviado correctamente'})

            # 3. Preparar Contenido del correo.
            asunto = 'Recuperación de Clave - Villa Vista al Mar'
            
            # Contexto para la plantilla HTML.
            contexto = {
                'codigo': code
            }

            # Renderiza el HTML del correo con el código insertado.
            html_body = render_to_string('registration/email_reset_password_app.html', contexto)
            # Crea una versión de solo texto del correo.
            text_body = strip_tags(html_body)
            
            # 4. ENVIAR POR WEBHOOK (No bloquea el hilo web, mejora performance).
            enviar_correo_via_webhook(
                to_email=email,
                subject=asunto,
                html_body=html_body,
                text_body=text_body
            )
            
            # Retorna éxito.
            return Response({'message': 'Código enviado correctamente'})

        except User.DoesNotExist:
            # Si el usuario no existe, retornamos éxito falso por seguridad.
            return Response({'message': 'Código enviado correctamente'})
            
        except Exception as e:
            # Loguea cualquier otro error y retorna fallo de servidor 500.
            print(f"Error en recuperación: {e}")
            return Response({'error': 'Error procesando solicitud'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ResetPasswordWithCodeAPI(APIView):
    """
    API para establecer la nueva contraseña usando el código recibido.
    1. Recibe { "email": "...", "code": "...", "new_password": "..." }
    2. Valida código y expiración.
    3. Cambia la contraseña.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # Extrae datos del JSON.
        email = request.data.get('email')
        code = request.data.get('code')
        new_password = request.data.get('new_password')

        # Valida que lleguen todos los datos necesarios.
        if not all([email, code, new_password]):
            return Response({'error': 'Faltan datos'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Busca al usuario.
            user = User.objects.get(email=email)
            perfil = user.perfil

            # Validaciones de seguridad.
            # Verifica si el código coincide.
            if perfil.recovery_code != code:
                return Response({'error': 'Código incorrecto'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Verifica si el código ha expirado o no existe fecha de expiración.
            if not perfil.recovery_code_expires or perfil.recovery_code_expires < timezone.now():
                return Response({'error': 'El código ha expirado'}, status=status.HTTP_400_BAD_REQUEST)

            # Cambiar contraseña (encripta y guarda).
            user.set_password(new_password)
            user.save()

            # Limpiar código usado para que no se pueda reutilizar.
            perfil.recovery_code = None
            perfil.recovery_code_expires = None
            perfil.save()

            return Response({'message': 'Contraseña actualizada correctamente'})

        except User.DoesNotExist:
            return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------
# VISTA: HOME / DASHBOARD (WEB)
# ---------------------------------------------------------
# OPTIMIZACIÓN CRÍTICA: La página de inicio (dashboard) ahora se cachea por 60 segundos.
# La primera petición será lenta (consulta BD), pero las siguientes serán rápidas (desde RAM/Redis).
@cache_page(60) 
@login_required
def home(request):
    """
    Vista principal que muestra estadísticas y resúmenes.
    """
    
    hoy = timezone.now()
    
    # --- 1. Tarjetas Superiores (Resumen Estadístico) ---
    # Cuenta total de usuarios.
    total_vecinos_registrados = User.objects.count()

    # Cálculo para obtener el último momento del mes actual.
    num_dias_mes = calendar.monthrange(hoy.year, hoy.month)[1]
    fin_mes = hoy.replace(day=num_dias_mes, hour=23, minute=59, second=59)
    
    # Cuenta reuniones pendientes dentro del mes actual.
    reuniones_pendientes_mes = Reunion.objects.filter(
        fecha__gte=hoy, # Desde hoy
        fecha__lte=fin_mes, # Hasta fin de mes
        estado='PROGRAMADA'
    ).count()

    # Cuenta publicaciones en las últimas 24 horas.
    hace_24h = hoy - timedelta(days=1)
    nuevas_publicaciones_24h = Publicacion.objects.filter(fecha_creacion__gte=hace_24h).count()

    # Cuenta votaciones que están activas y no han cerrado.
    votaciones_activas = Votacion.objects.filter(activa=True, fecha_cierre__gt=hoy).count()

    # --- LÓGICA TALLERES (Cupos Disponibles) ---
    # Define estados que no se deben mostrar.
    ESTADOS_A_EXCLUIR = ['CANCELADO', 'FINALIZADO', 'REALIZADO', 'SUSPENDIDO']

    # Consulta compleja optimizada con Annotate para calcular cupos en BD.
    talleres_con_cupos_query = Taller.objects.annotate(
        inscritos_count=Count('inscripcion') # Cuenta inscritos por taller.
    ).annotate(
        cupos_remanentes=F('cupos_totales') - F('inscritos_count') # Calcula disponibles.
    ).filter(
        fecha_termino__gte=hoy, # Taller no terminado.
        cupos_remanentes__gt=0 # Quedan cupos.
    ).exclude(
        estado__in=ESTADOS_A_EXCLUIR # Excluye cancelados/finalizados.
    ).order_by('fecha_termino')

    # Evalúa la QuerySet a lista.
    talleres_con_cupos_list_completa = list(talleres_con_cupos_query)
    
    # Cuenta solicitudes de recursos pendientes.
    solicitudes_pendientes = SolicitudReserva.objects.filter(estado="PENDIENTE").count()

    # --- 2. Secciones de Actividad (Listas cortas para el dashboard) ---
    # OPTIMIZACIÓN: select_related('autor') pre-carga los datos del autor (JOIN).
    # Obtiene las 3 últimas publicaciones.
    ultimas_publicaciones_foro = Publicacion.objects.select_related('autor').order_by('-fecha_creacion')[:3]
    
    # Obtiene las próximas 3 reuniones programadas.
    proximas_reuniones = Reunion.objects.filter(
        fecha__gte=hoy, 
        estado='PROGRAMADA'
    ).order_by('fecha')[:3]
    
    # Obtiene las próximas 3 votaciones activas.
    votaciones_activas_list = Votacion.objects.filter(activa=True, fecha_cierre__gt=hoy).order_by('fecha_cierre')[:3]

    # Prepara el contexto para enviar a la plantilla HTML.
    context = {
        # Nombre para saludar.
        'nombre_usuario': request.user.first_name if request.user.first_name else request.user.username,
        
        # Datos para tarjetas.
        'total_vecinos_registrados': total_vecinos_registrados,
        'reuniones_pendientes_mes': reuniones_pendientes_mes,
        'nuevas_publicaciones_24h': nuevas_publicaciones_24h,
        'votaciones_activas': votaciones_activas,
        'talleres_con_cupos': len(talleres_con_cupos_list_completa),
        'solicitudes_pendientes': solicitudes_pendientes,

        # Datos para listas.
        'ultimas_publicaciones_foro': ultimas_publicaciones_foro,
        'proximas_reuniones': proximas_reuniones,
        'votaciones_activas_list': votaciones_activas_list,
        'talleres_con_cupos_list': talleres_con_cupos_list_completa[:3], # Solo los primeros 3 talleres.
    }
    
    # Renderiza la vista.
    return render(request, "core/home.html", context)