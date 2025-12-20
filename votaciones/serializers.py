"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Serializadores para transformar los modelos Votacion, Opcion y Voto 
               a JSON. Incluye campos calculados para estado de voto y conteos.
--------------------------------------------------------------------------------
"""
from rest_framework import serializers
from .models import Votacion, Opcion as OpcionVoto, Voto  # Importa alias para claridad
from django.db.models import Count

class OpcionVotoSerializer(serializers.ModelSerializer):
    """Serializer para las opciones individuales de una votación."""
    
    # Campo calculado para contar cuántos votos tiene esta opción
    votos_count = serializers.SerializerMethodField()
    
    class Meta:
        model = OpcionVoto
        fields = ['id', 'texto', 'votos_count']
        read_only_fields = ['votos_count']

    def get_votos_count(self, obj):
        # Cuenta los objetos Voto asociados a esta opción
        return obj.voto_set.count() 

class VotacionSerializer(serializers.ModelSerializer):
    """Serializer principal para la Votación."""
    
    # 1. Lista anidada de todas las opciones de voto (incluyendo el conteo)
    opciones = OpcionVotoSerializer(many=True, read_only=True)
    
    # 2. Campo calculado para saber si el usuario ya votó
    ha_votado = serializers.SerializerMethodField()
    
    # 3. Mapea creada_por (FK) a autor (ID)
    autor = serializers.IntegerField(source='creada_por.id', read_only=True)

    class Meta:
        model = Votacion
        fields = [
            'id', 
            'titulo', 
            'descripcion', 
            'fecha_creacion', 
            'fecha_cierre',
            'activa',
            'opciones', 
            'ha_votado',
            'autor',
        ]
        
    def get_ha_votado(self, obj):
        """
        Determina si el usuario autenticado ha emitido un voto en esta votación.
        """
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            # Verifica existencia de voto para este usuario en esta votación
            return obj.voto_set.filter(vecino=request.user).exists() 
            
        return False

# --- Serializer para registrar un Voto ---
class VotoRegistroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voto
        fields = ['opcion_voto']  # Espera el ID de la opción
    
    def validate(self, data):
        # Validaciones de lógica de negocio (usuario, votación activa, unicidad)
        request = self.context.get('request')
        votacion = self.context.get('votacion')
        opcion = data['opcion_voto']
        
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Debe estar autenticado para votar.")
            
        if not votacion:
            raise serializers.ValidationError("La votación no es válida.")

        # Verificar si la opción pertenece a la votación
        if opcion.votacion != votacion:
            raise serializers.ValidationError("La opción seleccionada no pertenece a esta votación.")
            
        # Verificar si ya votó
        if Voto.objects.filter(votacion=votacion, vecino=request.user).exists():
            raise serializers.ValidationError("Usted ya emitió un voto para esta votación.")
            
        return data
        
    def create(self, validated_data):
        # Asignar votacion y vecino antes de crear el objeto Voto
        validated_data['votacion'] = self.context.get('votacion')
        validated_data['vecino'] = self.context.get('request').user
        return Voto.objects.create(**validated_data)