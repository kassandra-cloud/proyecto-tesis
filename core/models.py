from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model
from .rut import normalizar_rut, validar_rut
from django.utils import timezone  
import datetime                    
import random                      

User = get_user_model()

class Perfil(models.Model):
    class Roles(models.TextChoices):
        PRESIDENTE = "presidente", "PRESIDENTE"
        SECRETARIA = "secretaria", "SECRETARIA"
        TESORERO   = "tesorero",  "TESORERO"
        SUPLENTE   = "suplente",  "SUPLENTE"
        VECINO     = "vecino",    "VECINO"
       
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    rol     = models.CharField(max_length=20, choices=Roles.choices)
    rut     = models.CharField(max_length=12, unique=True, null=False, blank=False, help_text="12345678-9")

    apellido_paterno = models.CharField(max_length=100, blank=True)
    apellido_materno = models.CharField(max_length=100, blank=True)

    # --- CAMPOS DEMOGRÁFICOS ---
    direccion = models.CharField(
        max_length=255, 
        verbose_name="Dirección Completa",
        blank=False,
        default=""
    )
    telefono = models.CharField(max_length=15, blank=True, null=True, verbose_name="Teléfono")
    total_residentes = models.PositiveIntegerField(
        verbose_name="Total de Residentes",
        default=1
    )
    
    total_ninos = models.PositiveIntegerField(
        verbose_name="Número de Niños (< 18 años)",
        default=0
    )

    # Token FCM
    fcm_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name='Token FCM'
    )

    # =========================================================================
    #  NUEVOS CAMPOS MFA (Esto es lo que faltaba)
    # =========================================================================
    mfa_code = models.CharField(max_length=6, blank=True, null=True)
    mfa_expires = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.rut or not self.rut.strip():
            from django.core.exceptions import ValidationError
            raise ValidationError("El RUT no puede estar vacío.")
        self.rut = normalizar_rut(self.rut)
        validar_rut(self.rut)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario.username} - {self.get_rol_display()} - {self.rut}"

    # =========================================================================
    # 🔥 MÉTODOS MFA (Esto faltaba y causaba el error)
    # =========================================================================
    def generar_mfa(self):
        """Genera un código de 6 dígitos y le da 5 minutos de vida."""
        code = f"{random.randint(100000, 999999)}"
        self.mfa_code = code
        self.mfa_expires = timezone.now() + datetime.timedelta(minutes=5)
        self.save()
        return code

    def validar_mfa(self, code):
        """Valida si el código es correcto y no ha expirado."""
        if not self.mfa_code or not self.mfa_expires:
            return False
        if timezone.now() > self.mfa_expires:
            return False
        return self.mfa_code == code

    class Meta:
        constraints = [models.CheckConstraint(name="rut_not_empty", check=~Q(rut=""))]