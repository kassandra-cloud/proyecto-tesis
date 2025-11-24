from rest_framework import viewsets, status, permissions, serializers
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser # Importante para subir archivos
from foro.models import Publicacion, Comentario, ArchivoAdjunto

from .serializers import (
    PublicacionSerializer,
    ComentarioSerializer,
    ComentarioCreateSerializer,
    ArchivoAdjuntoSerializer, # Asegúrate de importar esto
)

# --- Serializer anidado SOLO para la vista tree=1 ---
class NestedComentarioSerializer(serializers.ModelSerializer):
    autor_username = serializers.CharField(source="autor.username", read_only=True)
    respuestas = serializers.SerializerMethodField()

    class Meta:
        model = Comentario
        fields = ["id", "autor_username", "contenido", "fecha_creacion", "parent", "respuestas"]

    def get_respuestas(self, obj):
        hijos = obj.respuestas.all().select_related("autor")
        return NestedComentarioSerializer(hijos, many=True, context=self.context).data
# ----------------------------------------------------


class PublicacionViewSet(viewsets.ModelViewSet):
    """
    Rutas via router:
      - GET/POST                 /foro/api/publicaciones/
      - GET/PUT/PATCH/DELETE     /foro/api/publicaciones/{id}/
      - GET/POST                 /foro/api/publicaciones/{id}/comentarios/
      - POST                     /foro/api/publicaciones/{id}/adjuntos/  <-- NUEVA RUTA
      - GET                      /foro/api/publicaciones/mias/
    """
    queryset = (
        Publicacion.objects
        .select_related("autor")
        .prefetch_related("comentarios")
        .order_by("-fecha_creacion")
    )
    serializer_class = PublicacionSerializer

    # Auth y permisos
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    pagination_class = None

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)

    # -------------------------------------------------------------------------
    # 🔹 NUEVA ACCIÓN: SUBIR FOTO CON DESCRIPCIÓN (CAPTION)
    # -------------------------------------------------------------------------
    @action(
        detail=True,
        methods=['post'],
        url_path='adjuntos',
        parser_classes=[MultiPartParser, FormParser] # Permite recibir archivos y texto
    )
    def subir_adjunto(self, request, pk=None):
        # Obtener la publicación
        publicacion = self.get_object()
        
        # 1. Obtener el archivo
        archivo = request.FILES.get('archivo')
        if not archivo:
            return Response({"detail": "No se envió ningún archivo."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Obtener datos extra (mensaje y descripción)
        es_mensaje_str = request.data.get('esMensaje', 'false')
        es_mensaje = es_mensaje_str.lower() == 'true'
        
        descripcion = request.data.get('descripcion', '') # <--- Aquí recibimos el texto

        # 3. Crear el objeto (Foto + Texto unidos)
        adjunto = ArchivoAdjunto.objects.create(
            publicacion=publicacion,
            autor=request.user,
            archivo=archivo,
            es_mensaje=es_mensaje,
            descripcion=descripcion 
        )

        # 4. Responder con el objeto creado
        data = ArchivoAdjuntoSerializer(adjunto, context={'request': request}).data
        return Response(data, status=status.HTTP_201_CREATED)

    # -------------------------------------------------------------------------

    @action(detail=True, methods=["get", "post"], url_path="comentarios")
    def comentarios(self, request, pk=None):
        publicacion = self.get_object()

        if request.method.lower() == "get":
            tree = request.query_params.get("tree") == "1"
            if tree:
                raices = (
                    Comentario.objects
                    .filter(publicacion=publicacion, parent__isnull=True)
                    .select_related("autor")
                    .prefetch_related(
                        "respuestas__autor",
                        "respuestas__respuestas__autor",
                    )
                )
                data = NestedComentarioSerializer(raices, many=True, context={"request": request}).data
                return Response(data, status=status.HTTP_200_OK)

            qs = (
                Comentario.objects
                .filter(publicacion=publicacion)
                .select_related("autor")
                .order_by("fecha_creacion")
            )
            data = ComentarioSerializer(qs, many=True, context={"request": request}).data
            return Response(data, status=status.HTTP_200_OK)

        s = ComentarioCreateSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)

        c = Comentario.objects.create(
            publicacion=publicacion,
            autor=request.user,
            contenido=s.validated_data["contenido"],
            parent_id=s.validated_data.get("parent"),
        )
        out = ComentarioSerializer(c, context={"request": request}).data
        return Response(out, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="mias")
    def mias(self, request):
        qs = self.get_queryset().filter(autor=request.user)
        data = self.get_serializer(qs, many=True, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)
    
