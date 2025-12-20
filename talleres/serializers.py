"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Serializador para transformar el modelo Taller a JSON. Incluye 
               campos calculados como cupos disponibles y estado de inscripción 
               del usuario actual.
--------------------------------------------------------------------------------
"""
from rest_framework import serializers
from .models import Taller
from .models import Taller, Inscripcion

class TallerSerializer(serializers.ModelSerializer):
    # Campos calculados adicionales
    inscritos_count = serializers.SerializerMethodField()
    cupos_disponibles = serializers.SerializerMethodField()
    # CORRECCIÓN 2: Declarar el nuevo campo para el estado de inscripción
    esta_inscrito = serializers.SerializerMethodField() 

    class Meta:
        model = Taller
        fields = [
            "id", 
            "nombre", 
            "descripcion", 
            "cupos_totales", 
            "fecha_inicio",  
            "fecha_termino", 
            "inscritos_count", 
            "cupos_disponibles",
            "esta_inscrito"
        ]

    def get_inscritos_count(self, obj):
        # Cuenta inscripciones asociadas
        return obj.inscripcion_set.count()

    def get_cupos_disponibles(self, obj):
        # Calcula cupos restantes, asegurando que no sea negativo
        return max(0, obj.cupos_totales - obj.inscripcion_set.count())
    

    def get_esta_inscrito(self, obj):
            # Verifica si el usuario de la petición está inscrito en este taller
            request = self.context.get('request') 
            if request and request.user.is_authenticated:
                return Inscripcion.objects.filter(vecino=request.user, taller=obj).exists()
            return False