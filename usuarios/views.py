# usuarios/views.py
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.authz import role_required
from .forms import UsuarioCrearForm, UsuarioEditarForm
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
User = get_user_model()
import json
from django.views.decorators.http import require_POST
# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
OPCIONES_PER_PAGE = [10, 25, 50]

# map de columnas permitidas en sort -> field de ORM
SORT_MAP = {
    "username": "username",
    "email": "email",
    "nombre": "first_name",
    "apellido": "last_name",
    "rut": "perfil__rut",
    "rol": "perfil__rol",
}

# -------------------------------------------------------------------
# Utilidades
# -------------------------------------------------------------------
def _paginar(request, queryset, default_per_page: int = 10):
    """
    Devuelve (page_obj, per_page, paginator)
    """
    try:
        per_page = int(request.GET.get("per_page") or default_per_page)
    except ValueError:
        per_page = default_per_page
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return page_obj, per_page, paginator

def _aplicar_busqueda(qs, q: str):
    """
    Filtro por username, email, nombre, apellido y RUT (en Perfil).
    """
    if not q:
        return qs
    return qs.filter(
        Q(username__icontains=q)
        | Q(email__icontains=q)
        | Q(first_name__icontains=q)
        | Q(last_name__icontains=q)
        | Q(perfil__rut__icontains=q)
    )

def _aplicar_orden(qs, sort_key: str | None, direction: str | None):
    """
    Aplica ordenamiento seguro según SORT_MAP y dir asc/desc.
    """
    sort_field = SORT_MAP.get((sort_key or "").lower(), "username")
    if (direction or "").lower() == "desc":
        sort_field = f"-{sort_field}"
    return qs.order_by(sort_field)

# -------------------------------------------------------------------
# Vistas
# -------------------------------------------------------------------
@login_required
@role_required("usuarios", "view")
def lista_usuarios(request):
    """
    Lista Users con su Perfil (RUT/rol), con búsqueda, orden y paginación.
    Muestra:
      - Tabla paginada de usuarios ACTIVOS (con botón Deshabilitar).
      - Acordeón con usuarios DESHABILITADOS (con botón Restaurar).
    """
    q = (request.GET.get("q") or "").strip()
    sort = (request.GET.get("sort") or "username").strip().lower()
    dir_ = (request.GET.get("dir") or "asc").strip().lower()
    next_dir = "desc" if dir_ == "asc" else "asc"

    # Base query con perfil asociado
    base = User.objects.select_related("perfil").filter(is_superuser=False)
    base = _aplicar_busqueda(base, q)
    base = _aplicar_orden(base, sort, dir_)

    # Separamos activos/inactivos
    activos_qs = base.filter(is_active=True)
    inactivos_qs = base.filter(is_active=False)

    # Paginamos SOLO los activos (lo usual)
    page_obj, per_page, paginator = _paginar(request, activos_qs, default_per_page=10)

    ctx = {
        "page_obj": page_obj,             # activos paginados
        "per_page": per_page,
        "paginator": paginator,
        "total": base.count(),
        "q": q,
        "opciones_per_page": OPCIONES_PER_PAGE,
        "sort": sort,
        "dir": dir_,
        "next_dir": next_dir,
        "usuarios_inactivos": inactivos_qs,  # lista completa para acordeón
        "titulo": "Usuarios",
    }
    return render(request, "usuarios/lista.html", ctx)

@login_required
@role_required("usuarios", "create")
@require_http_methods(["GET", "POST"])
def crear_usuario(request):
    """
    Crea User + Perfil en transacción (lo maneja el form).
    """
    if request.method == "POST":
        form = UsuarioCrearForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Usuario «{user.username}» creado correctamente.")
            # ⬇️ redirección con el nombre del "antiguo"
            return redirect("lista_usuarios")
        messages.error(request, "Revisa los errores del formulario.")
    else:
        form = UsuarioCrearForm()

    return render(request, "usuarios/form.html", {"form": form})

@login_required
@role_required("usuarios", "edit")
def editar_usuario(request, pk: int):
    """
    Edita datos básicos del User + RUT y rol (Perfil) vía form.
    """
    user = get_object_or_404(User.objects.select_related("perfil"), pk=pk)

    if request.method == "POST":
        form = UsuarioEditarForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuario actualizado.")
            # ⬇️ redirección con el nombre del "antiguo"
            return redirect("lista_usuarios")
        messages.error(request, "Revisa los errores del formulario.")
    else:
        form = UsuarioEditarForm(instance=user)

    return render(request, "usuarios/form.html", {"form": form, "user_obj": user})

@login_required
@role_required("usuarios", "delete")
@require_http_methods(["POST", "GET"])  # permite GET si usas un enlace con confirm JS
def eliminar_usuario(request, pk: int):
    """
    Elimina el User; si Perfil tiene on_delete=CASCADE se elimina automáticamente.
    """
    user = get_object_or_404(User, pk=pk)
    username = user.username
    user.delete()
    messages.success(request, f"Usuario «{username}» eliminado.")
    # ⬇️ redirección con el nombre del "antiguo" (unificamos)
    return redirect("lista_usuarios")
@api_view(['POST'])

@csrf_exempt
def login_api(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)

    # Tu app envía "username" y "password"
    username = data.get("username") or data.get("nombre_usuario")
    password = data.get("password")

    if not username or not password:
        return JsonResponse({"success": False, "message": "Faltan credenciales"}, status=400)

    # IMPORTANTE: aunque tu USERNAME_FIELD sea 'nombre_usuario',
    # pásalo como 'username' a authenticate.
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"success": False, "message": "Credenciales inválidas"}, status=401)
    if not user.is_active:
        return JsonResponse({"success": False, "message": "Usuario inactivo"}, status=403)

    # Token (DRF authtoken)
    try:
        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=user)
        token_key = token.key
    except Exception:
        # Si no usas DRF, puedes devolver None o un token propio
        token_key = None

    return JsonResponse({
        "success": True,
        "message": "Login exitoso",
        "token": token_key
    }, status=200)
    
@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok", "time": timezone.now().isoformat()})

@csrf_exempt
def ping(request):
    return JsonResponse({"ok": True, "detail": "pong"})

@login_required
@role_required("usuarios", "edit")
@require_POST
def deshabilitar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)

    # Reglas básicas de protección
    if usuario == request.user:
        messages.warning(request, "No puedes deshabilitar tu propia cuenta.")
        return redirect("usuarios:lista")
    if usuario.is_superuser:
        messages.warning(request, "No puedes deshabilitar a un superusuario.")
        return redirect("usuarios:lista")

    if not usuario.is_active:
        messages.info(request, "El usuario ya estaba deshabilitado.")
    else:
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])
        messages.success(request, f"Usuario “{usuario.username}” deshabilitado.")
    return redirect("lista_usuarios")


@login_required
@role_required("usuarios", "edit")
@require_POST
def restaurar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)

    if usuario.is_active:
        messages.info(request, "El usuario ya estaba activo.")
    else:
        usuario.is_active = True
        usuario.save(update_fields=["is_active"])
        messages.success(request, f"Usuario “{usuario.username}” restaurado.")
    return redirect("lista_usuarios")