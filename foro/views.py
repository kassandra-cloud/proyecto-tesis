# foro/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from core.authz import role_required

from .models import Publicacion, ArchivoAdjunto, Comentario
from .forms import PublicacionForm, ComentarioCreateForm
from core.authz import can
from django.db.models import Q

# ==== API (DRF) ====
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.response import Response
from rest_framework import status


# ------------------------------------------------------------------------------
#                                   WEB
# ------------------------------------------------------------------------------

@login_required
def lista_publicaciones(request):
    """Listado y formulario web para crear publicaciones."""
    
    # --- ▼ REEMPLAZA TU CONSULTA 'publicaciones' POR ESTO ▼ ---
    
    # Comprobamos si el usuario es moderador
    es_moderador = can(request.user, "foro", "moderar")

    if es_moderador:
        # Los moderadores ven TODO (incluyendo publicaciones ocultas)
        publicaciones_qs = Publicacion.objects.all()
    else:
        # Los vecinos normales solo ven las publicaciones visibles
        publicaciones_qs = Publicacion.objects.filter(visible=True)

    publicaciones = (
        publicaciones_qs
        .select_related("autor") # <--- AÑADE ESTO
        .prefetch_related("adjuntos")
        .order_by("-fecha_creacion")
    )

    # Restaurar estado del form si hubo errores en POST previo
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
def crear_publicacion(request):
    """Crea publicación desde el form de la vista anterior (maneja adjuntos)."""
    if request.method != "POST":
        return redirect("lista_publicaciones")

    form = PublicacionForm(request.POST)
    if form.is_valid():
        publicacion = form.save(commit=False)
        publicacion.autor = request.user
        publicacion.save()

        # Adjuntos subidos con <input name="archivos" multiple>
        for f in request.FILES.getlist("archivos"):
            ArchivoAdjunto.objects.create(publicacion=publicacion, archivo=f)

        messages.success(request, "Publicación creada.")
        return redirect("lista_publicaciones")

    # Guardar errores para rehidratar el form tras el redirect
    request.session["form_con_error_data"] = request.POST
    request.session["form_errors"] = form.errors.as_json()
    messages.error(request, "No se pudo crear la publicación.")
    return redirect("lista_publicaciones")


@login_required
def foro_web(request):
    """Versión web con publicaciones y comentarios precargados."""
    publicaciones = (
        Publicacion.objects
        .select_related("autor")
        .prefetch_related("comentarios__autor", "adjuntos")
        .order_by("-fecha_creacion")
    )
    return render(request, "foro/foro_web.html", {"publicaciones": publicaciones})


@require_POST
@login_required
def comentar(request, publicacion_id):
    """
    Crea comentario desde la web (form HTML).
    Esta vista está diseñada para ser llamada por HTMX.
    """
    publicacion = get_object_or_404(Publicacion, id=publicacion_id)
    form = ComentarioCreateForm(request.POST)
    
    if form.is_valid():
        form.save(publicacion=publicacion, autor=request.user)
        # Los 'messages' no se mostrarán porque HTMX reemplaza el HTML.
        # El éxito es implícito cuando el comentario aparece.
    else:
        # Si el form no es válido (ej. comentario vacío), no hacemos nada
        # y simplemente devolvemos la lista de comentarios sin cambios.
        # Podríamos pasar el error, pero por ahora lo mantenemos simple.
        pass

    # --- ESTA ES LA CORRECCIÓN ---
    # En lugar de un 'redirect', llamamos a tu otra vista 'comentarios_partial'
    # que genera solo el HTML de la lista de comentarios.
    # Esto es exactamente lo que HTMX espera recibir.
    return comentarios_partial(request, publicacion_id)


@login_required
def comentarios_partial(request, publicacion_id):
    """Devuelve el HTML parcial de los comentarios de una publicación."""
    pub = get_object_or_404(Publicacion, pk=publicacion_id)
    
    # --- ▼ REEMPLAZA TU CONSULTA 'comentarios' POR ESTO ▼ ---
    es_moderador = can(request.user, "foro", "moderar")
    
    if es_moderador:
        # El moderador ve todos los comentarios
        comentarios_qs = pub.comentarios.all()
    else:
        # El vecino normal ve solo comentarios visibles O sus propios comentarios
        comentarios_qs = pub.comentarios.filter(
            Q(visible=True) | Q(autor=request.user)
        )
        
    comentarios = comentarios_qs.select_related("autor").order_by("fecha_creacion")
    html = render_to_string(
        "foro/_comentarios_ul.html",  # <--- ¡CORREGIDO!
        {"publicacion": pub, "comentarios": comentarios},
        request=request,
    )
    return HttpResponse(html)
@require_POST
@login_required
@role_required("foro", "moderar") # Solo moderadores
def alternar_publicacion(request, pk):
    """
    Oculta o muestra una publicación completa.
    """
    publicacion = get_object_or_404(Publicacion, pk=pk)
    # Alternamos el estado
    publicacion.visible = not publicacion.visible
    publicacion.save()
    
    # --- ▼ ESTA ES LA CORRECCIÓN ▼ ---
    # Volvemos a hacer la consulta para obtener la lista actualizada
    es_moderador = can(request.user, "foro", "moderar")
    if es_moderador:
        publicaciones_qs = Publicacion.objects.all()
    else:
        publicaciones_qs = Publicacion.objects.filter(visible=True)

    publicaciones = (
        publicaciones_qs
        .select_related("autor")
        .prefetch_related("adjuntos")
        .order_by("-fecha_creacion")
    )
    
    context = {"publicaciones": publicaciones}
    
    # Devolvemos SÓLO el fragmento del bucle, no la página entera
    return render(request, "foro/_publicaciones_loop.html", context)
    # --- ▲ FIN DE LA CORRECCIÓN ▲ ---

@require_POST
@login_required
def eliminar_comentario(request, pk):
    """
    Oculta (soft delete) un comentario.
    Un moderador puede ocultar cualquiera.
    Un usuario normal solo puede ocultar el suyo.
    """
    comentario = get_object_or_404(Comentario, pk=pk)
    es_moderador = can(request.user, "foro", "moderar")
    
    # Comprobar permisos
    if request.user == comentario.autor or es_moderador:
        comentario.visible = False
        comentario.save()
    else:
        messages.error(request, "No tienes permisos para eliminar este comentario.")

    # Devolvemos el fragmento de comentarios actualizado
    return comentarios_partial(request, comentario.publicacion_id)

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


@api_view(["GET"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([AllowAny])   # Cambia a IsAuthenticated si lo requieres
def api_publicaciones_list(request):
    """GET /foro/api/v1/publicaciones/"""
    qs = (
        Publicacion.objects
        .select_related("autor")
        .prefetch_related("adjuntos")
        .order_by("-fecha_creacion")
    )
    data = [_publicacion_to_dict(p, incluir_comentarios=False) for p in qs]
    return Response(data)


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
