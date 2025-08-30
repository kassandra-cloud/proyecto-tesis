# core/validators.py
import re
from django.core.exceptions import ValidationError

RUT_REGEX = re.compile(r'^[0-9]{1,2}\.?[0-9]{3}\.?[0-9]{3}-[0-9Kk]$')  # permite puntos o sin puntos

def normalizar_rut(rut: str) -> str:
    """
    Quita puntos, pasa DV a mayúscula y asegura el formato XXXXXXXX-DV.
    """
    if rut is None:
        return rut
    rut = rut.strip().replace('.', '').replace(' ', '')
    # si viene sin guión y con 9 caracteres, lo intentamos separar
    if '-' not in rut and len(rut) >= 2:
        rut = f"{rut[:-1]}-{rut[-1]}"
    cuerpo, dv = rut.split('-', 1)
    return f"{int(cuerpo)}-{dv.upper()}"

def dv_mod11(cuerpo: int) -> str:
    """
    Calcula dígito verificador con algoritmo Módulo 11.
    Retorna '0'-'9' o 'K'.
    """
    suma = 0
    multiplicador = 2
    for c in str(cuerpo)[::-1]:
        suma += int(c) * multiplicador
        multiplicador += 1
        if multiplicador > 7:
            multiplicador = 2
    resto = 11 - (suma % 11)
    if resto == 11:
        return '0'
    if resto == 10:
        return 'K'
    return str(resto)

def validar_rut(value: str):
    """
    Valida:
    1) Formato (con o sin puntos, con guión).
    2) Dígito verificador correcto.
    Lanza ValidationError si no es válido.
    """
    if not value:
        raise ValidationError("El RUT es obligatorio.")

    # Acepta con o sin puntos, pero debe tener guión (se añade si falta en normalización posterior).
    # Aquí validamos una de dos formas: regex flexible o intentamos normalizar y seguir.
    _v = value.strip()

    # Intento de normalización temprana
    try:
        _v = normalizar_rut(_v)
    except Exception:
        raise ValidationError("Formato de RUT inválido.")

    # Verificación post-normalización: debe quedar NNNNNNNN-DV
    if not re.match(r'^[0-9]+-[0-9K]$', _v):
        raise ValidationError("Formato de RUT inválido. Use 12345678-9 o 12.345.678-9.")

    cuerpo_str, dv_ingresado = _v.split('-', 1)
    try:
        cuerpo = int(cuerpo_str)
    except ValueError:
        raise ValidationError("El RUT debe contener solo números antes del guión.")

    dv_correcto = dv_mod11(cuerpo)

    if dv_ingresado != dv_correcto:
        raise ValidationError(f"RUT inválido: dígito verificador debería ser {dv_correcto}.")

    # Si todo ok, no retorna nada (válido)
