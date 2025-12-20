"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Este archivo define los modelos fundamentales de la 
                       aplicación. Contiene el modelo 'Perfil' que extiende al 
                       usuario nativo de Django con datos vecinales y roles, y 
                       el modelo 'DispositivoFCM' para la gestión de tokens de 
                       notificaciones push. También incluye validaciones de RUT 
                       y lógica de autenticación de dos factores (MFA).
--------------------------------------------------------------------------------
"""

# Importa el módulo base de modelos de Django para interactuar con la base de datos.
from django.db import models
# Importa Q para construir consultas complejas (como filtros OR o negaciones).
from django.db.models import Q
# Importa la función para obtener el modelo de Usuario activo en el proyecto (User).
from django.contrib.auth import get_user_model
# Importa funciones utilitarias para el manejo de RUT chileno desde un archivo local.
from .rut import normalizar_rut, validar_rut
# Importa la utilidad timezone para manejar fechas con zona horaria correcta.
from django.utils import timezone  
# Importa el módulo nativo datetime para operaciones de tiempo.
import datetime                    
# Importa random para generar códigos numéricos aleatorios (usado en MFA).
import random                      

# Asigna el modelo de usuario actual a la variable 'User' para usarlo en relaciones.
User = get_user_model()

class Perfil(models.Model):
    """
    Modelo que extiende la información del usuario estándar de Django.
    Almacena datos específicos del vecino y su rol en la junta.
    """
    
    # Define una clase interna para enumerar las opciones de roles disponibles (Enum).
    class Roles(models.TextChoices):
        PRESIDENTE = "presidente", "PRESIDENTE" # Valor en BD, Etiqueta legible
        SECRETARIA = "secretaria", "SECRETARIA"
        TESORERO   = "tesorero",  "TESORERO"
        SUPLENTE   = "suplente",  "SUPLENTE"
        VECINO     = "vecino",    "VECINO"
       
    # Relación 1 a 1 con el usuario de Django. Si se borra el User, se borra el Perfil.
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    
    # Campo de texto para el rol, restringido a las opciones definidas en la clase Roles.
    rol     = models.CharField(max_length=20, choices=Roles.choices)
    
    # Campo para el RUT. Debe ser único en todo el sistema y no puede ser nulo.
    rut     = models.CharField(max_length=12, unique=True, null=False, blank=False, help_text="12345678-9")

    # Campos opcionales para apellidos adicionales.
    apellido_paterno = models.CharField(max_length=100, blank=True)
    apellido_materno = models.CharField(max_length=100, blank=True)
    
    # Campo para guardar un código temporal de recuperación de contraseña.
    recovery_code = models.CharField(max_length=6, blank=True, null=True)
    # Fecha de expiración para el código de recuperación.
    recovery_code_expires = models.DateTimeField(blank=True, null=True)
    
    # --- CAMPOS DEMOGRÁFICOS ---
    
    # Campo para el nombre de la calle. Es obligatorio (blank=False).
    direccion = models.CharField(
        max_length=255, 
        verbose_name="Nombre de la Calle/Pasaje", # Nombre visible en formularios
        blank=False,
        default=""
    )
    
    # Nuevo campo específico para el número de casa o departamento.
    numero_casa = models.CharField( 
        max_length=20,
        blank=True,
        default="",
        verbose_name="N° Casa/Depto/Lote"
    )
    
    # Campo opcional para contacto telefónico.
    telefono = models.CharField(max_length=15, blank=True, null=True, verbose_name="Teléfono")
    
    # Número total de personas que viven en el domicilio (para estadísticas).
    total_residentes = models.PositiveIntegerField(
        verbose_name="Total de Residentes",
        default=1
    )
    
    # Número de menores de edad en el domicilio.
    total_ninos = models.PositiveIntegerField(
        verbose_name="Número de Niños (< 18 años)",
        default=0
    )

    # Token para Firebase Cloud Messaging (Notificaciones Push).
    fcm_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name='Token FCM'
    )
    
    # Bandera para obligar al usuario a cambiar su clave (ej. en el primer login).
    debe_cambiar_password = models.BooleanField(default=False, verbose_name="Debe cambiar contraseña")
    
    # =========================================================================
    #  NUEVOS CAMPOS MFA (Autenticación Multifactor)
    # =========================================================================
    # Código temporal de 6 dígitos para validación de dos pasos.
    mfa_code = models.CharField(max_length=6, blank=True, null=True)
    # Fecha y hora de expiración del código MFA.
    mfa_expires = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        """Método que se ejecuta antes de guardar el registro en la BD."""
        # Valida que el RUT no venga vacío.
        if not self.rut or not self.rut.strip():
            # Importación local para evitar ciclos.
            from django.core.exceptions import ValidationError
            raise ValidationError("El RUT no puede estar vacío.")
        
        # Normaliza el RUT (formato estandarizado) antes de guardar.
        self.rut = normalizar_rut(self.rut)
        # Verifica que el RUT sea matemáticamente válido.
        validar_rut(self.rut)
        # Llama al método save original.
        super().save(*args, **kwargs)

    def __str__(self):
        """Representación en texto del perfil (para el admin o consola)."""
        return f"{self.usuario.username} - {self.get_rol_display()} - {self.rut}"

    # =========================================================================
    # MÉTODOS MFA 
    # =========================================================================
    def generar_mfa(self):
        """Crea un código numérico aleatorio y define su validez por 5 minutos."""
        # Genera número entre 100000 y 999999.
        code = f"{random.randint(100000, 999999)}"
        self.mfa_code = code
        # Calcula la expiración (Ahora + 5 min).
        self.mfa_expires = timezone.now() + datetime.timedelta(minutes=5)
        # Guarda solo los campos modificados para optimizar.
        self.save()
        return code

    def validar_mfa(self, code):
        """Verifica si el código ingresado es correcto y está vigente."""
        # Si no hay código generado, falla.
        if not self.mfa_code or not self.mfa_expires:
            return False
        # Si ya pasó la fecha de expiración, falla.
        if timezone.now() > self.mfa_expires:
            return False
        # Retorna True si los códigos coinciden.
        return self.mfa_code == code

    class Meta:
        # Restricción a nivel de base de datos para asegurar que el RUT no sea cadena vacía.
        constraints = [models.CheckConstraint(name="rut_not_empty", check=~Q(rut=""))]

class DispositivoFCM(models.Model):
    """
    Modelo para registrar dispositivos (celulares/tablets) asociados a un usuario.
    Permite enviar notificaciones a múltiples dispositivos de una misma persona.
    """
    # Relación muchos a uno: Un usuario puede tener múltiples dispositivos.
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="dispositivos_fcm"
    )
    # Token único generado por Firebase para el dispositivo.
    token = models.CharField(max_length=255, unique=True)
    
    # Nombre opcional para identificar el equipo (ej. "Celular de Juan").
    nombre_dispositivo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Nombre amigable (por ejemplo: 'Xiaomi de María', 'Emulador Android Studio')",
    )
    # Sistema operativo del dispositivo (Android, iOS, Web).
    plataforma = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="android, web, ios, etc."
    )
    # Fechas de auditoría automáticas.
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Muestra el usuario y una parte del token."""
        base = f"{self.usuario.username} - {self.token[:10]}..."
        if self.nombre_dispositivo:
            return f"{base} ({self.nombre_dispositivo})"
        return base