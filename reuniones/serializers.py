# reuniones/serializers.py
from rest_framework import serializers
from .models import Reunion, Acta
from .models import Asistencia 
from django.utils import timezone
from datetime import timedelta
class ReunionSerializer(serializers.ModelSerializer):
    # 💡 CORRECCIÓN 1: El modelo usa 'creada_por', el DTO espera 'autor' (Int ID)
    autor = serializers.IntegerField(source="creada_por.id", read_only=True)
    
    # 💡 CORRECCIÓN 2: El modelo usa 'fecha', el DTO espera 'fecha_inicio' (DateTime)
    fecha_inicio = serializers.DateTimeField(source="fecha", format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    # 💡 CORRECCIÓN 3 (Soluciona el error 500): El modelo usa 'tipo', el DTO espera 'tipo_reunion'
    # Mapeamos el campo 'tipo' del modelo al nombre 'tipo_reunion' en el JSON
    tipo_reunion = serializers.CharField(source="tipo", read_only=True) 

    # Asistentes count: Asumimos que la ViewSet anota este campo, pero lo definimos aquí.
    asistentes_count = serializers.IntegerField(source='asistentes.count', read_only=True)

    class Meta:
        model = Reunion
        fields = [
            "id", 
            "titulo", 
            "tabla", 
            "estado", # Ya fue corregido en la DB por la migración
            "creada_el",
            # Mapeados
            "autor",
            "fecha_inicio",
            "tipo_reunion",
            "asistentes_count"
        ]
class ActaSerializer(serializers.ModelSerializer):
    # Acta usa OneToOne(primary_key=True) con Reunion
    reunion = serializers.PrimaryKeyRelatedField(read_only=True)
    reunion_titulo = serializers.CharField(source="reunion.titulo", read_only=True)
    reunion_fecha = serializers.DateTimeField(source="reunion.fecha", read_only=True)
    reunion_tipo = serializers.CharField(source="reunion.tipo", read_only=True)
    
    # 💡 CORRECCIÓN 4: Añadimos el autor del acta como string para el DTO
    autor_username = serializers.CharField(source="autor.username", read_only=True)

    class Meta:
        model = Acta
        fields = [
            "reunion", "contenido", "aprobada",
            "reunion_titulo", "reunion_fecha", "reunion_tipo",
            "autor_username"
        ]
class AsistenciaSerializer(serializers.ModelSerializer):
    
    nombre_usuario  = serializers.CharField(source="vecino.nombre_usuario", read_only=True, default=None)
    rut             = serializers.CharField(source="vecino.rut", read_only=True, default=None)
    nombre_completo = serializers.SerializerMethodField()

    def get_nombre_completo(self, obj):
        v = getattr(obj, "vecino", None)
        if not v: return None
        if hasattr(v, "get_full_name"):
            full = v.get_full_name()
            if full: return full
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