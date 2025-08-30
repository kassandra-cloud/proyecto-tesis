# core/rut.py
import re

def dv_mod11(cuerpo: int) -> str:
    suma, factor = 0, 2
    for d in reversed(str(cuerpo)):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    if resto == 11: return "0"
    if resto == 10: return "K"
    return str(resto)

def normalizar_rut(rut: str) -> str:
    if rut is None:
        raise ValueError("RUT no puede ser None.")
    rut = rut.replace(".", "").replace(" ", "").upper()
    m = re.fullmatch(r"(\d{7,9})-([\dK])", rut)
    if not m:
        raise ValueError("Formato de RUT inválido. Ej: 12345678-9")
    cuerpo, dv = m.groups()
    return f"{int(cuerpo)}-{dv}"

def validar_rut(rut: str) -> None:
    import re
    m = re.fullmatch(r"(\d{7,9})-([\dK])", rut.upper())
    if not m:
        raise ValueError("Formato de RUT inválido. Ej: 12345678-9")
    cuerpo, dv = m.groups()
    if dv_mod11(int(cuerpo)) != dv:
        raise ValueError("Dígito verificador incorrecto.")