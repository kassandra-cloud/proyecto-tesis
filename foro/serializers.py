# foro/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from foro.models import Publicacion, Comentario, ArchivoAdjunto  # <-- OJO aquí
User = get_user_model()


class ArchivoAdjuntoSerializer(serializers.ModelSerializer):
    # si quieres exponer la URL absoluta puedes usar SerializerMethodField
    class Meta:
        model = ArchivoAdjunto
        fields = ("id", "archivo", "tipo_archivo", "nombre")

    # Alias "url" para que calce con tu app móvil (AdjuntoDto.url)
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        try:
            return obj.archivo.url
        except Exception:
            return ""


class ComentarioSerializer(serializers.ModelSerializer):
    autor_username = serializers.CharField(source="autor.username", read_only=True)
    fecha_creacion = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Comentario
        fields = ("id", "autor_username", "contenido", "fecha_creacion", "parent")


class ComentarioCreateSerializer(serializers.Serializer):
    texto = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)
    parent = serializers.IntegerField(required=False, allow_null=True)


class PublicacionSerializer(serializers.ModelSerializer):
    fecha_creacion = serializers.DateTimeField(read_only=True)
    # Si tu related_name en ArchivoAdjunto es "adjuntos" (lo usual en tu código)
    adjuntos = ArchivoAdjuntoSerializer(many=True, read_only=True)
    comentarios = serializers.SerializerMethodField()

    class Meta:
        model = Publicacion
        fields = ("id", "autor", "contenido", "fecha_creacion", "adjuntos", "comentarios")

    def get_comentarios(self, obj):
        qs = obj.comentarios.select_related("autor").order_by("fecha_creacion")
        return ComentarioSerializer(qs, many=True).data
