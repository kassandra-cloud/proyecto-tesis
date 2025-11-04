# foro/api.py
from rest_framework import viewsets, status, permissions, serializers
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response
from foro.models import Publicacion, Comentario, ArchivoAdjunto


from .serializers import (
    PublicacionSerializer,
    ComentarioSerializer,        # plano: id, autor_username, contenido, fecha_creacion, parent
    ComentarioCreateSerializer,  # POST: {contenido, parent?}
)

# --- Serializer anidado SOLO para la vista tree=1 ---
class NestedComentarioSerializer(serializers.ModelSerializer):
    autor_username = serializers.CharField(source="autor.username", read_only=True)
    respuestas = serializers.SerializerMethodField()

    class Meta:
        model = Comentario
        fields = ["id", "autor_username", "contenido", "fecha_creacion", "parent", "respuestas"]

    def get_respuestas(self, obj):
        # requiere en el modelo: parent = FK("self", related_name="respuestas", ...)
        hijos = obj.respuestas.all().select_related("autor")
        return NestedComentarioSerializer(hijos, many=True, context=self.context).data
# ----------------------------------------------------


class PublicacionViewSet(viewsets.ModelViewSet):
    """
    Rutas via router:
      - GET/POST                 /foro/api/publicaciones/
      - GET/PUT/PATCH/DELETE     /foro/api/publicaciones/{id}/
      - GET/POST                 /foro/api/publicaciones/{id}/comentarios/
      - GET                      /foro/api/publicaciones/mias/
    """
    queryset = (
        Publicacion.objects
        .select_related("autor")
        .prefetch_related("comentarios")     # comentarios de la publicación
        .order_by("-fecha_creacion")
    )
    serializer_class = PublicacionSerializer

    # Auth y permisos
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    # Sin paginación: Android recibe ARRAY
    pagination_class = None

    def perform_create(self, serializer):
        # setea autor automáticamente
        serializer.save(autor=self.request.user)

    @action(detail=True, methods=["get", "post"], url_path="comentarios")
    def comentarios(self, request, pk=None):
        """
        GET:
          - Plano (compat móvil): /foro/api/publicaciones/{id}/comentarios/
          - Árbol (anidado):      /foro/api/publicaciones/{id}/comentarios/?tree=1
        POST:
          body { "contenido": "texto...", "parent": <id_opcional> }
        """
        publicacion = self.get_object()

        if request.method.lower() == "get":
            tree = request.query_params.get("tree") == "1"
            if tree:
                # solo raíces + sus hijos recursivos (NestedComentarioSerializer)
                raices = (
                    Comentario.objects
                    .filter(publicacion=publicacion, parent__isnull=True)
                    .select_related("autor")
                    .prefetch_related(
                        "respuestas__autor",
                        "respuestas__respuestas__autor",  # 2 niveles; el serializer sigue recursivo
                    )
                )
                data = NestedComentarioSerializer(raices, many=True, context={"request": request}).data
                return Response(data, status=status.HTTP_200_OK)

            # lista plana ordenada por fecha (más simple para app)
            qs = (
                Comentario.objects
                .filter(publicacion=publicacion)
                .select_related("autor")
                .order_by("fecha_creacion")
            )
            data = ComentarioSerializer(qs, many=True, context={"request": request}).data
            return Response(data, status=status.HTTP_200_OK)

        # POST: crear comentario o respuesta
        s = ComentarioCreateSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)

        c = Comentario.objects.create(
            publicacion=publicacion,
            autor=request.user,
            contenido=s.validated_data["contenido"],
            parent_id=s.validated_data.get("parent"),  # puede venir null
        )
        out = ComentarioSerializer(c, context={"request": request}).data
        return Response(out, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="mias")
    def mias(self, request):
        """Devuelve solo las publicaciones del usuario autenticado (ARRAY)."""
        qs = self.get_queryset().filter(autor=request.user)
        data = self.get_serializer(qs, many=True, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)
