# reuniones/serializers.py
from rest_framework import serializers
from .models import Reunion, Acta, Asistencia


class ReunionSerializer(serializers.ModelSerializer):
    """
    Serializer para la API de Reuniones (App).
    Optimizado para evitar N+1.
    """

    # Autor como int, evitando null para cliente móvil
    autor = serializers.SerializerMethodField()

    # Mapeos de nombres
    fecha_inicio = serializers.DateTimeField(source="fecha", read_only=True)
    tipo_reunion = serializers.CharField(source="tipo", read_only=True)

    # ✅ IMPORTANTE: usar el annotate del queryset
    # Si en el queryset se agrega `.annotate(asistentes_count=Count(...))`,
    # aquí lo tomamos directo sin queries extra.
    asistentes_count = serializers.IntegerField(read_only=True)

    # Acta (OneToOne) – fields derivados (sin queries extra si usas select_related("acta"))
    acta_contenido = serializers.CharField(source="acta.contenido", read_only=True, allow_null=True)
    acta_estado_transcripcion = serializers.CharField(source="acta.estado_transcripcion", read_only=True, allow_null=True)
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
            "autor",
            "fecha_inicio",
            "tipo_reunion",
            "asistentes_count",
            "acta_contenido",
            "acta_estado_transcripcion",
            "acta_aprobada",
            "acta_id",
        ]

    def get_autor(self, obj):
        # devuelve int siempre (0 si no hay creada_por)
        return obj.creada_por.id if getattr(obj, "creada_por", None) else 0

    def get_acta_aprobada(self, obj):
        acta = getattr(obj, "acta", None)
        if acta is None:
            return None
        return bool(getattr(acta, "aprobada", False))

    def get_acta_id(self, obj):
        acta = getattr(obj, "acta", None)
        return getattr(acta, "pk", None)


class ActaSerializer(serializers.ModelSerializer):
    reunion = serializers.PrimaryKeyRelatedField(read_only=True)
    reunion_titulo = serializers.CharField(source="reunion.titulo", read_only=True)
    reunion_fecha = serializers.DateTimeField(source="reunion.fecha", read_only=True)
    reunion_tipo = serializers.CharField(source="reunion.tipo", read_only=True)

    autor_username = serializers.CharField(
        source="aprobado_por.username",
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Acta
        fields = [
            "reunion",
            "contenido",
            "aprobada",
            "reunion_titulo",
            "reunion_fecha",
            "reunion_tipo",
            "autor_username",
        ]


class AsistenciaSerializer(serializers.ModelSerializer):
    nombre_usuario = serializers.CharField(source="vecino.username", read_only=True, default=None)
    nombre_completo = serializers.SerializerMethodField()
    rut = serializers.SerializerMethodField()  # ✅ evita romper si User no tiene rut

    class Meta:
        model = Asistencia
        fields = ["id", "reunion", "nombre_usuario", "nombre_completo", "rut", "presente"]

    def get_rut(self, obj):
        v = getattr(obj, "vecino", None)
        if not v:
            return None
        return getattr(v, "rut", None)  # si no existe, None

    def get_nombre_completo(self, obj):
        v = getattr(obj, "vecino", None)
        if not v:
            return None

        if hasattr(v, "get_full_name"):
            full = v.get_full_name() or ""
            if full.strip():
                return full.strip()

        partes = []
        for a in ("first_name", "nombres", "nombre"):
            val = (getattr(v, a, "") or "").strip()
            if val:
                partes.append(val)
        for a in ("last_name", "apellidos", "apellido"):
            val = (getattr(v, a, "") or "").strip()
            if val:
                partes.append(val)

        full = " ".join(partes).strip()
        return full or None
