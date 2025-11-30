# usuarios/views.py
from __future__ import annotations

import json
import random
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, authenticate, login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.password_validation import validate_password  # <--- AGREGAR ESTA LÍNEA


from core.authz import role_required
from core.models import Perfil
from .forms import UsuarioCrearForm, UsuarioEditarForm

User = get_user_model()

# -------------------------------------------------------------------
# Configuración
# -------------------------------------------------------------------
OPCIONES_PER_PAGE = [10, 25, 50]

# Mapa de columnas permitidas en sort -> field de ORM
SORT_MAP = {
    "username": "username",
    "email": "email",
    "nombre": "first_name",
    "apellido": "last_name",
    "rut": "perfil__rut",
    "rol": "perfil__rol",
}

# -------------------------------------------------------------------
# Utilidades Internas
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
# Vistas de Gestión de Usuarios (Web)
# -------------------------------------------------------------------
@login_required
@role_required("usuarios", "view")
def lista_usuarios(request):
    """
    Lista Users con su Perfil (RUT/rol), con búsqueda, orden y paginación.
    """
    q = (request.GET.get("q") or "").strip()
    sort = (request.GET.get("sort") or "username").strip().lower()
    dir_ = (request.GET.get("dir") or "asc").strip().lower()
    next_dir = "desc" if dir_ == "asc" else "asc"

    base = User.objects.select_related("perfil").filter(is_superuser=False)
    base = _aplicar_busqueda(base, q)
    base = _aplicar_orden(base, sort, dir_)

    activos_qs = base.filter(is_active=True)
    inactivos_qs = base.filter(is_active=False)

    page_obj, per_page, paginator = _paginar(request, activos_qs, default_per_page=10)

    ctx = {
        "page_obj": page_obj,
        "per_page": per_page,
        "paginator": paginator,
        "total": base.count(),
        "q": q,
        "opciones_per_page": OPCIONES_PER_PAGE,
        "sort": sort,
        "dir": dir_,
        "next_dir": next_dir,
        "usuarios_inactivos": inactivos_qs,
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
            try:
                form.save()
                messages.success(request, 'Usuario creado exitosamente')
                return redirect('lista_usuarios')
            except ValidationError as e:
                form.add_error('email', e) 
    else:
        form = UsuarioCrearForm()

    return render(request, 'usuarios/form.html', {'form': form})

@login_required
@role_required("usuarios", "edit")
def editar_usuario(request, pk: int):
    user = get_object_or_404(User.objects.select_related("perfil"), pk=pk)

    if request.method == "POST":
        form = UsuarioEditarForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuario actualizado.")
            return redirect("lista_usuarios")
        messages.error(request, "Revisa los errores del formulario.")
    else:
        form = UsuarioEditarForm(instance=user)

    return render(request, "usuarios/form.html", {"form": form, "user_obj": user})

@login_required
@role_required("usuarios", "delete")
@require_http_methods(["POST", "GET"])
def eliminar_usuario(request, pk: int):
    user = get_object_or_404(User, pk=pk)
    username = user.username
    user.delete()
    messages.success(request, f"Usuario «{username}» eliminado.")
    return redirect("lista_usuarios")

@login_required
@role_required("usuarios", "edit")
@require_POST
def deshabilitar_usuario(request, pk):
    usuario_a_bloquear = get_object_or_404(User, pk=pk)

    # 1. PROTECCIÓN: No bloquearse a sí mismo
    if usuario_a_bloquear == request.user:
        messages.warning(request, "No puedes deshabilitar tu propia cuenta.")
        return redirect("lista_usuarios")

    # 2. PROTECCIÓN: No bloquear a Superusuarios
    if usuario_a_bloquear.is_superuser:
        messages.warning(request, "No puedes deshabilitar a un superusuario.")
        return redirect("lista_usuarios")

    # 3. PROTECCIÓN: No bloquear a otros Presidentes
    if hasattr(usuario_a_bloquear, 'perfil') and usuario_a_bloquear.perfil.rol == Perfil.Roles.PRESIDENTE:
        messages.error(request, "No tienes permisos para deshabilitar a otro Presidente.")
        return redirect("lista_usuarios")

    # Lógica
    if not usuario_a_bloquear.is_active:
        messages.info(request, "El usuario ya estaba deshabilitado.")
    else:
        usuario_a_bloquear.is_active = False
        usuario_a_bloquear.save(update_fields=["is_active"])
        messages.success(request, f"Usuario “{usuario_a_bloquear.username}” deshabilitado correctamente.")
        
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

# -------------------------------------------------------------------
# APIs (Para App Móvil)
# -------------------------------------------------------------------

@api_view(['POST'])
@csrf_exempt
def login_api(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)

    login_input = data.get("username") or data.get("email")
    password = data.get("password")

    if not login_input or not password:
        return JsonResponse({"success": False, "message": "Faltan credenciales"}, status=400)

    user = None
    # Intento A: Email
    if '@' in login_input:
        try:
            user_obj = User.objects.get(email=login_input)
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            pass
        except User.MultipleObjectsReturned:
             return JsonResponse({"success": False, "message": "Error: Correo duplicado en sistema"}, status=400)

    # Intento B: Username
    if user is None:
        user = authenticate(request, username=login_input, password=password)

    if user is None:
        return JsonResponse({"success": False, "message": "Credenciales inválidas"}, status=401)
    
    if not user.is_active:
        return JsonResponse({"success": False, "message": "Usuario inactivo"}, status=403)

    try:
        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=user)
        token_key = token.key
    except Exception:
        token_key = None

    must_change = False
    if hasattr(user, 'perfil'):
        must_change = user.perfil.debe_cambiar_password

    apellido_mostrar = user.last_name
    if hasattr(user, 'perfil') and user.perfil.apellido_paterno:
        apellido_mostrar = user.perfil.apellido_paterno

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
            "last_name": apellido_mostrar
        }
    }, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cambiar_password_inicial(request):
    """
    Endpoint para cambiar la contraseña obligatoria (Onboarding App).
    """
    new_password = request.data.get("new_password")
    
    if not new_password:
        return Response({"error": "La contraseña es requerida"}, status=400)
    if len(new_password) < 14:
         return Response({"error": "La contraseña debe tener al menos 14 caracteres"}, status=400)

    user = request.user
    user.set_password(new_password)
    user.save()
    
    full_name = user.get_full_name().strip()
    display_name = full_name if full_name else user.username
    success_message = f"¡Bienvenido(a) {display_name}, tu contraseña ha sido actualizada correctamente!"
    
    if hasattr(user, 'perfil'):
        user.perfil.debe_cambiar_password = False
        user.perfil.save()
        
    return Response({"success": True, "message": success_message})

@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok", "time": timezone.now().isoformat()})

@csrf_exempt
def ping(request):
    return JsonResponse({"ok": True, "detail": "pong"})

@login_required
def api_usuarios_by_role(request):
    """
    API interna para selectores dinámicos en la web.
    """
    role = (request.GET.get("role") or "").strip()
    qs = (
        User.objects.filter(is_active=True)
        .exclude(email__isnull=True)
        .exclude(email__exact="")
        .exclude(is_superuser=True)
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

# -------------------------------------------------------------------
# Flujos de Seguridad Web (Passwords)
# -------------------------------------------------------------------

@login_required
def cambiar_password_obligatorio(request):
    """
    Vista forzada por el Middleware cuando debe_cambiar_password es True.
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # 1. Mantener sesión activa
            update_session_auth_hash(request, user)
            
            # 2. Apagar bandera
            if hasattr(user, 'perfil'):
                user.perfil.debe_cambiar_password = False
                user.perfil.save()
                
            messages.success(request, '¡Tu contraseña ha sido actualizada exitosamente!')
            return redirect('home')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'usuarios/cambiar_password_obligatorio.html', {'form': form})

# --- RECUPERACIÓN DE CONTRASEÑA CON CÓDIGO (WEB) ---

def web_recuperar_paso1(request):
    """Paso 1: Solicitar correo y enviar código OTP"""
    if request.method == 'POST':
        email = request.POST.get('email')
        
        user = User.objects.filter(email__iexact=email).first()
        
        if user:
            # 1. Generar Código
            codigo = str(random.randint(100000, 999999))
            
            # 2. Guardar en Perfil
            if hasattr(user, 'perfil'):
                perfil = user.perfil
                perfil.recovery_code = codigo
                # Expira en 15 minutos
                perfil.recovery_code_expires = timezone.now() + timedelta(minutes=15)
                perfil.save()
                
                # 3. Enviar Correo
                html_message = render_to_string('registration/email_codigo_otp.html', {
                    'user': user,
                    'codigo': codigo
                })
                plain_message = strip_tags(html_message)
                
                send_mail(
                    subject='Código de Recuperación - Junta de Vecinos',
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=True
                )
                
                # Guardamos el email en sesión
                request.session['recuperar_email'] = user.email
                messages.success(request, f"Código enviado a {user.email}")
                return redirect('web_recuperar_paso2')
            else:
                messages.error(request, "El usuario no tiene un perfil asociado.")
        else:
            messages.error(request, "No encontramos una cuenta con ese correo.")

    return render(request, 'registration/recuperar_paso1.html')

def web_recuperar_paso2(request):
    """Paso 2: Ingresar código OTP y nueva contraseña (CON VALIDACIONES)"""
    email_session = request.session.get('recuperar_email')
    
    if not email_session:
        messages.error(request, "Sesión expirada, inicia el proceso nuevamente.")
        return redirect('web_recuperar_paso1')

    if request.method == 'POST':
        codigo_ingresado = request.POST.get('codigo')
        pass1 = request.POST.get('pass1')
        pass2 = request.POST.get('pass2')

        user = User.objects.filter(email__iexact=email_session).first()

        # 1. Validaciones básicas de usuario y sesión
        if not user:
            return redirect('web_recuperar_paso1')
            
        # 2. Validación de Código OTP
        if not hasattr(user, 'perfil') or user.perfil.recovery_code != codigo_ingresado:
            messages.error(request, "El código ingresado es incorrecto.")
            return render(request, 'registration/recuperar_paso2.html', {'email': email_session})
            
        if user.perfil.recovery_code_expires and user.perfil.recovery_code_expires < timezone.now():
            messages.error(request, "El código ha expirado. Por favor solicita uno nuevo.")
            return render(request, 'registration/recuperar_paso2.html', {'email': email_session})

        # 3. Validación de coincidencia de contraseñas
        if pass1 != pass2:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, 'registration/recuperar_paso2.html', {'email': email_session})

        # 4. VALIDACIÓN DE SEGURIDAD DE DJANGO (Lo nuevo)
        try:
            # Esto chequea largo mínimo (14), similitud con usuario, password común, etc.
            validate_password(pass1, user=user)
        except ValidationError as e:
            # Si falla, mostramos cada error que Django encontró
            for error in e.messages:
                messages.error(request, error)
            return render(request, 'registration/recuperar_paso2.html', {'email': email_session})

        # --- SI LLEGA AQUÍ, TODO ESTÁ CORRECTO ---
        
        # Guardar contraseña
        user.set_password(pass1)
        user.save()
        
        # Limpiar código usado
        user.perfil.recovery_code = None
        user.perfil.recovery_code_expires = None
        
        # Apagar cambio obligatorio (ya la cambió voluntariamente)
        user.perfil.debe_cambiar_password = False 
        user.perfil.save()
        
        # Limpiar sesión temporal
        del request.session['recuperar_email']
        
        messages.success(request, "¡Contraseña restablecida exitosamente! Ya puedes iniciar sesión.")
        return redirect('login')

    return render(request, 'registration/recuperar_paso2.html', {'email': email_session})