# usuarios/forms.py
import re
import secrets
import string
from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.validators import RegexValidator
from django.core.mail import send_mail
from django.conf import settings

from core.models import Perfil
from core.rut import normalizar_rut, dv_mod11, validar_rut

User = get_user_model()

# ------------------ Validadores reutilizables ------------------
USERNAME_VALIDATOR = RegexValidator(
    regex=r'^[\w.@+-]+$',
    message='Usa solo letras, números y @/./+/-/_',
)

NAME_VALIDATOR = RegexValidator(
    regex=r'^[A-Za-zÁÉÍÓÚÑáéíóúñ ]*$',
    message='Solo letras y espacios.',
)


def _armar_rut_desde_cuerpo(cuerpo_str: str) -> tuple[str, str]:
    cuerpo = (cuerpo_str or "").replace(".", "").replace(" ", "")
    if not re.fullmatch(r'\d{7,8}', cuerpo):
        raise forms.ValidationError("El RUT debe tener 8 dígitos en el cuerpo.")
    dv = dv_mod11(int(cuerpo))
    rut = normalizar_rut(f"{int(cuerpo)}-{dv}")
    validar_rut(rut)
    return rut, dv


# ================== CREAR USUARIO ==================
class UsuarioCrearForm(forms.ModelForm):
    # Nombre: misma lógica que apellidos (solo letras y espacios)
    first_name = forms.CharField(
        label="Nombre",
        max_length=150,
        required=True,
        validators=[NAME_VALIDATOR],
    )

    # UI extra para RUT
    rut_cuerpo = forms.CharField(label="RUT", help_text="Solo números (8 dígitos)")
    rut_dv     = forms.CharField(
        label="DV",
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'})
    )
    
    rol = forms.ChoiceField(label="Rol", choices=Perfil.Roles.choices)

    # Apellidos obligatorios + NAME_VALIDATOR
    apellido_paterno = forms.CharField(
        label="Apellido paterno",
        max_length=100,
        required=True,
        validators=[NAME_VALIDATOR],
    )
    apellido_materno = forms.CharField(
        label="Apellido materno",
        max_length=100,
        required=True,
        validators=[NAME_VALIDATOR],
    )

    # --- CAMPOS DEMOGRÁFICOS ---
    direccion = forms.CharField(
        label="Nombre de la Calle/Pasaje",
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Av. Principal, Pasaje 5'})
    )
    
    numero_casa = forms.CharField(
        label="N° Casa/Depto/Lote",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Ej: 123, Dpto 45, Lote B'})
    )
    
    telefono = forms.CharField(
        label="Teléfono de Contacto", 
        max_length=8,  # solo los 8 dígitos
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control", 
            "placeholder": "12345678", 
            "type": "number",
            "maxlength": "8"
        })
    )

    total_residentes = forms.IntegerField(
        label="Total Residentes",
        min_value=1,
        initial=1,
        required=True
    )
    
    total_ninos = forms.IntegerField(
        label="N° de Niños (< 12)",
        min_value=0,
        initial=0,
        required=False
    )
    
    class Meta:
        model  = User
        fields = ["username", "email", "first_name"]
        labels = {"first_name": "Nombre"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Estética general
        for name in (
            "username", "email", "first_name",
            "rut_cuerpo", "rut_dv",
            "apellido_paterno", "apellido_materno",
            "direccion", "numero_casa",
            "telefono", "total_residentes", "total_ninos"
        ):
            if self.fields.get(name):
                self.fields[name].widget.attrs.setdefault("class", "form-control")
                if name in ["rut_cuerpo", "telefono"]:
                    self.fields[name].widget.attrs["maxlength"] = "8"

        self.fields["rol"].widget.attrs.setdefault("class", "form-select")
        self.fields["username"].widget.attrs.setdefault("placeholder", "ej: kassandra")
        if self.fields.get("rut_dv"):
            self.fields["rut_dv"].widget.attrs["readonly"] = "readonly"

    # ----- VALIDACIÓN TELÉFONO (+569) -----
    def clean_telefono(self):
        data = self.cleaned_data.get('telefono')
        if not data:
            return None 
        
        data = data.strip()
        if not data.isdigit():
            raise forms.ValidationError("El teléfono debe contener solo números.")
        
        if len(data) != 8:
            raise forms.ValidationError("Debe ingresar exactamente 8 dígitos (sin el +569).")

        return f"+569{data}"

    # ----- VALIDACIÓN USERNAME -----
    def clean_username(self):
        u = (self.cleaned_data.get("username") or "").strip()
        if " " in u:
            raise forms.ValidationError("El nombre de usuario no puede tener espacios.")
        
        if User.objects.filter(username__iexact=u).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return u

    # ----- CLEAN FORM -----
    def clean(self):
        cleaned = super().clean()

        # RUT normalizado + unicidad
        cuerpo_rut = cleaned.get("rut_cuerpo")
        if cuerpo_rut:
            try:
                rut, dv = _armar_rut_desde_cuerpo(cuerpo_rut)
                if Perfil.objects.filter(rut__iexact=rut).exists():
                    self.add_error("rut_cuerpo", "Este RUT ya está registrado.")
                    self.add_error("rut_dv", "Este RUT ya está registrado.")
                cleaned["rut"] = rut
                cleaned["rut_dv"] = dv
            except forms.ValidationError as e:
                self.add_error("rut_cuerpo", e.message)
        
        return cleaned

    # ----- SAVE: User + Perfil + Email -----
    @transaction.atomic
    def save(self, commit=True):
        if not self.cleaned_data.get("rut"):
            raise forms.ValidationError("No se puede guardar sin RUT válido.")

        user = super().save(commit=False)
        user.username   = self.cleaned_data["username"].strip()
        user.email      = (self.cleaned_data.get("email") or "").strip()
        user.first_name = (self.cleaned_data.get("first_name") or "").strip().title()

        ap = (self.cleaned_data.get("apellido_paterno") or "").strip().title()
        am = (self.cleaned_data.get("apellido_materno") or "").strip().title()
        user.last_name  = f"{ap} {am}".strip()

        # GENERACIÓN DE CONTRASEÑA
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        while True:
            password_provisoria = ''.join(secrets.choice(alphabet) for _ in range(12))
            if (any(c.islower() for c in password_provisoria) and 
                any(c.isupper() for c in password_provisoria) and 
                any(c in "!@#$%^&*" for c in password_provisoria)):
                break
        
        user.set_password(password_provisoria)

        if commit:
            user.save()

        # Crear Perfil
        Perfil.objects.create(
            usuario=user,
            rol=self.cleaned_data["rol"],
            rut=self.cleaned_data["rut"],
            apellido_paterno=ap,
            apellido_materno=am,
            direccion=self.cleaned_data.get("direccion", "").strip(),
            numero_casa=self.cleaned_data.get("numero_casa", "").strip(),
            telefono=self.cleaned_data['telefono'],  # Ya viene con +569
            total_residentes=self.cleaned_data.get("total_residentes", 1),
            total_ninos=self.cleaned_data.get("total_ninos") or 0,
            debe_cambiar_password=True
        )

        # ENVIAR CORREO
        if user.email:
            asunto = "Bienvenido a la Comunidad - Tus credenciales"
            mensaje = f"""
Hola {user.first_name},

Tu cuenta ha sido creada exitosamente.

Usuario: {user.username}
Contraseña temporal: {password_provisoria}

IMPORTANTE:
Por tu seguridad, la aplicación te pedirá cambiar esta contraseña 
automáticamente la primera vez que inicies sesión.
"""
            try:
                send_mail(asunto, mensaje, settings.EMAIL_HOST_USER, [user.email], fail_silently=False)
            except Exception as e:
                print(f"Error enviando correo al usuario {user.username}: {e}")

        return user


# ================== EDITAR USUARIO ==================
class UsuarioEditarForm(forms.ModelForm):
    # Nombre con mismo validador
    first_name = forms.CharField(
        label="Nombre",
        max_length=150,
        required=True,
        validators=[NAME_VALIDATOR],
    )

    rut_cuerpo = forms.CharField(label="RUT", help_text="Solo números (8 dígitos)")
    rut_dv     = forms.CharField(
        label="DV",
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'})
    )
    rol = forms.ChoiceField(label="Rol", choices=Perfil.Roles.choices)

    apellido_paterno = forms.CharField(
        label="Apellido paterno",
        max_length=100,
        required=True,
        validators=[NAME_VALIDATOR],
    )
    apellido_materno = forms.CharField(
        label="Apellido materno",
        max_length=100,
        required=True,
        validators=[NAME_VALIDATOR],
    )

    direccion = forms.CharField(
        label="Nombre de la Calle/Pasaje",
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Av. Principal, Pasaje 5'})
    )
    
    numero_casa = forms.CharField(
        label="N° Casa/Depto/Lote",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Ej: 123, Dpto 45, Lote B'})
    )
    
    telefono = forms.CharField(
        label="Teléfono de Contacto", 
        max_length=8, 
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "12345678",
            "type": "number",
            "maxlength": "8"
        })
    )

    total_residentes = forms.IntegerField(
        label="Total Residentes",
        min_value=1,
        required=True
    )
    
    total_ninos = forms.IntegerField(
        label="N° de Niños (< 12)",
        min_value=0,
        required=False
    )

    class Meta:
        model  = User
        fields = ["username", "email", "first_name"]
        labels = {"first_name": "Nombre"}

    def __init__(self, *args, **kwargs):
        self.instance_user: User = kwargs.get("instance")  # type: ignore
        super().__init__(*args, **kwargs)

        # Estética
        for name in (
            "username", "email", "first_name",
            "rut_cuerpo", "rut_dv",
            "apellido_paterno", "apellido_materno",
            "direccion", "numero_casa",
            "telefono", "total_residentes", "total_ninos"
        ):
            if self.fields.get(name):
                self.fields[name].widget.attrs.setdefault("class", "form-control")
                if name in ["rut_cuerpo", "telefono"]:
                    self.fields[name].widget.attrs["maxlength"] = "8"

        self.fields["rol"].widget.attrs.setdefault("class", "form-select")
        if self.fields.get("rut_dv"):
            self.fields["rut_dv"].widget.attrs["readonly"] = "readonly"

        # Pre-cargar desde Perfil
        if self.instance_user and hasattr(self.instance_user, "perfil"):
            p = self.instance_user.perfil
            rut = p.rut or ""
            if "-" in rut:
                cuerpo, dv = rut.split("-", 1)
                self.fields["rut_cuerpo"].initial = cuerpo
                self.fields["rut_dv"].initial = dv

            self.fields["rol"].initial = p.rol
            self.fields["apellido_paterno"].initial = p.apellido_paterno
            self.fields["apellido_materno"].initial = p.apellido_materno
            
            self.fields["direccion"].initial = p.direccion
            self.fields["numero_casa"].initial = p.numero_casa
            self.fields["total_residentes"].initial = p.total_residentes
            self.fields["total_ninos"].initial = p.total_ninos
            
            # Quitar +569 visualmente al editar
            fono = p.telefono or ""
            if fono.startswith("+569"):
                self.fields["telefono"].initial = fono[4:]
            else:
                self.fields["telefono"].initial = fono

    # ----- VALIDACIÓN TELÉFONO -----
    def clean_telefono(self):
        data = self.cleaned_data.get('telefono')
        if not data:
            return None
        
        data = data.strip()
        if not data.isdigit():
            raise forms.ValidationError("El teléfono debe contener solo números.")
        if len(data) != 8:
            raise forms.ValidationError("Debe ingresar exactamente 8 dígitos.")
        return f"+569{data}"

    def clean_username(self):
        u = (self.cleaned_data.get("username") or "").strip()
        if " " in u:
            raise forms.ValidationError("El nombre de usuario no puede tener espacios.")
        if User.objects.filter(username__iexact=u).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return u

    def clean(self):
        cleaned = super().clean()
        cuerpo_rut = cleaned.get("rut_cuerpo")
        if cuerpo_rut:
            try:
                rut, dv = _armar_rut_desde_cuerpo(cuerpo_rut)
                qs = Perfil.objects.filter(rut__iexact=rut)
                perfil_pk = getattr(getattr(self.instance_user, "perfil", None), "pk", None)
                if perfil_pk:
                    qs = qs.exclude(pk=perfil_pk)
                if qs.exists():
                    self.add_error("rut_cuerpo", "Este RUT ya está registrado.")
                cleaned["rut"] = rut
            except forms.ValidationError as e:
                self.add_error("rut_cuerpo", e.message)
        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        if not self.cleaned_data.get("rut"):
            raise forms.ValidationError("No se puede guardar sin RUT válido.")
        user = super().save(commit=False)
        user.username   = (self.cleaned_data.get("username") or "").strip()
        user.email      = (self.cleaned_data.get("email") or "").strip()
        user.first_name = (self.cleaned_data.get("first_name") or "").strip().title()

        ap = (self.cleaned_data.get("apellido_paterno") or "").strip().title()
        am = (self.cleaned_data.get("apellido_materno") or "").strip().title()
        user.last_name  = f"{ap} {am}".strip()

        if commit:
            user.save()

        perfil, _ = Perfil.objects.get_or_create(usuario=user)
        perfil.rol = self.cleaned_data["rol"]
        perfil.rut = self.cleaned_data["rut"]
        perfil.apellido_paterno = ap
        perfil.apellido_materno = am
        perfil.direccion = self.cleaned_data.get("direccion", "").strip()
        perfil.numero_casa = self.cleaned_data.get("numero_casa", "").strip()
        perfil.total_residentes = self.cleaned_data.get("total_residentes", 1)
        perfil.total_ninos = self.cleaned_data.get("total_ninos") or 0
        
        perfil.telefono = self.cleaned_data['telefono']  # ya incluye +569
        
        perfil.save()
        return user
