from rest_framework import viewsets, status, permissions, serializers
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Count
from itertools import chain
from operator import attrgetter

from foro.models import Publicacion, Comentario, ArchivoAdjunto
from foro.forms import PublicacionForm, ComentarioCreateForm
from core.authz import can, role_required  # 👈 ÚNICA IMPORTACIÓN CORRECTA DE 'can'

from .serializers import (
    PublicacionSerializer,
    ComentarioSerializer,
    ComentarioCreateSerializer,
    ArchivoAdjuntoSerializer
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

# ------------------------------------------------------------------------------
#                                   VIEWSETS (DRF)
# ------------------------------------------------------------------------------

class PublicacionViewSet(viewsets.ModelViewSet):
    queryset = (
        Publicacion.objects
        .select_related("autor")
        .prefetch_related("comentarios")
        .order_by("-fecha_creacion")
    )
    serializer_class = PublicacionSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)

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
                    .prefetch_related("respuestas__autor", "respuestas__respuestas__autor")
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


# ------------------------------------------------------------------------------
#                                   VISTAS WEB
# ------------------------------------------------------------------------------

@login_required
def lista_publicaciones(request):
    es_moderador = can(request.user, "foro", "moderar")

    if es_moderador:
        publicaciones_qs = Publicacion.objects.all()
    else:
        publicaciones_qs = Publicacion.objects.filter(visible=True)

    publicaciones = (
        publicaciones_qs
        .select_related("autor")
        .prefetch_related("adjuntos")
        .annotate(num_comentarios=Count('comentarios'))
        .order_by("-fecha_creacion")
    )
    
    form_con_error_data = request.session.pop("form_con_error_data", None)
    form_errors = request.session.pop("form_errors", None)

    if form_con_error_data:
        form = PublicacionForm(form_con_error_data)
        if form_errors:
            form.add_error(None, form_errors)
    else:
        form = PublicacionForm()

    context = {
        "publicaciones": publicaciones,
        "form": form,
        "form_errors_manual": form_errors,
    }
    return render(request, "foro/lista_publicaciones.html", context)

@login_required
def detalle_publicacion(request, pk):
    es_moderador = can(request.user, "foro", "moderar")
    
    try:
        qs = Publicacion.objects.select_related("autor").prefetch_related("adjuntos")
        if es_moderador:
            publicacion = get_object_or_404(qs, pk=pk)
        else:
            publicacion = get_object_or_404(qs, pk=pk, visible=True)
    except:
        messages.error(request, "Esa publicación no existe o no tienes permiso para verla.")
        return redirect("foro:lista_publicaciones")

    if request.method == "POST":
        form = ComentarioCreateForm(request.POST, request.FILES)
        if form.is_valid():
            contenido = form.cleaned_data.get('contenido')
            archivo = form.cleaned_data.get('archivo')

            if archivo:
                ArchivoAdjunto.objects.create(
                    publicacion=publicacion,
                    autor=request.user,
                    archivo=archivo,
                    es_mensaje=True,
                    descripcion=contenido
                )
                messages.success(request, "Archivo publicado.")
            elif contenido:
                comentario = form.save(commit=False)
                comentario.publicacion = publicacion
                comentario.autor = request.user
                comentario.save()
                messages.success(request, "Comentario publicado.")

            return redirect("foro:detalle_publicacion", pk=publicacion.pk)
        else:
            messages.error(request, "No se pudo publicar el comentario.")
    else:
        form = ComentarioCreateForm()

    comentarios = publicacion.comentarios.filter(visible=True).select_related('autor')
    adjuntos_chat = publicacion.adjuntos.filter(es_mensaje=True).select_related('autor')

    conversacion = sorted(
        chain(comentarios, adjuntos_chat),
        key=attrgetter('fecha_creacion')
    )

    return render(request, 'foro/detalle_publicacion.html', {
        'publicacion': publicacion,
        'form': form,
        'conversacion': conversacion, 
        'es_moderador': es_moderador
    })

@login_required
def crear_publicacion(request):
    if request.method != "POST":
        return redirect("foro:lista_publicaciones")

    form = PublicacionForm(request.POST, request.FILES)
    if form.is_valid():
        publicacion = form.save(commit=False)
        publicacion.autor = request.user
        publicacion.save()

        for f in request.FILES.getlist("archivos"):
            ArchivoAdjunto.objects.create(
                publicacion=publicacion,
                archivo=f,
                autor=request.user
            )

        messages.success(request, "Publicación creada correctamente.")
        return redirect("foro:lista_publicaciones")

    request.session["form_con_error_data"] = request.POST
    request.session["form_errors"] = form.errors.as_json()
    messages.error(request, "No se pudo crear la publicación.")
    return redirect("foro:lista_publicaciones")

# --- ACCIONES DE MODERACIÓN Y LIKES (WEB) ---

@require_POST
@login_required
@role_required("foro", "moderar")
def alternar_publicacion_web(request, pk):
    publicacion = get_object_or_404(Publicacion, pk=pk)
    publicacion.visible = not publicacion.visible
    publicacion.save()
    if publicacion.visible:
        messages.success(request, "Publicación restaurada.")
    else:
        messages.warning(request, "Publicación ocultada.")
    return redirect("foro:lista_publicaciones")

@require_POST
@login_required
def eliminar_comentario_web(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    es_moderador = can(request.user, "foro", "moderar")
    if request.user == comentario.autor or es_moderador:
        comentario.visible = False
        comentario.save()
        messages.warning(request, "Comentario eliminado.")
    else:
        messages.error(request, "No tienes permisos para esta acción.")
    return redirect("foro:detalle_publicacion", pk=comentario.publicacion_id)

@require_POST
@login_required
@role_required("foro", "moderar")
def restaurar_comentario_web(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    if not comentario.visible:
        comentario.visible = True
        comentario.save()
        messages.success(request, "Comentario restaurado.")
    return redirect("foro:detalle_publicacion", pk=comentario.publicacion_id)

@require_POST
@login_required
@role_required("foro", "delete")
def eliminar_publicacion_web(request, pk):
    publicacion = get_object_or_404(Publicacion, pk=pk)
    publicacion.delete()
    messages.error(request, "Publicación eliminada permanentemente.")
    return redirect("foro:lista_publicaciones")

@login_required
def reaccionar_comentario_web(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk, visible=True)
    if request.user in comentario.likes.all():
        comentario.likes.remove(request.user)
    else:
        comentario.likes.add(request.user)
    return redirect("foro:detalle_publicacion", pk=comentario.publicacion.pk)


# ------------------------------------------------------------------------------
#                                   API ENDPOINTS (Funcionales)
# ------------------------------------------------------------------------------

def _adjunto_to_dict(adj: ArchivoAdjunto) -> dict:
    if hasattr(adj, "tipo_archivo") and adj.tipo_archivo:
        tipo = adj.tipo_archivo
    else:
        # Fallback simple
        name = getattr(adj.archivo, "name", "")
        ext = (name.rsplit(".", 1)[-1] if "." in name else "").lower()
        if ext in {"png", "jpg", "jpeg", "gif", "webp"}: tipo = "imagen"
        elif ext in {"mp3", "wav", "ogg", "m4a"}: tipo = "audio"
        else: tipo = "archivo"

    return {
        "id": adj.id,
        "url": adj.archivo.url,
        "tipo_archivo": tipo,
        "nombre": getattr(adj, "nombre", None),
    }

def _comentario_to_dict(c: Comentario) -> dict:
    return {
        "id": c.id,
        "autor_username": c.autor.username,
        "contenido": c.contenido,
        "fecha_creacion": c.fecha_creacion,
        "parent": c.parent_id,
    }

@api_view(["GET"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticatedOrReadOnly])
def api_publicaciones_list(request):
    qs = (
        Publicacion.objects.filter(visible=True)
        .select_related("autor")
        .prefetch_related("adjuntos", "comentarios__autor")
        .order_by("-fecha_creacion")
    )
    serializer = PublicacionSerializer(qs, many=True, context={"request": request})
    return Response(serializer.data)

@api_view(["GET", "POST"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def api_publicacion_comentarios(request, pk: int):
    pub = get_object_or_404(Publicacion, pk=pk)

    if request.method == "GET":
        qs = pub.comentarios.select_related("autor").order_by("fecha_creacion")
        return Response([_comentario_to_dict(c) for c in qs])

    if not request.user.is_authenticated:
        return Response({"detail": "No autenticado."}, status=401)

    texto = (request.data.get("texto") or "").strip()
    parent_id = request.data.get("parent")

    if not texto:
        return Response({"detail": "texto requerido"}, status=400)

    parent_obj = None
    if parent_id:
        parent_obj = get_object_or_404(Comentario, pk=parent_id, publicacion=pub)

    c = Comentario.objects.create(
        publicacion=pub,
        autor=request.user,
        contenido=texto,
        parent=parent_obj,
    )
    return Response(_comentario_to_dict(c), status=201)

# 🔹 API: SUBIR FOTO + DESCRIPCIÓN (UNIFICADO)
@api_view(["POST"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def api_subir_adjunto(request, pk: int):
    try:
        publicacion = Publicacion.objects.get(pk=pk, visible=True)
    except Publicacion.DoesNotExist:
        return Response({"detail": "Publicación no encontrada."}, status=404)

    archivo = request.FILES.get("archivo")
    if not archivo:
        return Response({"detail": "No se envió ningún archivo."}, status=400)

    es_mensaje_str = request.data.get('esMensaje', 'false')
    es_mensaje = es_mensaje_str.lower() == 'true'
    descripcion = request.data.get('descripcion', '') # Capturamos el texto

    adj = ArchivoAdjunto(
        publicacion=publicacion,
        archivo=archivo,
        autor=request.user,
        es_mensaje=es_mensaje,
        descripcion=descripcion
    )
    adj.save()

    serializer = ArchivoAdjuntoSerializer(adj, context={"request": request})
    return Response(serializer.data, status=201)

@api_view(["DELETE"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def api_eliminar_comentario(request, pk):
    try:
        comentario = Comentario.objects.get(pk=pk, visible=True)
    except Comentario.DoesNotExist:
        return Response({"error": "Comentario no encontrado"}, status=404)

    if comentario.autor != request.user:
        return Response({"error": "No tienes permiso"}, status=403)

    comentario.visible = False
    comentario.save()
    return Response(status=204)

@api_view(["DELETE"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def api_eliminar_adjunto(request, pk):
    try:
        adjunto = ArchivoAdjunto.objects.get(pk=pk)
    except ArchivoAdjunto.DoesNotExist:
        return Response({"error": "Adjunto no encontrado"}, status=404)

    if adjunto.autor != request.user:
        return Response({"error": "No tienes permiso"}, status=403)

    adjunto.delete()
    return Response(status=204)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_toggle_like_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk, visible=True)
    usuario = request.user
    if usuario in comentario.likes.all():
        comentario.likes.remove(usuario)
        liked = False
    else:
        comentario.likes.add(usuario)
        liked = True
    return Response({"liked": liked, "total_likes": comentario.likes.count()})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_toggle_like_adjunto(request, pk):
    adjunto = get_object_or_404(ArchivoAdjunto, pk=pk)
    usuario = request.user
    if usuario in adjunto.likes.all():
        adjunto.likes.remove(usuario)
        liked = False
    else:
        adjunto.likes.add(usuario)
        liked = True
    return Response({"liked": liked, "total_likes": adjunto.likes.count()})