from rest_framework import serializers
from .models import Votacion, OpcionVoto, Voto
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
        # Cuenta los objetos Voto que apuntan a esta opción
        # Se asume que el related_name por defecto 'voto_set' está activo
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
        Requiere que el request esté disponible en el contexto.
        """
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            # Asumimos que la relación inversa de Voto a Votacion es 'votos'
            # y que la FK a User en Voto es 'vecino' (basado en otros módulos)
            # Si el related_name del FK de Voto a Votacion es 'votos', esto funcionará:
            # Voto.objects.filter(votacion=obj, vecino=request.user).exists()
            return obj.voto_set.filter(vecino=request.user).exists() 
            
        return False

# --- Serializer para registrar un Voto ---
class VotoRegistroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voto
        # Solo necesitamos la opción elegida, ya que votacion y vecino (user) 
        # se obtendrán del contexto o la URL
        fields = ['opcion_voto'] 
    
    def validate(self, data):
        # Lógica de validación
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