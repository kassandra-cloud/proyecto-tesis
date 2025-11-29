from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count, F
from datetime import timedelta
import calendar

# --- IMPORTACIONES DE TUS MODELOS ---
from reuniones.models import Reunion
from foro.models import Publicacion
from votaciones.models import Votacion
from talleres.models import Taller, Inscripcion
from recursos.models import SolicitudReserva

# --- IMPORTACIONES PARA LA API DE RECUPERACIÓN (DRF) ---
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.core.mail import send_mail
from django.utils.crypto import get_random_string

# ---------------------------------------------------------
# VISTAS DE ERROR Y UTILIDAD
# ---------------------------------------------------------
def sin_permiso(request):
    return render(request, "core/sin_permiso.html", status=403)

# ---------------------------------------------------------
# API: RECUPERACIÓN DE CONTRASEÑA (APP MÓVIL)
# ---------------------------------------------------------

class RequestRecoveryCodeAPI(APIView):
    """
    1. Recibe { "email": "..." }
    2. Genera un código de 6 dígitos.
    3. Lo guarda en el perfil del usuario.
    4. Envía el correo real.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'El correo es obligatorio'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            
            # 1. Generar código
            code = get_random_string(length=6, allowed_chars='0123456789')
            
            # 2. Guardar en perfil 
            # (Asegúrate de que el modelo Perfil tenga los campos 'recovery_code' y 'recovery_code_expires')
            user.perfil.recovery_code = code
            user.perfil.recovery_code_expires = timezone.now() + timedelta(minutes=15)
            user.perfil.save()

            # 3. Enviar Correo
            asunto = 'Código de Recuperación - Villa Vista al Mar'
            mensaje = f"""
            Hola {user.first_name},

            Has solicitado restablecer tu contraseña.
            Tu código de verificación es:

            {code}

            Este código expira en 15 minutos.
            Si no fuiste tú, ignora este mensaje.
            """
            
            send_mail(
                asunto,
                mensaje,
                None, # Usa el correo configurado en settings.py
                [email],
                fail_silently=False,
            )
            
            return Response({'message': 'Código enviado correctamente'})

        except User.DoesNotExist:
            # Por seguridad, respondemos éxito aunque el correo no exista
            return Response({'message': 'Código enviado correctamente'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResetPasswordWithCodeAPI(APIView):
    """
    1. Recibe { "email": "...", "code": "...", "new_password": "..." }
    2. Valida código y expiración.
    3. Cambia la contraseña.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')
        new_password = request.data.get('new_password')

        if not all([email, code, new_password]):
            return Response({'error': 'Faltan datos'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            perfil = user.perfil

            # Validaciones
            if perfil.recovery_code != code:
                return Response({'error': 'Código incorrecto'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not perfil.recovery_code_expires or perfil.recovery_code_expires < timezone.now():
                return Response({'error': 'El código ha expirado'}, status=status.HTTP_400_BAD_REQUEST)

            # Cambiar contraseña
            user.set_password(new_password)
            user.save()

            # Limpiar código usado
            perfil.recovery_code = None
            perfil.recovery_code_expires = None
            perfil.save()

            return Response({'message': 'Contraseña actualizada correctamente'})

        except User.DoesNotExist:
            return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------
# VISTA: HOME / DASHBOARD (WEB)
# ---------------------------------------------------------
@login_required
def home(request):
    
    hoy = timezone.now()
    
    # --- 1. Tarjetas Superiores (Resumen) ---
    total_vecinos_registrados = User.objects.count()

    # Reuniones mes
    num_dias_mes = calendar.monthrange(hoy.year, hoy.month)[1]
    fin_mes = hoy.replace(day=num_dias_mes, hour=23, minute=59, second=59)
    
    reuniones_pendientes_mes = Reunion.objects.filter(
        fecha__gte=hoy,      # Desde hoy
        fecha__lte=fin_mes,  # Hasta fin de mes
        estado='PROGRAMADA'
    ).count()

    # Publicaciones 24h
    hace_24h = hoy - timedelta(days=1)
    nuevas_publicaciones_24h = Publicacion.objects.filter(fecha_creacion__gte=hace_24h).count()

    # Votaciones activas
    votaciones_activas = Votacion.objects.filter(activa=True, fecha_cierre__gt=hoy).count()

    # --- LÓGICA TALLERES (Cupos Disponibles) ---
    ESTADOS_A_EXCLUIR = ['CANCELADO', 'FINALIZADO', 'REALIZADO', 'SUSPENDIDO']

    talleres_con_cupos_query = Taller.objects.annotate(
        inscritos_count=Count('inscripcion')
    ).annotate(
        cupos_remanentes=F('cupos_totales') - F('inscritos_count')
    ).filter(
        fecha_termino__gte=hoy,
        cupos_remanentes__gt=0
    ).exclude(
        estado__in=ESTADOS_A_EXCLUIR
    ).order_by('fecha_termino')

    talleres_con_cupos_list_completa = list(talleres_con_cupos_query)
    
    # Solicitudes pendientes
    solicitudes_pendientes = SolicitudReserva.objects.filter(estado="PENDIENTE").count()

    # --- 2. Secciones de Actividad ---
    ultimas_publicaciones_foro = Publicacion.objects.order_by('-fecha_creacion')[:3]
    
    proximas_reuniones = Reunion.objects.filter(
        fecha__gte=hoy, 
        estado='PROGRAMADA'
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
        'talleres_con_cupos_list': talleres_con_cupos_list_completa[:3],
    }
    
    return render(request, "core/home.html", context)