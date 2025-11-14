from rest_framework import serializers
from .models import Reunion, Acta, Asistencia 
from django.utils import timezone
from datetime import timedelta

class ReunionSerializer(serializers.ModelSerializer):
    """
    Serializer para la API de Reuniones.
    """
    # 1. Mapea creada_por (FK) a autor (ID)
    autor = serializers.IntegerField(source="creada_por.id", read_only=True)
    
    # 2. Mapea Reunion.fecha a 'fecha_inicio'. ELIMINAMOS EL ARGUMENTO 'format'.
    # Django ahora usará el formato ISO 8601 estándar con zona horaria.
    fecha_inicio = serializers.DateTimeField(source="fecha", read_only=True)
    
    # 3. Mapea Reunion.tipo a 'tipo_reunion'
    tipo_reunion = serializers.CharField(source="tipo", read_only=True) 

    # 4. Campo calculado: Asistentes
    asistentes_count = serializers.SerializerMethodField()

    class Meta:
        model = Reunion
        fields = [
            "id", 
            "titulo", 
            "tabla", 
            "estado", 
            "creada_el",
            # Campos mapeados/calculados
            "autor",
            "fecha_inicio",
            "tipo_reunion",
            "asistentes_count"
        ]

    def get_asistentes_count(self, obj):
        """
        Calcula el número de asistentes confirmados (presente=True) 
        usando el related_name correcto: 'asistentes'.
        """
        try:
            return obj.asistentes.filter(presente=True).count()
        except Exception as e:
            # En caso de error inesperado, devuelve 0
            print(f"Error al calcular asistentes: {e}")
            return 0


class ActaSerializer(serializers.ModelSerializer):
    # Acta usa OneToOne(primary_key=True) con Reunion
    reunion = serializers.PrimaryKeyRelatedField(read_only=True)
    reunion_titulo = serializers.CharField(source="reunion.titulo", read_only=True)
    # ELIMINAMOS EL FORMATO TAMBIÉN AQUÍ si tu Acta API usa este Serializer
    reunion_fecha = serializers.DateTimeField(source="reunion.fecha", read_only=True) 
    reunion_tipo = serializers.CharField(source="reunion.tipo", read_only=True)
    
    # Añadimos el autor del acta como string para el DTO
    autor_username = serializers.CharField(source="autor.username", read_only=True)

    class Meta:
        model = Acta
        fields = [
            "reunion", "contenido", "aprobada",
            "reunion_titulo", "reunion_fecha", "reunion_tipo",
            "autor_username"
        ]
class AsistenciaSerializer(serializers.ModelSerializer):

    nombre_usuario= serializers.CharField(source="vecino.username", read_only=True, default=None)
    rut  = serializers.CharField(source="vecino.rut", read_only=True, default=None)
    nombre_completo = serializers.SerializerMethodField()

    def get_nombre_completo(self, obj):
        v = getattr(obj, "vecino", None)
        if not v:
            return None
    
        if hasattr(v, "get_full_name"):
            full = v.get_full_name()
            if full:
                return full
        # Lógica de construcción de nombre
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
        model= Asistencia
        fields = ["id", "reunion", "nombre_usuario", "nombre_completo", "rut", "presente"]