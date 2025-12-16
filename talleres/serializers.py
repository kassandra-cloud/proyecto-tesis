from rest_framework import serializers
from .models import Taller, Inscripcion


class TallerSerializer(serializers.ModelSerializer):
    inscritos_count = serializers.SerializerMethodField()
    cupos_disponibles = serializers.SerializerMethodField()
    esta_inscrito = serializers.SerializerMethodField()

    class Meta:
        model = Taller
        fields = [
            "id",
            "nombre",
            "descripcion",
            "cupos_totales",
            "fecha_inicio",
            "fecha_termino",
            "inscritos_count",
            "cupos_disponibles",
            "esta_inscrito",
        ]

    def get_inscritos_count(self, obj):
        return Inscripcion.objects.filter(taller=obj).count()

    def get_cupos_disponibles(self, obj):
        inscritos = Inscripcion.objects.filter(taller=obj).count()
        return max(0, obj.cupos_totales - inscritos)

    def get_esta_inscrito(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return Inscripcion.objects.filter(vecino=request.user, taller=obj).exists()
        return False
