# foro/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from foro.models import Publicacion, Comentario, ArchivoAdjunto  # <-- OJO aquí
User = get_user_model()


class ArchivoAdjuntoSerializer(serializers.ModelSerializer):
    # Alias "url" para que calce con tu app móvil (AdjuntoDto.url)
    url = serializers.SerializerMethodField()

    class Meta:
        model = ArchivoAdjunto
        # 👇 Agregamos "url" al tuple de fields
        fields = ("id", "archivo", "tipo_archivo","url")

    def get_url(self, obj):
        # Si quieres URL absoluta (http://.../media/archivo.png):
        request = self.context.get("request")
        try:
            if request and obj.archivo:
                return request.build_absolute_uri(obj.archivo.url)
            return obj.archivo.url  # relativa como /media/...
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
