# recursos/serializers.py
from rest_framework import serializers
from .models import Recurso,SolicitudReserva
from django.utils import timezone
class RecursoSerializer(serializers.ModelSerializer):
    # 💡 CAMBIO CRÍTICO: Sobreescribir 'disponible' para calcular si está siendo usado
    disponible = serializers.SerializerMethodField() 
    
    class Meta:
        model = Recurso
        # Asegúrate de que 'disponible' esté en fields para que se incluya en el JSON
        fields = ["id", "nombre", "descripcion", "disponible"] 

    def get_disponible(self, obj: Recurso) -> bool:
        """
        Calcula si el recurso está actualmente disponible.
        Un recurso NO está disponible si:
        1. Su campo 'disponible' (de administración) es False.
        2. Tiene una reserva APROBADA o PENDIENTE activa en este momento.
        """
        # Si la administración lo marca como no disponible, es no disponible
        if not obj.disponible:
            return False

        now = timezone.now().date() # Usamos .date() porque SolicitudReserva usa DateField

        # Busca una solicitud APROBADA (o PENDIENTE, si quieres bloquearlas temporalmente)
        # que esté activa en la fecha de hoy.
        reserva_activa = SolicitudReserva.objects.filter(
            recurso=obj,
            estado__in=["APROBADA"], # Solo las aprobadas deberían bloquear la disponibilidad
        ).filter(
            fecha_inicio__lte=now,
            fecha_fin__gte=now
        ).exists()

        # Si hay una reserva activa APROBADA, el recurso no está disponible.
        return not reserva_activa
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
        return data