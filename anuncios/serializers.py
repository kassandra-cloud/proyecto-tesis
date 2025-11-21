# anuncios/serializers.py
from rest_framework import serializers
from .models import Anuncio

class AnuncioSerializer(serializers.ModelSerializer):
    # Traemos el nombre completo del autor para que se vea bonito en la app
    autor_nombre = serializers.CharField(source='autor.get_full_name', read_only=True)

    class Meta:
        model = Anuncio
        fields = ['id', 'titulo', 'contenido', 'fecha_creacion', 'autor_nombre']