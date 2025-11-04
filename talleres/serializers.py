from rest_framework import serializers
from .models import Taller

class TallerSerializer(serializers.ModelSerializer):
    inscritos_count = serializers.SerializerMethodField()
    cupos_disponibles = serializers.SerializerMethodField()

    class Meta:
        model = Taller
        fields = ["id", "nombre", "descripcion", "cupos_totales", "inscritos_count", "cupos_disponibles"]

    def get_inscritos_count(self, obj):
        # usa la relación Inscripcion -> Taller
        return obj.inscripcion_set.count()

    def get_cupos_disponibles(self, obj):
        return max(0, obj.cupos_totales - obj.inscripcion_set.count())