"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Define el serializador para el modelo Anuncio usando 
                       Django REST Framework. Convierte los objetos de la base 
                       de datos a JSON para ser consumidos por la API.
--------------------------------------------------------------------------------
"""

# Importa el módulo de serializadores de DRF.
from rest_framework import serializers
# Importa el modelo Anuncio.
from .models import Anuncio

class AnuncioSerializer(serializers.ModelSerializer):
    """Serializador para convertir anuncios a JSON."""
    
    # Campo personalizado: obtiene el nombre completo del autor accediendo a la relación.
    # 'read_only=True' asegura que este campo es solo para mostrar, no para escribir.
    autor_nombre = serializers.CharField(source='autor.get_full_name', read_only=True)

    class Meta:
        # Define el modelo base.
        model = Anuncio
        # Lista explícita de campos a incluir en el JSON final.
        fields = ['id', 'titulo', 'contenido', 'fecha_creacion', 'autor_nombre']