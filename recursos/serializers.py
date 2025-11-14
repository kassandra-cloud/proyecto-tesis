# recursos/serializers.py
from rest_framework import serializers
from .models import Recurso,SolicitudReserva
from django.utils import timezone
from django.contrib.auth import get_user_model


User = get_user_model()
class RecursoSerializer(serializers.ModelSerializer):
    disponible = serializers.SerializerMethodField() 
    solicitud_activa_usuario = serializers.SerializerMethodField()

    class Meta:
        model = Recurso
        fields = ["id", "nombre", "descripcion", "disponible", "solicitud_activa_usuario"] 

    def get_disponible(self, obj: Recurso) -> bool:
        """
        Calcula si el recurso está actualmente disponible globalmente.
        """
        if not obj.disponible:
            return False

        now = timezone.now().date() 

        reserva_activa = SolicitudReserva.objects.filter(
            recurso=obj,
            estado__in=["APROBADA"], 
        ).filter(
            fecha_inicio__lte=now,
            fecha_fin__gte=now
        ).exists()

        return not reserva_activa

    def get_solicitud_activa_usuario(self, obj: Recurso) -> bool:
        """
        Indica si el usuario autenticado tiene una solicitud PENDIENTE o APROBADA.
        """
        request = self.context.get('request')
        
        if request and request.user.is_authenticated:
            user: User = request.user
            
            # 🛑 CORRECCIÓN CLAVE: Cambiar 'usuario' por 'solicitante'
            return SolicitudReserva.objects.filter(
                recurso=obj,
                solicitante=user, # ✅ AHORA USA EL CAMPO CORRECTO
                estado__in=["PENDIENTE", "APROBADA"] 
            ).exists()
            
        return False
class SolicitudReservaSerializer(serializers.ModelSerializer):
    recurso_nombre = serializers.CharField(source="recurso.nombre", read_only=True)

    class Meta:
        model = SolicitudReserva
        fields = [
            "id", "recurso", "recurso_nombre",
            "fecha_inicio", "fecha_fin", "motivo",
            "estado", "creado_el"
        ]
        read_only_fields = ["estado", "creado_el", "recurso_nombre"]
class CrearSolicitudSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolicitudReserva
        fields = ["recurso", "fecha_inicio", "fecha_fin", "motivo"]

    def validate(self, data):
        if data["fecha_fin"] < data["fecha_inicio"]:
            raise serializers.ValidationError("La fecha de fin no puede ser menor a la de inicio.")
        
        # Validación adicional para evitar doble solicitud
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # 🛑 CORRECCIÓN CLAVE: Cambiar 'usuario' por 'solicitante'
            if SolicitudReserva.objects.filter(
                solicitante=request.user, # ✅ AHORA USA EL CAMPO CORRECTO
                recurso=data["recurso"],
                estado__in=["PENDIENTE", "APROBADA"]
            ).exists():
                raise serializers.ValidationError("Ya tienes una solicitud pendiente o aprobada para este recurso.")
        
        return data