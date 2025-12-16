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
from rest_framework.decorators import api_view, permission_classes, authentication_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.response import Response
from rest_framework import status
from .serializers import PublicacionSerializer, ArchivoAdjuntoSerializer, ComentarioSerializer
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from core.templatetags.can import can
from itertools import chain
from operator import attrgetter
from core.authz import can, role_required
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
            es_mensaje=True
        )

    return Response({"mensaje": "ok"})
@login_required
def detalle_publicacion(request, pk):
    es_moderador = can(request.user, "foro", "moderar")

    # 1) Publicación
    try:
        qs = (
            Publicacion.objects
            .select_related("autor")
            .prefetch_related("adjuntos")
        )
        if es_moderador:
            publicacion = get_object_or_404(qs, pk=pk)
        else:
            publicacion = get_object_or_404(qs, pk=pk, visible=True)
    except Http404:
        messages.error(request, "Esa publicación no existe o no tienes permiso para verla.")
        return redirect("foro:lista_publicaciones")

    # 2) POST (comentario / respuesta / adjunto)
    if request.method == "POST":
        parent_id = request.POST.get("parent_id")
        reply_to_adjunto_id = request.POST.get("reply_to_adjunto_id")  # ✅ NUEVO

        # ---- CASO A: Respuesta (a comentario o a adjunto) ----
        if parent_id or reply_to_adjunto_id:
            contenido = (request.POST.get("contenido") or "").strip()

            if not contenido:
                messages.error(request, "El contenido de la respuesta no puede estar vacío.")
                return redirect("foro:detalle_publicacion", pk=publicacion.pk)

            parent_comment = None
            reply_adjunto = None

            # Respuesta a comentario
            if parent_id:
                try:
                    parent_comment = Comentario.objects.get(
                        pk=parent_id,
                        publicacion=publicacion,
                        visible=True
                    )
                except Comentario.DoesNotExist:
                    messages.error(request, "Error al responder: El comentario original no es válido o ha sido eliminado.")
                    return redirect("foro:detalle_publicacion", pk=publicacion.pk)

            # Respuesta a adjunto (imagen/archivo/audio)
            if reply_to_adjunto_id:
                try:
                    reply_adjunto = ArchivoAdjunto.objects.get(
                        pk=reply_to_adjunto_id,
                        publicacion=publicacion
                    )
                except ArchivoAdjunto.DoesNotExist:
                    messages.error(request, "Error al responder: El archivo no existe o no pertenece a la publicación.")
                    return redirect("foro:detalle_publicacion", pk=publicacion.pk)

            Comentario.objects.create(
                publicacion=publicacion,
                autor=request.user,
                contenido=contenido,
                parent=parent_comment,
                reply_to_adjunto=reply_adjunto  # ✅ NUEVO
            )

            messages.success(request, "Respuesta publicada.")
            return redirect("foro:detalle_publicacion", pk=publicacion.pk)

        # ---- CASO B: Form principal (texto + archivo opcional) ----
        form = ComentarioCreateForm(request.POST, request.FILES)

        if form.is_valid():
            contenido = (form.cleaned_data.get("contenido") or "").strip()
            archivos_subidos = request.FILES.getlist("archivo")

            if not contenido and not archivos_subidos:
                messages.error(request, "Debes ingresar contenido o adjuntar un archivo.")
                return redirect("foro:detalle_publicacion", pk=publicacion.pk)

            if archivos_subidos:
                for archivo in archivos_subidos:
                    ArchivoAdjunto.objects.create(
                        publicacion=publicacion,
                        autor=request.user,
                        archivo=archivo,
                        es_mensaje=True,
                        descripcion=contenido
                    )
                messages.success(request, "Archivos publicados correctamente.")
            else:
                form.save(publicacion=publicacion, autor=request.user)
                messages.success(request, "Comentario publicado.")

            return redirect("foro:detalle_publicacion", pk=publicacion.pk)

        messages.error(request, "No se pudo publicar el comentario. Revisa los campos.")

    else:
        form = ComentarioCreateForm()

    # 3) Conversación (comentarios + adjuntos chat)
    comentarios = (
        publicacion.comentarios
        .filter(visible=True)
        .select_related("autor", "parent__autor", "reply_to_adjunto__autor")  # ✅ NUEVO
    )
    adjuntos_chat = (
        publicacion.adjuntos
        .filter(es_mensaje=True)
        .select_related("autor")
    )

    conversacion = sorted(
        chain(comentarios, adjuntos_chat),
        key=attrgetter("fecha_creacion")
    )

    return render(request, "foro/detalle_publicacion.html", {
        "publicacion": publicacion,
        "form": form,
        "conversacion": conversacion,
        "es_moderador": es_moderador,
    })

# --- VISTAS DE MODERACIÓN (WEB) ---

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

    # ✅ SOLO el autor puede eliminar
    if request.user != comentario.autor:
        messages.error(request, "Solo puedes eliminar tus propios comentarios.")
        return redirect("foro:detalle_publicacion", pk=comentario.publicacion_id)

    comentario.visible = False
    comentario.save()
    messages.warning(request, "Comentario eliminado.")

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
    contenido_truncado = (publicacion.contenido[:20] + '...') if len(publicacion.contenido) > 20 else publicacion.contenido
    
    publicacion.delete()
    
    messages.error(request, f"Publicación '{contenido_truncado}' eliminada permanentemente.")
    return redirect("foro:lista_publicaciones")


# ------------------------------------------------------------------------------
#                                   API (REST)
# ------------------------------------------------------------------------------

# Funciones auxiliares para DTOs
def _adjunto_to_dict(adj: ArchivoAdjunto) -> dict:
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
        "parent": c.parent_id, # <--- CLAVE PARA ANIDACIÓN EN APP MÓVIL
    }
@login_required
def crear_publicacion(request):
    if request.method != "POST":
        return redirect("foro:lista_publicaciones")

    form = PublicacionForm(request.POST, request.FILES)
    if form.is_valid():
        publicacion = form.save(commit=False)
        publicacion.autor = request.user
        publicacion.save()

        # CORRECCIÓN APLICADA: Marcar como mensaje para que aparezca en el feed.
        for f in request.FILES.getlist("archivos"):
            ArchivoAdjunto.objects.create(
                publicacion=publicacion,
                archivo=f,
                autor=request.user,
                es_mensaje=True # <--- Línea agregada
            )

        messages.success(request, "Publicación creada correctamente.")
        return redirect("foro:lista_publicaciones")

    request.session["form_con_error_data"] = request.POST
    request.session["form_errors"] = form.errors.as_json()
    messages.error(request, "No se pudo crear la publicación.")
    return redirect("foro:lista_publicaciones")

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
        parent_obj = get_object_or_404(Comentario, pk=parent_id, publicacion=pub)

    c = Comentario.objects.create(
        publicacion=pub,
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
        return Response({"detail": "No se envió ningún archivo."}, status=400)

    # 1. Recibir el flag 'esMensaje' (Android envía "true"/"false" como string)
    es_mensaje_str = request.data.get('esMensaje', 'false')
    es_mensaje = es_mensaje_str.lower() == 'true'

    # 2. Recibir la descripción (caption)
    descripcion = request.data.get('descripcion', '')

    # 3. Crear el objeto incluyendo la descripción
    adj = ArchivoAdjunto(
        publicacion=publicacion,
        archivo=archivo,
        autor=request.user,
        es_mensaje=es_mensaje,     # Usamos el valor recibido
        descripcion=descripcion    # <--- Guardamos el texto aquí
    )
    adj.save()

    serializer = ArchivoAdjuntoSerializer(adj, context={"request": request})
    return Response(serializer.data, status=201)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def enviar_mensaje(request, publicacion_id):
    """
    Recibe mensaje unificado (texto + archivo).
    CORREGIDO: No escribe en el campo 'tipo_archivo'.
    """
    
    # --- DEBUG (Puedes borrar esto cuando funcione) ---
    print("--- DEBUG ENVIO MENSAJE ---")
    print(f"Usuario: {request.user}")
    print(f"Data: {request.data}")
    print(f"FILES: {request.FILES}")
    # --------------------------------------------------

    try:
        pub = Publicacion.objects.get(id=publicacion_id)
    except Publicacion.DoesNotExist:
        return Response({"error": "Publicación no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    usuario = request.user
    texto = request.data.get("texto", "").strip()
    archivo = request.FILES.get("archivo", None)

    if not texto and not archivo:
        return Response(
            {"error": "Debe enviar texto o una imagen"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 1. Crear comentario (solo si hay texto)
    if texto:
        Comentario.objects.create(
            publicacion=pub,
            autor=usuario,
            contenido=texto,
            visible=True
        )

    # 2. Crear adjunto (solo si hay imagen)
    if archivo:
        ArchivoAdjunto.objects.create(
            publicacion=pub,
            archivo=archivo,
            # CORREGIDO: Eliminada la línea 'tipo_archivo="imagen"'
            autor=usuario
        )

    # 3. Devolver la publicación actualizada
    serializer = PublicacionSerializer(pub, context={"request": request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(["DELETE"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def api_eliminar_comentario(request, pk):
    try:
        comentario = Comentario.objects.get(pk=pk, visible=True)
    except Comentario.DoesNotExist:
        return Response({"error": "Comentario no encontrado"}, status=404)

    if comentario.autor != request.user:
        return Response({"error": "No tienes permiso para eliminar este comentario"}, status=403)

    comentario.visible = False
    comentario.save()

    return Response(status=status.HTTP_204_NO_CONTENT)

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

    return Response({
        "liked": liked,
        "total_likes": comentario.likes.count()
    })

@require_POST
@login_required
def reaccionar_comentario_web(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk, visible=True)

    if request.user in comentario.likes.all():
        comentario.likes.remove(request.user)
    else:
        comentario.likes.add(request.user)

    return redirect("foro:detalle_publicacion", pk=comentario.publicacion.pk)

@api_view(["DELETE"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def api_eliminar_adjunto(request, pk):
    try:
        # Buscamos el adjunto por ID
        adjunto = ArchivoAdjunto.objects.get(pk=pk)
    except ArchivoAdjunto.DoesNotExist:
        return Response({"error": "Adjunto no encontrado"}, status=404)

    # Verificamos que quien borra sea el dueño
    if adjunto.autor != request.user:
        return Response({"error": "No tienes permiso para eliminar esto"}, status=403)

    # Borramos el archivo y el registro
    adjunto.delete()

    return Response(status=status.HTTP_204_NO_CONTENT)

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

    return Response({
        "liked": liked,
        "total_likes": adjunto.likes.count()
    })
@require_POST
@login_required
def reaccionar_adjunto_web(request, pk):
    adjunto = get_object_or_404(ArchivoAdjunto, pk=pk)

    if request.user in adjunto.likes.all():
        adjunto.likes.remove(request.user)
    else:
        adjunto.likes.add(request.user)

    return redirect("foro:detalle_publicacion", pk=adjunto.publicacion_id)

@require_POST
@login_required
def eliminar_adjunto_web(request, pk):
    adjunto = get_object_or_404(ArchivoAdjunto, pk=pk)

    # ✅ SOLO el autor puede eliminar su adjunto
    if request.user != adjunto.autor:
        messages.error(request, "Solo puedes eliminar tus propios archivos.")
        return redirect("foro:detalle_publicacion", pk=adjunto.publicacion_id)

    adjunto.delete()
    messages.warning(request, "Archivo eliminado.")

    return redirect("foro:detalle_publicacion", pk=adjunto.publicacion_id)