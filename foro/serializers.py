# foro/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from foro.models import Publicacion, Comentario, ArchivoAdjunto  # <-- OJO aquí
User = get_user_model()
class ArchivoAdjuntoSerializer(serializers.ModelSerializer):
    autor = serializers.CharField(source="autor.username", read_only=True)
    url = serializers.SerializerMethodField()
    fecha_creacion = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

    class Meta:
        model = ArchivoAdjunto
        fields = ("id", "autor", "tipo_archivo", "url", "fecha_creacion", "archivo")

    def get_url(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.archivo.url)
        return obj.archivo.url
class ComentarioSerializer(serializers.ModelSerializer):
    autor_username = serializers.CharField(source="autor.username", read_only=True)
    fecha_creacion = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

    class Meta:
        model = Comentario
        # 💡 Aseguramos que el campo en la respuesta sea 'autor_username'
        fields = ("id", "autor_username", "contenido", "fecha_creacion", "parent")
class ComentarioCreateSerializer(serializers.Serializer):
    texto = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)
    parent = serializers.IntegerField(required=False, allow_null=True)


class PublicacionSerializer(serializers.ModelSerializer):
    # 💡 CORRECCIÓN 2: Usamos el ID (Int) para que coincida con el PublicacionDto
    autor = serializers.IntegerField(source="autor.id", read_only=True) 
    
    fecha_creacion = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    # Usamos el ComentarioSerializer corregido (que ahora tiene 'autor_username')
    adjuntos = ArchivoAdjuntoSerializer(many=True, read_only=True)
    comentarios = ComentarioSerializer(many=True, read_only=True)

    class Meta:
        model = Publicacion
        fields = (
            "id",
            "autor",
            "contenido",
            "fecha_creacion",
            "adjuntos",
            "comentarios",
        )