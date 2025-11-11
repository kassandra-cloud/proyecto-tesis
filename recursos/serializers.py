# recursos/serializers.py
from rest_framework import serializers
from .models import Recurso,SolicitudReserva

class RecursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recurso
        fields = ["id", "nombre", "descripcion", "disponible"]

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