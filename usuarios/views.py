# usuarios/views.py
from __future__ import annotations

import json
from django.contrib import messages
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated  
from rest_framework.response import Response
from rest_framework import status

from core.authz import role_required
from .forms import UsuarioCrearForm, UsuarioEditarForm
from django.core.exceptions import ValidationError
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
    if request.method == 'POST':
        form = UsuarioCrearForm(request.POST)
        
        if form.is_valid():
            # 2. ENVOLVER EL GUARDADO EN UN TRY-EXCEPT
            try:
                form.save()
                messages.success(request, 'Usuario creado exitosamente')
                return redirect('lista_usuarios') # O a donde redirijas
            
            except ValidationError as e:
                # 3. ATRAPAMOS EL ERROR DEL SIGNAL
                # Esto toma el error que lanzó tu signal ("El correo ya existe...")
                # y lo pone en el campo 'email' del formulario para que se vea rojo y bonito.
                form.add_error('email', e) 
                
    else:
        form = UsuarioCrearForm()

    return render(request, 'usuarios/form.html', {'form': form})

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
            #  redirección con el nombre del "antiguo"
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
    return redirect("lista_usuarios")

# ===================================================================
#  APIs
# ===================================================================

@api_view(['POST'])
@csrf_exempt
def login_api(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)

    # 1. Recibimos el dato (Usuario O Correo)
    login_input = data.get("username") or data.get("email")
    password = data.get("password")

    if not login_input or not password:
        return JsonResponse({"success": False, "message": "Faltan credenciales"}, status=400)

    # 2. Lógica Híbrida: Detectar si es Email o Usuario
    user = None
    
    # Intento A: ¿Es un correo electrónico?
    if '@' in login_input:
        try:
            user_obj = User.objects.get(email=login_input)
            # Si existe por email, usamos su username real para autenticar
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            pass # No existe ese email
        except User.MultipleObjectsReturned:
             return JsonResponse({"success": False, "message": "Error: Correo duplicado en sistema"}, status=400)

    # Intento B: Si no funcionó arriba, probamos como username directo
    if user is None:
        user = authenticate(request, username=login_input, password=password)

    # 3. Verificaciones finales
    if user is None:
        return JsonResponse({"success": False, "message": "Credenciales inválidas"}, status=401)
    
    if not user.is_active:
        return JsonResponse({"success": False, "message": "Usuario inactivo"}, status=403)

    # Generación de token
    try:
        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=user)
        token_key = token.key
    except Exception:
        token_key = None

    # Verificar cambio de contraseña
    must_change = False
    if hasattr(user, 'perfil'):
        must_change = user.perfil.debe_cambiar_password

    # Lógica para obtener el apellido paterno preferente
    apellido_mostrar = user.last_name
    # Verificamos si tiene perfil y si este tiene apellido paterno guardado
    if hasattr(user, 'perfil') and user.perfil.apellido_paterno:
        apellido_mostrar = user.perfil.apellido_paterno

    # RESPUESTA FINAL CON DATOS DEL USUARIO
    return JsonResponse({
        "success": True,
        "message": "Login exitoso",
        "token": token_key,
        "must_change_password": must_change,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": apellido_mostrar # <--- Enviamos el apellido paterno real
        }
    }, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cambiar_password_inicial(request):
    """
    Endpoint para cambiar la contraseña obligatoria (Onboarding).
    Espera JSON: { "new_password": "..." }
    """
    new_password = request.data.get("new_password")
    
    # Validaciones básicas
    if not new_password:
        return Response({"error": "La contraseña es requerida"}, status=400)
    
    if len(new_password) < 14:
         return Response({"error": "La contraseña debe tener al menos 12 caracteres"}, status=400)

    user = request.user
    user.set_password(new_password)
    user.save()
    
    # Lógica para obtener el nombre (esto es correcto)
    full_name = user.get_full_name().strip()
    display_name = full_name if full_name else user.username
    
    # Determinar el mensaje de éxito (esto es correcto)
    success_message = f"¡Bienvenido(a) {display_name}, tu contraseña ha sido actualizada correctamente!"
    
    # Actualizar bandera en perfil
    if hasattr(user, 'perfil'):
        user.perfil.debe_cambiar_password = False
        user.perfil.save()
        
    # CORRECCIÓN: Usar la variable 'success_message' en la respuesta
    return Response({"success": True, "message": success_message})

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
        return redirect("lista_usuarios")
    if usuario.is_superuser:
        messages.warning(request, "No puedes deshabilitar a un superusuario.")
        return redirect("lista_usuarios")

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

@login_required
def api_usuarios_by_role(request):
    """
    Devuelve JSON con usuarios activos (con email) filtrados por rol del Perfil.
    GET /usuarios/api/usuarios/by-role/?role=vecino
    role = "ALL" o vacío -> todos.
    """
    role = (request.GET.get("role") or "").strip()
    qs = (
        User.objects.filter(is_active=True)
        .exclude(email__isnull=True)
        .exclude(email__exact="")
        .exclude(is_superuser=True)  # mantiene tu criterio actual
        .select_related("perfil")
        .order_by("first_name", "last_name", "email")
    )
    if role and role.upper() != "ALL":
        qs = qs.filter(perfil__rol=role)

    data = [
        {
            "id": u.id,
            "name": (u.get_full_name() or u.username).strip(),
            "email": u.email,
        }
        for u in qs
    ]
    return JsonResponse({"results": data})