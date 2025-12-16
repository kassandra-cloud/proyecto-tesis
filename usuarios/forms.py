# usuarios/forms.py
import re
import secrets
import string

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from core.models import Perfil
from core.rut import normalizar_rut, dv_mod11, validar_rut
from usuarios.utils import enviar_correo_via_webhook

User = get_user_model()

# ------------------ Validadores reutilizables ------------------
USERNAME_VALIDATOR = RegexValidator(
    regex=r"^[\w.@+-]+$",
    message="Usa solo letras, números y @/./+/-/_",
)

# ✅ Solo letras (incluye acentos, Ñ) y espacios
NAME_VALIDATOR = RegexValidator(
    regex=r"^[A-Za-zÁÉÍÓÚÑáéíóúñ ]*$",
    message="Solo letras y espacios.",
)

# ✅ Calle/Pasaje: letras + espacios + puntos + comas (SIN números)
# Ej: "Av. Principal", "Pasaje Los Pinos", "Calle San Martín"
DIRECCION_VALIDATOR = RegexValidator(
    regex=r"^[A-Za-zÁÉÍÓÚÑáéíóúñ\s\.,\-°#]*$",
    message="La dirección solo puede contener letras y caracteres básicos (sin números).",
)

def _armar_rut_desde_cuerpo(cuerpo_str: str) -> tuple[str, str]:
    cuerpo = (cuerpo_str or "").replace(".", "").replace(" ", "")
    if not re.fullmatch(r"\d{7,8}", cuerpo):
        raise forms.ValidationError("El RUT debe tener 7 u 8 dígitos en el cuerpo.")
    dv = dv_mod11(int(cuerpo))
    rut = normalizar_rut(f"{int(cuerpo)}-{dv}")
    validar_rut(rut)
    return rut, dv


# ================== CREAR USUARIO ==================
class UsuarioCrearForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Nombre",
        max_length=150,
        required=True,
        validators=[NAME_VALIDATOR],
    )

    rut_cuerpo = forms.CharField(label="RUT", help_text="Solo números (7 u 8 dígitos)")
    rut_dv = forms.CharField(
        label="DV",
        required=False,
        widget=forms.TextInput(attrs={"readonly": "readonly"})
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

    # --- CAMPOS DEMOGRÁFICOS ---
    direccion = forms.CharField(
        label="Nombre de la Calle/Pasaje",
        max_length=255,
        required=True,
        validators=[DIRECCION_VALIDATOR],
        widget=forms.TextInput(attrs={"placeholder": "Ej: Av. Principal, Pasaje Los Pinos"})
    )
    numero_casa = forms.CharField(
        label="N° Casa/Depto/Lote",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Ej: 123, Dpto 45, Lote B"})
    )

    telefono = forms.CharField(
        label="Teléfono de Contacto",
        max_length=8,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "12345678",
            # OJO: usar text + inputmode numeric es mejor que type=number
            "type": "text",
            "inputmode": "numeric",
            "maxlength": "8",
            "autocomplete": "off",
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
        model = User
        fields = ["username", "email", "first_name"]
        labels = {"first_name": "Nombre"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Estética bootstrap
        for name in (
            "username", "email", "first_name",
            "rut_cuerpo", "rut_dv",
            "apellido_paterno", "apellido_materno",
            "direccion", "numero_casa",
            "telefono", "total_residentes", "total_ninos"
        ):
            if self.fields.get(name):
                self.fields[name].widget.attrs.setdefault("class", "form-control")

        self.fields["rol"].widget.attrs.setdefault("class", "form-select")
        self.fields["username"].widget.attrs.setdefault("placeholder", "ej: kassandra")

        if self.fields.get("rut_dv"):
            self.fields["rut_dv"].widget.attrs["readonly"] = "readonly"

        # ✅ Bloqueo inmediato (frontend)
        attrs_solo_letras = {
            "inputmode": "text",
            "autocomplete": "off",
            "oninput": "this.value=this.value.replace(/[^A-Za-zÁÉÍÓÚÑáéíóúñ\\s]/g,'')",
        }
        self.fields["first_name"].widget.attrs.update(attrs_solo_letras)
        self.fields["apellido_paterno"].widget.attrs.update(attrs_solo_letras)
        self.fields["apellido_materno"].widget.attrs.update(attrs_solo_letras)

        # ✅ Calle/Pasaje: SIN números
        self.fields["direccion"].widget.attrs.update({
            "inputmode": "text",
            "autocomplete": "off",
            # permite letras, espacios y . , - ° # (pero NO números)
            "oninput": "this.value=this.value.replace(/[^A-Za-zÁÉÍÓÚÑáéíóúñ\\s\\.,\\-°#]/g,'')",
        })

        # ✅ Teléfono: solo números + máximo 8
        self.fields["telefono"].widget.attrs.update({
            "oninput": "this.value=this.value.replace(/\\D/g,'').slice(0,8);"
        })

    # ✅ Backend (por si mandan números por POST)
    def clean_first_name(self):
        v = (self.cleaned_data.get("first_name") or "").strip()
        if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÑáéíóúñ ]+", v):
            raise forms.ValidationError("Nombre: solo letras y espacios.")
        return v

    def clean_apellido_paterno(self):
        v = (self.cleaned_data.get("apellido_paterno") or "").strip()
        if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÑáéíóúñ ]+", v):
            raise forms.ValidationError("Apellido paterno: solo letras y espacios.")
        return v

    def clean_apellido_materno(self):
        v = (self.cleaned_data.get("apellido_materno") or "").strip()
        if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÑáéíóúñ ]+", v):
            raise forms.ValidationError("Apellido materno: solo letras y espacios.")
        return v

    def clean_direccion(self):
        v = (self.cleaned_data.get("direccion") or "").strip()
        if re.search(r"\d", v):
            raise forms.ValidationError("Calle/Pasaje no debe contener números. Usa N° Casa/Depto/Lote.")
        # valida caracteres permitidos
        if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÑáéíóúñ\s\.,\-°#]+", v):
            raise forms.ValidationError("Dirección inválida. Solo letras y caracteres básicos (sin números).")
        return v

    # ----- VALIDACIÓN TELÉFONO (+569) -----
    def clean_telefono(self):
        data = (self.cleaned_data.get("telefono") or "").strip()

        # seguridad extra: si llega con más, recorta
        data = re.sub(r"\D", "", data)[:8]

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

    # ----- SAVE: User + Perfil + Email (WEBHOOK) -----
    @transaction.atomic
    def save(self, commit=True):
        if not self.cleaned_data.get("rut"):
            raise forms.ValidationError("No se puede guardar sin RUT válido.")

        user = super().save(commit=False)
        user.username = self.cleaned_data["username"].strip()
        user.email = (self.cleaned_data.get("email") or "").strip()
        user.first_name = (self.cleaned_data.get("first_name") or "").strip().title()

        ap = (self.cleaned_data.get("apellido_paterno") or "").strip().title()
        am = (self.cleaned_data.get("apellido_materno") or "").strip().title()
        user.last_name = f"{ap} {am}".strip()

        # ✅ Contraseña provisoria (16 chars)
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        while True:
            password_provisoria = "".join(secrets.choice(alphabet) for _ in range(16))
            if (
                any(c.islower() for c in password_provisoria)
                and any(c.isupper() for c in password_provisoria)
                and any(c.isdigit() for c in password_provisoria)
                and any(c in "!@#$%^&*" for c in password_provisoria)
            ):
                break

        user.set_password(password_provisoria)

        if commit:
            user.save()

        Perfil.objects.create(
            usuario=user,
            rol=self.cleaned_data["rol"],
            rut=self.cleaned_data["rut"],
            apellido_paterno=ap,
            apellido_materno=am,
            direccion=(self.cleaned_data.get("direccion") or "").strip(),
            numero_casa=(self.cleaned_data.get("numero_casa") or "").strip(),
            telefono=self.cleaned_data["telefono"],  # +569...
            total_residentes=self.cleaned_data.get("total_residentes", 1),
            total_ninos=self.cleaned_data.get("total_ninos") or 0,
            debe_cambiar_password=True,
        )

        # ✅ Enviar correo por WEBHOOK
        if user.email:
            try:
                host = getattr(settings, "RENDER_EXTERNAL_HOSTNAME", "127.0.0.1:8000")
                protocol = "https" if getattr(settings, "RENDER_EXTERNAL_HOSTNAME", None) else "http"
                link_login = f"{protocol}://{host}/accounts/login/"

                contexto = {
                    "nombre": user.first_name,
                    "rut": user.username,
                    "password": password_provisoria,
                    "link_login": link_login,
                }

                html_body = render_to_string("usuarios/email_bienvenida.html", contexto)
                text_body = strip_tags(html_body)
                asunto = "Bienvenido a Villa Vista al Mar - Credenciales de Acceso"

                enviar_correo_via_webhook(
                    to_email=user.email,
                    subject=asunto,
                    html_body=html_body,
                    text_body=text_body,
                )
            except Exception:
                # no romper creación por error de correo
                pass

        return user


# ================== EDITAR USUARIO ==================
class UsuarioEditarForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Nombre",
        max_length=150,
        required=True,
        validators=[NAME_VALIDATOR],
    )

    rut_cuerpo = forms.CharField(label="RUT", help_text="Solo números (7 u 8 dígitos)")
    rut_dv = forms.CharField(
        label="DV",
        required=False,
        widget=forms.TextInput(attrs={"readonly": "readonly"})
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
        validators=[DIRECCION_VALIDATOR],
        widget=forms.TextInput(attrs={"placeholder": "Ej: Av. Principal, Pasaje Los Pinos"})
    )

    numero_casa = forms.CharField(
        label="N° Casa/Depto/Lote",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Ej: 123, Dpto 45, Lote B"})
    )

    telefono = forms.CharField(
        label="Teléfono de Contacto",
        max_length=8,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "12345678",
            "type": "text",
            "inputmode": "numeric",
            "maxlength": "8",
            "autocomplete": "off",
        })
    )

    total_residentes = forms.IntegerField(label="Total Residentes", min_value=1, required=True)
    total_ninos = forms.IntegerField(label="N° de Niños (< 12)", min_value=0, required=False)

    class Meta:
        model = User
        fields = ["username", "email", "first_name"]
        labels = {"first_name": "Nombre"}

    def __init__(self, *args, **kwargs):
        self.instance_user: User = kwargs.get("instance")  # type: ignore
        super().__init__(*args, **kwargs)

        for name in (
            "username", "email", "first_name",
            "rut_cuerpo", "rut_dv",
            "apellido_paterno", "apellido_materno",
            "direccion", "numero_casa",
            "telefono", "total_residentes", "total_ninos"
        ):
            if self.fields.get(name):
                self.fields[name].widget.attrs.setdefault("class", "form-control")

        self.fields["rol"].widget.attrs.setdefault("class", "form-select")
        if self.fields.get("rut_dv"):
            self.fields["rut_dv"].widget.attrs["readonly"] = "readonly"

        # ✅ Bloqueo inmediato para nombre/apellidos
        attrs_solo_letras = {
            "inputmode": "text",
            "autocomplete": "off",
            "oninput": "this.value=this.value.replace(/[^A-Za-zÁÉÍÓÚÑáéíóúñ\\s]/g,'')",
        }
        self.fields["first_name"].widget.attrs.update(attrs_solo_letras)
        self.fields["apellido_paterno"].widget.attrs.update(attrs_solo_letras)
        self.fields["apellido_materno"].widget.attrs.update(attrs_solo_letras)

        # ✅ Calle/Pasaje: SIN números
        self.fields["direccion"].widget.attrs.update({
            "inputmode": "text",
            "autocomplete": "off",
            "oninput": "this.value=this.value.replace(/[^A-Za-zÁÉÍÓÚÑáéíóúñ\\s\\.,\\-°#]/g,'')",
        })

        # ✅ Teléfono: solo números + máximo 8
        self.fields["telefono"].widget.attrs.update({
            "oninput": "this.value=this.value.replace(/\\D/g,'').slice(0,8);"
        })

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

            fono = p.telefono or ""
            if fono.startswith("+569"):
                self.fields["telefono"].initial = fono[4:]
            else:
                self.fields["telefono"].initial = fono

    # ✅ Backend
    def clean_first_name(self):
        v = (self.cleaned_data.get("first_name") or "").strip()
        if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÑáéíóúñ ]+", v):
            raise forms.ValidationError("Nombre: solo letras y espacios.")
        return v

    def clean_apellido_paterno(self):
        v = (self.cleaned_data.get("apellido_paterno") or "").strip()
        if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÑáéíóúñ ]+", v):
            raise forms.ValidationError("Apellido paterno: solo letras y espacios.")
        return v

    def clean_apellido_materno(self):
        v = (self.cleaned_data.get("apellido_materno") or "").strip()
        if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÑáéíóúñ ]+", v):
            raise forms.ValidationError("Apellido materno: solo letras y espacios.")
        return v

    def clean_direccion(self):
        v = (self.cleaned_data.get("direccion") or "").strip()
        if re.search(r"\d", v):
            raise forms.ValidationError("Calle/Pasaje no debe contener números. Usa N° Casa/Depto/Lote.")
        if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÑáéíóúñ\s\.,\-°#]+", v):
            raise forms.ValidationError("Dirección inválida. Solo letras y caracteres básicos (sin números).")
        return v

    def clean_telefono(self):
        data = (self.cleaned_data.get("telefono") or "").strip()
        data = re.sub(r"\D", "", data)[:8]
        if len(data) != 8:
            raise forms.ValidationError("Debe ingresar exactamente 8 dígitos (sin el +569).")
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
        user.username = (self.cleaned_data.get("username") or "").strip()
        user.email = (self.cleaned_data.get("email") or "").strip()
        user.first_name = (self.cleaned_data.get("first_name") or "").strip().title()

        ap = (self.cleaned_data.get("apellido_paterno") or "").strip().title()
        am = (self.cleaned_data.get("apellido_materno") or "").strip().title()
        user.last_name = f"{ap} {am}".strip()

        if commit:
            user.save()

        perfil, _ = Perfil.objects.get_or_create(usuario=user)
        perfil.rol = self.cleaned_data["rol"]
        perfil.rut = self.cleaned_data["rut"]
        perfil.apellido_paterno = ap
        perfil.apellido_materno = am
        perfil.direccion = (self.cleaned_data.get("direccion") or "").strip()
        perfil.numero_casa = (self.cleaned_data.get("numero_casa") or "").strip()
        perfil.total_residentes = self.cleaned_data.get("total_residentes", 1)
        perfil.total_ninos = self.cleaned_data.get("total_ninos") or 0
        perfil.telefono = self.cleaned_data["telefono"]  # +569...
        perfil.save()

        return user
