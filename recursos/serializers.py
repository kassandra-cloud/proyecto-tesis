"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Serializadores para convertir modelos Recurso y SolicitudReserva 
               a JSON. Incluye lógica dinámica para determinar disponibilidad y 
               estado de solicitudes del usuario actual.
--------------------------------------------------------------------------------
"""
from rest_framework import serializers
from .models import Recurso, SolicitudReserva
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

class RecursoSerializer(serializers.ModelSerializer):
    # Campos calculados dinámicamente
    disponible = serializers.SerializerMethodField() 
    solicitud_activa_usuario = serializers.SerializerMethodField()
    estado_ultima_solicitud = serializers.SerializerMethodField()
    
    class Meta:
        model = Recurso
        fields = ["id", "nombre", "descripcion", "disponible", "solicitud_activa_usuario","estado_ultima_solicitud"] 

    def get_disponible(self, obj: Recurso) -> bool:
        """
        Calcula si el recurso está disponible HOY.
        Si está deshabilitado globalmente o tiene reserva aprobada hoy -> False.
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
        Indica si el usuario que consulta tiene una solicitud PENDIENTE o APROBADA
        para este recurso. Útil para la UI de la app (mostrar botón "Reservar" o no).
        """
        request = self.context.get('request')
        
        if request and request.user.is_authenticated:
            user: User = request.user
            return SolicitudReserva.objects.filter(
                recurso=obj,
                solicitante=user, 
                estado__in=["PENDIENTE", "APROBADA"] 
            ).exists()
        return False

    def get_estado_ultima_solicitud(self, obj: Recurso) -> str | None:
        """
        Devuelve el estado textual de la última solicitud realizada por el usuario.
        """
        request = self.context.get('request')
        
        if request and request.user.is_authenticated:
            user = request.user
            ultima_solicitud = SolicitudReserva.objects.filter(
                recurso=obj,
                solicitante=user
            ).order_by('-creado_el').first()
            return ultima_solicitud.estado if ultima_solicitud else None
        return None 

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
    """Serializer específico para crear solicitudes (validaciones extra)"""
    class Meta:
        model = SolicitudReserva
        fields = ["recurso", "fecha_inicio", "fecha_fin", "motivo"]

    def validate(self, data):
        # Validación básica de fechas
        if data["fecha_fin"] < data["fecha_inicio"]:
            raise serializers.ValidationError("La fecha de fin no puede ser menor a la de inicio.")
        
        # Validación: Usuario no debe tener otra solicitud activa para el mismo recurso
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if SolicitudReserva.objects.filter(
                solicitante=request.user,
                recurso=data["recurso"],
                estado__in=["PENDIENTE", "APROBADA"]
            ).exists():
                raise serializers.ValidationError("Ya tienes una solicitud pendiente o aprobada para este recurso.")
        
        return data