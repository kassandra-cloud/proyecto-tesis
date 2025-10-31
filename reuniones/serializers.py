# reuniones/serializers.py
from rest_framework import serializers
from .models import Reunion, Acta
from .models import Asistencia 
class ReunionSerializer(serializers.ModelSerializer):
    asistentes_count = serializers.IntegerField(source='asistentes.count', read_only=True)

    class Meta:
        model = Reunion
        fields = [
            "id", "fecha", "tipo", "titulo", "tabla", "creada_el", "asistentes_count"
        ]

class ActaSerializer(serializers.ModelSerializer):
    # Acta usa OneToOne(primary_key=True) con Reunion → el ID del acta == ID de la reunión
    reunion = serializers.PrimaryKeyRelatedField(read_only=True)
    reunion_titulo = serializers.CharField(source="reunion.titulo", read_only=True)
    reunion_fecha = serializers.DateTimeField(source="reunion.fecha", read_only=True)
    reunion_tipo = serializers.CharField(source="reunion.tipo", read_only=True)

    class Meta:
        model = Acta
        fields = [
            "reunion", "contenido", "aprobada",
            "reunion_titulo", "reunion_fecha", "reunion_tipo",
        ]
class AsistenciaSerializer(serializers.ModelSerializer):

    nombre_usuario  = serializers.CharField(source="vecino.nombre_usuario", read_only=True, default=None)
    rut             = serializers.CharField(source="vecino.rut", read_only=True, default=None)
    nombre_completo = serializers.SerializerMethodField()

    def get_nombre_completo(self, obj):
        v = getattr(obj, "vecino", None)
        if not v:
            return None
 
        if hasattr(v, "get_full_name"):
            full = v.get_full_name()
            if full:
                return full
        partes = []
        for a in ("first_name", "nombres", "nombre"):
            val = getattr(v, a, "") or ""
            if val: partes.append(val)
        for a in ("last_name", "apellidos", "apellido"):
            val = getattr(v, a, "") or ""
            if val: partes.append(val)
        full = " ".join(partes).strip()
        return full or None

    class Meta:
        model  = Asistencia
        fields = ["id", "reunion", "nombre_usuario", "nombre_completo", "rut", "presente"]