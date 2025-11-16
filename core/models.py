# core/models.py
from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model
from .rut import normalizar_rut, validar_rut

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

    # --- INICIO DE CAMPOS DEMOGRÁFICOS ---
    direccion = models.CharField(
        max_length=255, 
        verbose_name="Dirección Completa",
        blank=False, # Obligatorio en formularios
        default=""   # Valor para registros existentes
    )
    
    total_residentes = models.PositiveIntegerField(
        verbose_name="Total de Residentes",
        default=1 # Asumimos al menos 1 (el propio vecino)
    )
    
    total_ninos = models.PositiveIntegerField(
        verbose_name="Número de Niños (< 18 años)",
        default=0 # Por defecto 0
    )
    # --- FIN DE CAMPOS DEMOGRÁFICOS ---
    # Nuevo campo para almacenar el Token de Firebase Cloud Messaging
    fcm_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name='Token FCM'
    )

    def save(self, *args, **kwargs):
        # ... (función save sin cambios) ...
        if not self.rut or not self.rut.strip():
            from django.core.exceptions import ValidationError
            raise ValidationError("El RUT no puede estar vacío.")
        self.rut = normalizar_rut(self.rut)
        validar_rut(self.rut)
        super().save(*args, **kwargs)

    def __str__(self):
        # ... (función __str__ sin cambios) ...
        return f"{self.usuario.username} - {self.get_rol_display()} - {self.rut}"

    class Meta:
        # ... (Meta sin cambios) ...
        constraints = [models.CheckConstraint(name="rut_not_empty", check=~Q(rut=""))]