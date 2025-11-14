# foro/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.template.loader import render_to_string
from django.db.models import Count, Q
import json

from .models import Publicacion, ArchivoAdjunto, Comentario
from .forms import PublicacionForm, ComentarioCreateForm
from core.authz import can, role_required

# ==== API (DRF) ====
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.response import Response
from rest_framework import status
from .serializers import PublicacionSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Publicacion, ArchivoAdjunto
from .serializers import ArchivoAdjuntoSerializer
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
    parser_classes,
)
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

# ------------------------------------------------------------------------------
#                                   WEB
# ------------------------------------------------------------------------------

@login_required
def lista_publicaciones(request):
    """Listado web. Ahora solo carga publicaciones, no comentarios."""
    
    es_moderador = can(request.user, "foro", "moderar")

    if es_moderador:
        publicaciones_qs = Publicacion.objects.all()
    else:
        publicaciones_qs = Publicacion.objects.filter(visible=True)

    publicaciones = (
        publicaciones_qs
        .select_related("autor")
        .prefetch_related("adjuntos")
        .annotate(num_comentarios=Count('comentarios')) # Contamos comentarios
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
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def crear_mensaje(request):

    publicacion_id = request.data.get("publicacion_id")
    texto = request.data.get("texto", "").strip()
    archivo = request.FILES.get("archivo")

    try:
        publicacion = Publicacion.objects.get(id=publicacion_id)
    except Publicacion.DoesNotExist:
        return Response({"error": "Publicación no existe"}, status=404)

    # 1) si hay texto -> crear comentario
    if texto:
        Comentario.objects.create(
            publicacion=publicacion,
            autor=request.user,
            contenido=texto
        )

    # 2) si hay imagen -> crear "mensaje adjunto"
    if archivo:
        ArchivoAdjunto.objects.create(
            publicacion=publicacion,
            archivo=archivo,
            autor=request.user,
            es_mensaje=True  # <- CLAVE
        )

    return Response({"mensaje": "ok"})

@login_required
def detalle_publicacion(request, pk):
    """
    NUEVA VISTA. Muestra una publicación y sus comentarios.
    También maneja el POST para crear nuevos comentarios/respuestas.
    """
    es_moderador = can(request.user, "foro", "moderar")
    
    # Obtenemos la publicación
    try:
        if es_moderador:
            publicacion = get_object_or_404(Publicacion.objects.select_related("autor").prefetch_related("adjuntos"), pk=pk)
        else:
            publicacion = get_object_or_404(Publicacion.objects.select_related("autor").prefetch_related("adjuntos"), pk=pk, visible=True)
    except Http404:
        messages.error(request, "Esa publicación no existe o no tienes permiso para verla.")
        return redirect("foro:lista_publicaciones") # 👈 CORRECCIÓN: Añadido "foro:"

    # Lógica para ENVIAR un comentario (POST)
    if request.method == "POST":
        form = ComentarioCreateForm(request.POST)
        if form.is_valid():
            form.save(publicacion=publicacion, autor=request.user)
            messages.success(request, "Comentario publicado.")
            # Redirigimos a la misma página (al ancla del nuevo comentario si quisiéramos)
            return redirect("foro:detalle_publicacion", pk=publicacion.pk) # 👈 CORRECCIÓN: Añadido "foro:"
        else:
            messages.error(request, "No se pudo publicar el comentario.")
            # Si hay error, continuamos al GET para mostrar el form con errores
    else:
        # Lógica para VER la página (GET)
        form = ComentarioCreateForm()

    # Obtenemos los comentarios para esta publicación
    if es_moderador:
        comentarios_qs = publicacion.comentarios.all()
    else:
        comentarios_qs = publicacion.comentarios.filter(
            Q(visible=True) | Q(autor=request.user)
        )
        
    comentarios = comentarios_qs.select_related("autor").order_by("fecha_creacion")
    
    context = {
        "publicacion": publicacion,
        "comentarios": comentarios,
        "form_comentario": form,
    }
    return render(request, "foro/detalle_publicacion.html", context)


# --- VISTAS DE MODERACIÓN (WEB) ---
# (Las vistas de HTMX fueron eliminadas o renombradas)

@require_POST
@login_required
@role_required("foro", "moderar")
def alternar_publicacion_web(request, pk):
    """Oculta o muestra una publicación y redirige a la lista."""
    publicacion = get_object_or_404(Publicacion, pk=pk)
    publicacion.visible = not publicacion.visible
    publicacion.save()
    
    if publicacion.visible:
        messages.success(request, "Publicación restaurada.")
    else:
        messages.warning(request, "Publicación ocultada.")
    
    return redirect("foro:lista_publicaciones") # 👈 CORRECCIÓN: Añadido "foro:"

@require_POST
@login_required
def eliminar_comentario_web(request, pk):
    """Oculta (soft delete) un comentario y redirige de vuelta."""
    comentario = get_object_or_404(Comentario, pk=pk)
    es_moderador = can(request.user, "foro", "moderar")
    
    if request.user == comentario.autor or es_moderador:
        comentario.visible = False
        comentario.save()
        messages.warning(request, "Comentario eliminado.")
    else:
        messages.error(request, "No tienes permisos para esta acción.")

    # Redirige de vuelta a la página de detalle
    return redirect("foro:detalle_publicacion", pk=comentario.publicacion_id) # 👈 CORRECCIÓN: Añadido "foro:"

@require_POST
@login_required
@role_required("foro", "moderar")
def restaurar_comentario_web(request, pk):
    """Restaura un comentario (lo vuelve visible) y redirige de vuelta."""
    comentario = get_object_or_404(Comentario, pk=pk)
    
    if not comentario.visible:
        comentario.visible = True
        comentario.save()
        messages.success(request, "Comentario restaurado.")
    
    return redirect("foro:detalle_publicacion", pk=comentario.publicacion_id) # 👈 CORRECCIÓN: Añadido "foro:"

@require_POST
@login_required
@role_required("foro", "delete")
def eliminar_publicacion_web(request, pk):
    """Elimina PERMANENTEMENTE una publicación y redirige a la lista."""
    publicacion = get_object_or_404(Publicacion, pk=pk)
    contenido_truncado = (publicacion.contenido[:20] + '...') if len(publicacion.contenido) > 20 else publicacion.contenido
    
    publicacion.delete()
    
    messages.error(request, f"Publicación '{contenido_truncado}' eliminada permanentemente.")
    return redirect("foro:lista_publicaciones") # 👈 CORRECCIÓN: Añadido "foro:"


# ------------------------------------------------------------------------------
#                                   API (REST)
#  - PublicacionDto: id, autor, contenido, fecha_creacion, adjuntos[], comentarios[]
#  - ComentarioDto:  id, autor_username, contenido, fecha_creacion, parent
#  - AdjuntoDto:     id, url, tipo_archivo, nombre
# ------------------------------------------------------------------------------

def _adjunto_to_dict(adj: ArchivoAdjunto) -> dict:
    """Mapeo a DTO esperado por Android."""
    # Si no tienes campo tipo_archivo, lo derivamos por extensión
    if hasattr(adj, "tipo_archivo") and adj.tipo_archivo:
        tipo = adj.tipo_archivo
    else:
        name = getattr(adj.archivo, "name", "")
        ext = (name.rsplit(".", 1)[-1] if "." in name else "").lower()
        if ext in {"png", "jpg", "jpeg", "gif", "webp"}:
            tipo = "imagen"
        elif ext in {"mp3", "wav", "ogg", "m4a", "webm"}:
            tipo = "audio"
        elif ext in {"mp4", "mov", "avi", "mkv"}:
            tipo = "video"
        else:
            tipo = "archivo"

    return {
        "id": adj.id,
        "url": adj.archivo.url,                 # FileField/Storage
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


def _publicacion_to_dict(p: Publicacion, incluir_comentarios: bool = False) -> dict:
    data = {
        "id": p.id,
        "autor": getattr(p.autor, "username", str(p.autor)),
        "contenido": p.contenido,
        "fecha_creacion": p.fecha_creacion,
        "adjuntos": [_adjunto_to_dict(a) for a in p.adjuntos.all()],
        "comentarios": [],
    }
    if incluir_comentarios:
        qs = p.comentarios.select_related("autor").order_by("fecha_creacion")
        data["comentarios"] = [_comentario_to_dict(c) for c in qs]
    return data
@login_required
def crear_publicacion(request):
    """Crea una publicación desde el sitio web (formulario en modal)."""

    if request.method != "POST":
        return redirect("foro:lista_publicaciones") # 👈 CORRECCIÓN: Añadido "foro:"

    form = PublicacionForm(request.POST, request.FILES)
    if form.is_valid():
        publicacion = form.save(commit=False)
        publicacion.autor = request.user
        publicacion.save()

        # Guardar archivos adjuntos si existen
        for f in request.FILES.getlist("archivos"):
            ArchivoAdjunto.objects.create(
                publicacion=publicacion,
                archivo=f,
                autor=request.user
            )

        messages.success(request, "Publicación creada correctamente.")
        return redirect("foro:lista_publicaciones") # 👈 CORRECCIÓN: Añadido "foro:"

    # Si hay error, mantener el formulario en sesión
    request.session["form_con_error_data"] = request.POST
    request.session["form_errors"] = form.errors.as_json()
    messages.error(request, "No se pudo crear la publicación.")
    return redirect("foro:lista_publicaciones") # 👈 CORRECCIÓN: Añadido "foro:"

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
    """
    GET  /foro/api/v1/publicaciones/<pk>/comentarios/  -> lista comentarios
    POST /foro/api/v1/publicaciones/<pk>/comentarios/  -> crea comentario
         body: {"texto": "...", "parent": <id|null>}
    """
    pub = get_object_or_404(Publicacion, pk=pk)

    if request.method == "GET":
        qs = pub.comentarios.select_related("autor").order_by("fecha_creacion")
        return Response([_comentario_to_dict(c) for c in qs])

    # POST: requiere usuario autenticado
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication credentials were not provided."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    texto = (request.data.get("texto") or "").strip()
    parent_id = request.data.get("parent")

    if not texto:
        return Response({"detail": "texto requerido"}, status=status.HTTP_400_BAD_REQUEST)

    parent_obj = None
    if parent_id:
        parent_obj = get_object_or_404(Comentario, pk=parent_id, publicacion=pub)  # <-- FK

    c = Comentario.objects.create(
        publicacion=pub,     # <-- FK (ajusta si tu campo tiene otro nombre)
        autor=request.user,
        contenido=texto,
        parent=parent_obj,
    )
    return Response(_comentario_to_dict(c), status=status.HTTP_201_CREATED)
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
        return Response({"detail": "No se envió ningún archivo en el campo 'archivo'."},
                        status=400)

    # 🔹 AQUÍ marcamos que este adjunto viene de la app y se mostrará como "mensaje"
    adj = ArchivoAdjunto(
        publicacion=publicacion,
        archivo=archivo,
        autor=request.user,
        es_mensaje=True,   # 👈 CLAVE
    )
    adj.save()

    serializer = ArchivoAdjuntoSerializer(adj, context={"request": request})
    return Response(serializer.data, status=201)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def enviar_mensaje(request, publicacion_id):
    """
    Recibe un mensaje unificado:
    - texto (opcional)
    - archivo (opcional)
    y lo guarda como comentario + adjunto si corresponde.
    """

    try:
        pub = Publicacion.objects.get(id=publicacion_id)
    except Publicacion.DoesNotExist:
        return Response({"error": "Publicación no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    usuario = request.user

    texto = request.data.get("texto", "").strip()
    archivo = request.FILES.get("archivo", None)

    # Si NO hay texto y NO hay imagen → error
    if not texto and not archivo:
        return Response(
            {"error": "Debe enviar texto o una imagen"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # -------------------------------
    # 1. Crear comentario (solo si hay texto)
    # -------------------------------
    comentario = None
    if texto:
        comentario = Comentario.objects.create(
            publicacion=pub,
            autor=usuario,
            contenido=texto,
            visible=True
        )

    # -------------------------------
    # 2. Crear adjunto (solo si hay imagen)
    # -------------------------------
    if archivo:
        ArchivoAdjunto.objects.create(
            publicacion=pub,
            archivo=archivo,
            tipo_archivo="imagen",
            autor=usuario
        )

    # -------------------------------
    # 3. Devolver la publicación actualizada
    # -------------------------------
    serializer = PublicacionSerializer(pub, context={"request": request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)