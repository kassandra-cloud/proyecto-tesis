from rest_framework import serializers
from .models import Reunion, Acta, Asistencia 
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers
from .models import Reunion, Acta


class ReunionSerializer(serializers.ModelSerializer):
    """
    Serializer para la API de Reuniones.
    """
    # 🆕 CORRECCIÓN: Usamos SerializerMethodField para manejar creador=None
    autor = serializers.SerializerMethodField() 
    
    fecha_inicio = serializers.DateTimeField(source="fecha", read_only=True)
    tipo_reunion = serializers.CharField(source="tipo", read_only=True)
    asistentes_count = serializers.SerializerMethodField()

    # Campos relacionados al acta
    acta_contenido = serializers.CharField(
        source="acta.contenido",
        read_only=True,
        allow_null=True
    )
    acta_estado_transcripcion = serializers.CharField(
        source="acta.estado_transcripcion",
        read_only=True,
        allow_null=True
    )
    acta_aprobada = serializers.SerializerMethodField()
    acta_id = serializers.SerializerMethodField()

    class Meta:
        model = Reunion
        fields = [
            "id",
            "titulo",
            "tabla",
            "estado",
            "creada_el",
            # mapeados / calculados
            "autor",
            "fecha_inicio",
            "tipo_reunion",
            "asistentes_count",
            # info de acta
            "acta_contenido",
            "acta_estado_transcripcion",
            "acta_aprobada",
            "acta_id",
        ]

    # 🆕 AJUSTE CLAVE: Retorna 0 si el autor es nulo para satisfacer al cliente móvil.
    def get_autor(self, obj):
        """Devuelve el ID del creador o 0 si no existe."""
        if obj.creada_por:
            return obj.creada_por.id
        # Si es None, retorna 0 para que el móvil reciba un Int en lugar de NULL.
        return 0
    
    def get_asistentes_count(self, obj):
        try:
            return obj.asistentes.filter(presente=True).count()
        except Exception:
            return 0

    def get_acta_aprobada(self, obj):
        """
        Devuelve:
        - True  si el acta existe y está aprobada
        - False si el acta existe pero no está aprobada
        - None  si no hay acta
        """
        acta = getattr(obj, "acta", None)
        if acta is None:
            return None
        return bool(getattr(acta, "aprobada", False))

    def get_acta_id(self, obj):
        """
        Devuelve el PK del acta, o None si no existe.
        """
        acta = getattr(obj, "acta", None)
        if acta is None:
            return None
        return acta.pk

class ActaSerializer(serializers.ModelSerializer):
    # Acta usa OneToOne(primary_key=True) con Reunion
    reunion = serializers.PrimaryKeyRelatedField(read_only=True)
    reunion_titulo = serializers.CharField(source="reunion.titulo", read_only=True)
    reunion_fecha = serializers.DateTimeField(source="reunion.fecha", read_only=True) 
    reunion_tipo = serializers.CharField(source="reunion.tipo", read_only=True)
    
    # 🆕 CORRECCIÓN: Fuente aprobada_por y allow_null=True para manejar nulos
    autor_username = serializers.CharField(
        source="aprobado_por.username", # Campo correcto en Acta es 'aprobado_por'
        read_only=True,
        allow_null=True # Permite que sea nulo si no ha sido aprobado
    )

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