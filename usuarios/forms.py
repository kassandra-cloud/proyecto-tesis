# usuarios/forms.py
import re
from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.validators import RegexValidator
from django.shortcuts import get_object_or_404

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
    if not re.fullmatch(r'\d{7,8}', cuerpo):
        raise forms.ValidationError("El RUT debe tener 8 dígitos en el cuerpo.")
    dv = dv_mod11(int(cuerpo))
    rut = normalizar_rut(f"{int(cuerpo)}-{dv}")
    validar_rut(rut)
    return rut, dv


# ================== CREAR USUARIO ==================
class UsuarioCrearForm(forms.ModelForm):
    # UI extra
    rut_cuerpo = forms.CharField(label="RUT", help_text="Solo números (8 dígitos)")
    rut_dv     = forms.CharField(label="DV", required=False,
                                 widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    password1  = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2  = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput)
    rol        = forms.ChoiceField(label="Rol", choices=Perfil.Roles.choices)

    # 🔹 NUEVOS CAMPOS (se guardan en Perfil)
    apellido_paterno = forms.CharField(label="Apellido paterno", max_length=100, required=False)
    apellido_materno = forms.CharField(label="Apellido materno", max_length=100, required=False)

    # --- CAMPOS DEMOGRÁFICOS ---
    direccion = forms.CharField(label="Dirección Completa", max_length=255, required=True,
                                widget=forms.TextInput(attrs={'placeholder': 'Ej: Av. Principal 123, Depto 45'}))

    telefono = forms.CharField(label="Teléfono de Contacto", max_length=15, required=False,widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "+569XXXXXXXX"}))
    total_residentes = forms.IntegerField(label="Total Residentes", min_value=1, initial=1, required=True)
    total_ninos = forms.IntegerField(label="N° de Niños (< 12)", min_value=0, initial=0, required=True)
    
    class Meta:
        model  = User
        # quitamos last_name del form para no duplicar los apellidos
        fields = ["username", "email", "first_name"]
        labels = {"first_name": "Nombre"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Estética (Bucle Único y Corregido)
        for name in ("username", "email", "first_name",
                     "password1", "password2", "rut_cuerpo", "rut_dv",
                     "apellido_paterno", "apellido_materno",
                     "direccion", "total_residentes", "total_ninos"):
            # Usamos .get() para evitar errores si un campo no existe (aunque aquí deberían existir todos)
            if self.fields.get(name):
                self.fields[name].widget.attrs.setdefault("class", "form-control")
                self.fields["rut_cuerpo"].widget.attrs["maxlength"] = 8

        self.fields["rol"].widget.attrs.setdefault("class", "form-select")
        self.fields["username"].widget.attrs.setdefault("placeholder", "ej: kassandra")
        if self.fields.get("rut_dv"):
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

    def clean_apellido_paterno(self):
        v = (self.cleaned_data.get("apellido_paterno") or "").strip()
        if v:
            NAME_VALIDATOR(v)
        return v

    def clean_apellido_materno(self):
        v = (self.cleaned_data.get("apellido_materno") or "").strip()
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

    # ----- save atómico: User + Perfil -----
    @transaction.atomic
    def save(self, commit=True):
        if not self.cleaned_data.get("rut"):
            # Esto previene guardar si el RUT falló en clean()
            raise forms.ValidationError("No se puede guardar sin RUT válido.")

        user = super().save(commit=False)
        user.username   = self.cleaned_data["username"].strip()
        user.email      = (self.cleaned_data.get("email") or "").strip()
        user.first_name = (self.cleaned_data.get("first_name") or "").strip()

        # mantener compatibilidad con auth_user.last_name
        ap = (self.cleaned_data.get("apellido_paterno") or "").strip()
        am = (self.cleaned_data.get("apellido_materno") or "").strip()
        user.last_name  = f"{ap} {am}".strip()

        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()

        # si UNIQUE falla aquí, la transacción revierte también el user
        Perfil.objects.create(
            usuario=user,
            rol=self.cleaned_data["rol"],
            rut=self.cleaned_data["rut"],
            apellido_paterno=ap,
            apellido_materno=am,
            # --- Campos demográficos ---
            direccion=self.cleaned_data.get("direccion", "").strip(),
            telefono=self.cleaned_data['telefono'],
            total_residentes=self.cleaned_data.get("total_residentes", 1),
            total_ninos=self.cleaned_data.get("total_ninos", 0),
        )
        return user


# ================== EDITAR USUARIO ==================
class UsuarioEditarForm(forms.ModelForm):
    """
    Edita datos básicos + rol y RUT (la contraseña se cambia en otra vista).
    """
    rut_cuerpo = forms.CharField(label="RUT", help_text="Solo números (8 dígitos)")
    rut_dv     = forms.CharField(label="DV", required=False,
                                 widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    rol        = forms.ChoiceField(label="Rol", choices=Perfil.Roles.choices)

    # 🔹 NUEVOS CAMPOS
    apellido_paterno = forms.CharField(label="Apellido paterno", max_length=100, required=False)
    apellido_materno = forms.CharField(label="Apellido materno", max_length=100, required=False)

    # --- CAMPOS DEMOGRÁFICOS ---
    direccion = forms.CharField(label="Dirección Completa", max_length=255, required=True,
                                widget=forms.TextInput(attrs={'placeholder': 'Ej: Av. Principal 123, Depto 45'}))
    telefono = forms.CharField(label="Teléfono de Contacto", max_length=15, required=False,widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "+569XXXXXXXX"}))
    total_residentes = forms.IntegerField(label="Total Residentes", min_value=1, required=True)
    total_ninos = forms.IntegerField(label="N° de Niños (< 12)", min_value=0, required=True)

    class Meta:
        model  = User
        fields = ["username", "email", "first_name"]
        labels = {"first_name": "Nombre"}

    def __init__(self, *args, **kwargs):
        self.instance_user: User = kwargs.get("instance")
        super().__init__(*args, **kwargs)

        # Estética (Bucle Único y Corregido)
        # NOTA: Este bucle NO incluye 'password1' ni 'password2'
        for name in ("username", "email", "first_name", "rut_cuerpo", "rut_dv",
                     "apellido_paterno", "apellido_materno",
                     "direccion", "total_residentes", "total_ninos"):
            if self.fields.get(name):
                self.fields[name].widget.attrs.setdefault("class", "form-control")
                self.fields["rut_cuerpo"].widget.attrs["maxlength"] = 8

        self.fields["rol"].widget.attrs.setdefault("class", "form-select")
        if self.fields.get("rut_dv"):
            self.fields["rut_dv"].widget.attrs["readonly"] = "readonly"

        # Pre-cargar RUT/rol y apellidos desde Perfil
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
            # --- Pre-cargar demográficos ---
            self.fields["direccion"].initial = p.direccion
            self.fields["total_residentes"].initial = p.total_residentes
            self.fields["total_ninos"].initial = p.total_ninos


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

    def clean_apellido_paterno(self):
        v = (self.cleaned_data.get("apellido_paterno") or "").strip()
        if v:
            NAME_VALIDATOR(v)
        return v

    def clean_apellido_materno(self):
        v = (self.cleaned_data.get("apellido_materno") or "").strip()
        if v:
            NAME_VALIDATOR(v)
        return v

    # ----- form-level -----
    def clean(self):
        cleaned = super().clean()
        
        # RUT normalizado + unicidad (excluyendo el propio perfil)
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
                    self.add_error("rut_dv", "Este RUT ya está registrado.")

                cleaned["rut"] = rut
                cleaned["rut_dv"] = dv
            except forms.ValidationError as e:
                self.add_error("rut_cuerpo", e.message)

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

        ap = (self.cleaned_data.get("apellido_paterno") or "").strip()
        am = (self.cleaned_data.get("apellido_materno") or "").strip()
        user.last_name  = f"{ap} {am}".strip()  # compatibilidad con auth_user.last_name

        if commit:
            user.save()

        # Asegurar Perfil
        perfil, _ = Perfil.objects.get_or_create(usuario=user)
        perfil.rol = self.cleaned_data["rol"]
        perfil.rut = self.cleaned_data["rut"]
        perfil.apellido_paterno = ap
        perfil.apellido_materno = am
        # --- Campos demográficos ---
        perfil.direccion = self.cleaned_data.get("direccion", "").strip()
        perfil.total_residentes = self.cleaned_data.get("total_residentes", 1)
        perfil.total_ninos = self.cleaned_data.get("total_ninos", 0)
        
        perfil.save()
        return user