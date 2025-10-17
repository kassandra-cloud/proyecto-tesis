# usuarios/forms.py
import re
from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.validators import RegexValidator

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

def _validar_password_fuerte(pw: str):
    if len(pw) < 12:
        raise forms.ValidationError("La contraseña debe tener al menos 12 caracteres.")
    if not re.search(r'[a-z]', pw):
        raise forms.ValidationError("Debe incluir al menos una minúscula.")
    if not re.search(r'[A-Z]', pw):
        raise forms.ValidationError("Debe incluir al menos una mayúscula.")
    if not re.search(r'[^A-Za-z0-9]', pw):
        raise forms.ValidationError("Debe incluir al menos un símbolo.")

def _armar_rut_desde_cuerpo(cuerpo_str: str) -> tuple[str, str]:
    """
    Recibe solo el cuerpo (7–9 dígitos) y retorna (rut_normalizado, dv).
    """
    cuerpo = (cuerpo_str or "").replace(".", "").replace(" ", "")
    if not re.fullmatch(r'\d{7,9}', cuerpo):
        raise forms.ValidationError("El RUT debe tener 7 a 9 dígitos en el cuerpo.")
    dv = dv_mod11(int(cuerpo))
    rut = normalizar_rut(f"{int(cuerpo)}-{dv}")
    validar_rut(rut)
    return rut, dv


# ================== CREAR USUARIO ==================
class UsuarioCrearForm(forms.ModelForm):
    # UI extra
    rut_cuerpo = forms.CharField(label="RUT", help_text="Solo números (7–9 dígitos)")
    rut_dv     = forms.CharField(label="DV", required=False,
                                 widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    password1  = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2  = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput)
    rol        = forms.ChoiceField(label="Rol", choices=Perfil.Roles.choices)

    class Meta:
        model  = User
        fields = ["username", "email", "first_name", "last_name"]
        labels = {"first_name": "Nombre", "last_name": "Apellido"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Estética
        for name in ("username","email","first_name","last_name",
                     "password1","password2","rut_cuerpo","rut_dv"):
            self.fields[name].widget.attrs.setdefault("class", "form-control")
        self.fields["rol"].widget.attrs.setdefault("class", "form-select")
        self.fields["username"].widget.attrs.setdefault("placeholder", "ej: kassandra")
        self.fields["rut_dv"].widget.attrs["readonly"] = "readonly"

    # ----- field-level -----
    def clean_username(self):
        u = (self.cleaned_data.get("username") or "").strip()
        if " " in u:
            raise forms.ValidationError("El nombre de usuario no puede tener espacios.")
        USERNAME_VALIDATOR(u)
        if User.objects.filter(username__iexact=u).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return u

    def clean_first_name(self):
        v = (self.cleaned_data.get("first_name") or "").strip()
        if v:
            NAME_VALIDATOR(v)
        return v

    def clean_last_name(self):
        v = (self.cleaned_data.get("last_name") or "").strip()
        if v:
            NAME_VALIDATOR(v)
        return v

    # ----- form-level -----
    def clean(self):
        cleaned = super().clean()

        # Password fuerte + coinciden
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2:
            if p1 != p2:
                raise forms.ValidationError("Las contraseñas no coinciden.")
            _validar_password_fuerte(p1)

        # RUT normalizado + unicidad
        rut, dv = _armar_rut_desde_cuerpo(cleaned.get("rut_cuerpo"))
        if Perfil.objects.filter(rut__iexact=rut).exists():
            self.add_error("rut_cuerpo", "Este RUT ya está registrado.")
            self.add_error("rut_dv", "Este RUT ya está registrado.")
            raise forms.ValidationError("RUT duplicado.")

        cleaned["rut"] = rut
        cleaned["rut_dv"] = dv
        return cleaned

    # ----- save atómico: User + Perfil -----
    @transaction.atomic
    def save(self, commit=True):
        if not self.cleaned_data.get("rut"):
            raise forms.ValidationError("No se puede guardar sin RUT válido.")

        user = super().save(commit=False)
        user.username   = self.cleaned_data["username"].strip()
        user.email      = (self.cleaned_data.get("email") or "").strip()
        user.first_name = (self.cleaned_data.get("first_name") or "").strip()
        user.last_name  = (self.cleaned_data.get("last_name") or "").strip()
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()

        # si UNIQUE falla aquí, la transacción revierte también el user
        Perfil.objects.create(
            usuario=user,
            rol=self.cleaned_data["rol"],
            rut=self.cleaned_data["rut"],
        )
        return user


# ================== EDITAR USUARIO ==================
class UsuarioEditarForm(forms.ModelForm):
    """
    Edita datos básicos + rol y RUT (la contraseña se cambia en otra vista).
    """
    rut_cuerpo = forms.CharField(label="RUT", help_text="Solo números (7–9 dígitos)")
    rut_dv     = forms.CharField(label="DV", required=False,
                                 widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    rol        = forms.ChoiceField(label="Rol", choices=Perfil.Roles.choices)

    class Meta:
        model  = User
        fields = ["username", "email", "first_name", "last_name"]
        labels = {"first_name": "Nombre", "last_name": "Apellido"}

    def __init__(self, *args, **kwargs):
        self.instance_user: User = kwargs.get("instance")
        super().__init__(*args, **kwargs)

        # Estética
        for name in ("username","email","first_name","last_name","rut_cuerpo","rut_dv"):
            self.fields[name].widget.attrs.setdefault("class", "form-control")
        self.fields["rol"].widget.attrs.setdefault("class", "form-select")
        self.fields["rut_dv"].widget.attrs["readonly"] = "readonly"

        # Pre-cargar RUT y rol desde Perfil
        if self.instance_user and hasattr(self.instance_user, "perfil"):
            rut = self.instance_user.perfil.rut or ""
            if "-" in rut:
                cuerpo, dv = rut.split("-", 1)
                self.fields["rut_cuerpo"].initial = cuerpo
                self.fields["rut_dv"].initial = dv
            self.fields["rol"].initial = self.instance_user.perfil.rol

    # ----- field-level -----
    def clean_username(self):
        u = (self.cleaned_data.get("username") or "").strip()
        if " " in u:
            raise forms.ValidationError("El nombre de usuario no puede tener espacios.")
        USERNAME_VALIDATOR(u)
        qs = User.objects.filter(username__iexact=u)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return u

    def clean_first_name(self):
        v = (self.cleaned_data.get("first_name") or "").strip()
        if v:
            NAME_VALIDATOR(v)
        return v

    def clean_last_name(self):
        v = (self.cleaned_data.get("last_name") or "").strip()
        if v:
            NAME_VALIDATOR(v)
        return v

    # ----- form-level -----
    def clean(self):
        cleaned = super().clean()
        # RUT normalizado + unicidad (excluyendo el propio perfil)
        rut, dv = _armar_rut_desde_cuerpo(cleaned.get("rut_cuerpo"))
        qs = Perfil.objects.filter(rut__iexact=rut)

        # <<< ARREGLO: no usar perfil_id; obtener pk del perfil de forma segura >>>
        perfil_pk = getattr(getattr(self.instance_user, "perfil", None), "pk", None)
        if perfil_pk:
            qs = qs.exclude(pk=perfil_pk)

        if qs.exists():
            self.add_error("rut_cuerpo", "Este RUT ya está registrado.")
            self.add_error("rut_dv", "Este RUT ya está registrado.")
            raise forms.ValidationError("RUT duplicado.")

        cleaned["rut"] = rut
        cleaned["rut_dv"] = dv
        return cleaned

    # ----- save atómico: User + Perfil -----
    @transaction.atomic
    def save(self, commit=True):
        if not self.cleaned_data.get("rut"):
            raise forms.ValidationError("No se puede guardar sin RUT válido.")

        user = super().save(commit=False)
        # Normalizar campos básicos
        user.username   = (self.cleaned_data.get("username") or "").strip()
        user.email      = (self.cleaned_data.get("email") or "").strip()
        user.first_name = (self.cleaned_data.get("first_name") or "").strip()
        user.last_name  = (self.cleaned_data.get("last_name") or "").strip()

        if commit:
            user.save()

        # Asegurar Perfil
        perfil, _ = Perfil.objects.get_or_create(usuario=user)
        perfil.rol = self.cleaned_data["rol"]
        perfil.rut = self.cleaned_data["rut"]
        perfil.save()
        return user
