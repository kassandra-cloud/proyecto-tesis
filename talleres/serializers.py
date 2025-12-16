from rest_framework import serializers
from .models import Taller
from .models import Taller, Inscripcion
class TallerSerializer(serializers.ModelSerializer):
    inscritos_count = serializers.SerializerMethodField()
    cupos_disponibles = serializers.SerializerMethodField()
    # 🔑 CORRECCIÓN 2: Declarar el nuevo campo para el estado de inscripción
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
      
        return obj.inscripcion_set.count()

    def get_cupos_disponibles(self, obj):
        return max(0, obj.cupos_totales - obj.inscripcion_set.count())
    

    def get_esta_inscrito(self, obj):
            request = self.context.get('request') 
            if request and request.user.is_authenticated:
                return Inscripcion.objects.filter(vecino=request.user, taller=obj).exists()
            return False