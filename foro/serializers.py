# foro/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from foro.models import Publicacion, Comentario, ArchivoAdjunto  # <-- OJO aquí
User = get_user_model()
class ArchivoAdjuntoSerializer(serializers.ModelSerializer):
    autor = serializers.CharField(source="autor.username", read_only=True)
    url = serializers.SerializerMethodField()
    fecha_creacion = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    total_likes = serializers.SerializerMethodField()
    me_gusta_usuario = serializers.SerializerMethodField()
    class Meta:
        model = ArchivoAdjunto
        fields = ("id", "autor", "tipo_archivo", "url", "fecha_creacion", "archivo", "es_mensaje", "descripcion")

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
        # Aseguramos que el campo en la respuesta sea 'autor_username'
        fields = ("id", "autor_username", "contenido", "fecha_creacion", "parent")
class ComentarioCreateSerializer(serializers.Serializer):
    texto = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)
    parent = serializers.IntegerField(required=False, allow_null=True)
    total_likes = serializers.SerializerMethodField()
    me_gusta_usuario = serializers.SerializerMethodField()
    class Meta:
        model = Comentario
        fields = ("id", "autor_username", "contenido", "fecha_creacion", "parent", "total_likes", "me_gusta_usuario")
    def get_total_likes(self, obj):
        return obj.likes.count()

    def get_me_gusta_usuario(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.likes.filter(pk=request.user.pk).exists()
        return False
class PublicacionSerializer(serializers.ModelSerializer):
    autor = serializers.CharField(source="autor.username", read_only=True)
    fecha_creacion = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    adjuntos = ArchivoAdjuntoSerializer(many=True, read_only=True)
    
    comentarios = serializers.SerializerMethodField()

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
    def get_comentarios(self, obj):
        # Filtramos solo los comentarios que NO han sido eliminados (visible=True)
        qs = obj.comentarios.filter(visible=True).order_by('fecha_creacion')
        return ComentarioSerializer(qs, many=True).data