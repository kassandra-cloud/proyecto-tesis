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

User = get_user_model()

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
    """
    q = (request.GET.get("q") or "").strip()
    sort = (request.GET.get("sort") or "").strip().lower()
    dir_ = (request.GET.get("dir") or "asc").strip().lower()
    next_dir = "desc" if dir_ == "asc" else "asc"

    qs = User.objects.select_related("perfil")
    qs = _aplicar_busqueda(qs, q)
    qs = _aplicar_orden(qs, sort, dir_)

    page_obj, per_page, paginator = _paginar(request, qs, default_per_page=10)

    ctx = {
        "page_obj": page_obj,
        "per_page": per_page,
        "paginator": paginator,
        "total": qs.count(),
        "q": q,
        "opciones_per_page": OPCIONES_PER_PAGE,
        "sort": sort,
        "dir": dir_,
        "next_dir": next_dir,
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
