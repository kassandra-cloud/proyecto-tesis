"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Contiene validadores personalizados para formularios y 
                       modelos de Django. Incluye lógica completa para validar,
                       normalizar y calcular el dígito verificador del RUT chileno.
--------------------------------------------------------------------------------
"""

# Importa módulo de expresiones regulares.
import re
# Importa la excepción estándar de validación de Django.
from django.core.exceptions import ValidationError

# Compila una expresión regular para el formato RUT (acepta con/sin puntos).
RUT_REGEX = re.compile(r'^[0-9]{1,2}\.?[0-9]{3}\.?[0-9]{3}-[0-9Kk]$')

def normalizar_rut(rut: str) -> str:
    """
    Quita puntos, pasa DV a mayúscula y asegura el formato XXXXXXXX-DV.
    """
    if rut is None:
        return rut
    # Limpia espacios y puntos.
    rut = rut.strip().replace('.', '').replace(' ', '')
    
    # Lógica inteligente: si el usuario escribió '123456789' sin guion,
    # asume que el último dígito es el verificador e inserta el guion.
    if '-' not in rut and len(rut) >= 2:
        rut = f"{rut[:-1]}-{rut[-1]}"
        
    # Separa cuerpo y DV.
    cuerpo, dv = rut.split('-', 1)
    # Retorna formateado limpio.
    return f"{int(cuerpo)}-{dv.upper()}"

def dv_mod11(cuerpo: int) -> str:
    """
    Calcula dígito verificador con algoritmo Módulo 11.
    Retorna '0'-'9' o 'K'.
    """
    suma = 0
    multiplicador = 2
    # Recorre el número invertido multiplicando por la serie 2,3,4,5,6,7.
    for c in str(cuerpo)[::-1]:
        suma += int(c) * multiplicador
        multiplicador += 1
        if multiplicador > 7:
            multiplicador = 2
            
    # Cálculo del resto según Mod11.
    resto = 11 - (suma % 11)
    
    # Mapeo de casos especiales.
    if resto == 11:
        return '0'
    if resto == 10:
        return 'K'
    return str(resto)

def validar_rut(value: str):
    """
    Valida integralmente un RUT:
    1) Formato (con o sin puntos, con guión).
    2) Dígito verificador correcto (matemática).
    Lanza ValidationError si no es válido.
    """
    if not value:
        raise ValidationError("El RUT es obligatorio.")

    # Limpia espacios iniciales/finales.
    _v = value.strip()

    # Intento de normalización temprana para estandarizar la entrada.
    try:
        _v = normalizar_rut(_v)
    except Exception:
        raise ValidationError("Formato de RUT inválido.")

    # Verificación estricta post-normalización: debe quedar NNNNNNNN-DV.
    if not re.match(r'^[0-9]+-[0-9K]$', _v):
        raise ValidationError("Formato de RUT inválido. Use 12345678-9 o 12.345.678-9.")

    # Separa para validación matemática.
    cuerpo_str, dv_ingresado = _v.split('-', 1)
    try:
        cuerpo = int(cuerpo_str)
    except ValueError:
        raise ValidationError("El RUT debe contener solo números antes del guión.")

    # Calcula el DV correcto para ese cuerpo.
    dv_correcto = dv_mod11(cuerpo)

    # Compara el calculado con el ingresado.
    if dv_ingresado != dv_correcto:
        raise ValidationError(f"RUT inválido: dígito verificador debería ser {dv_correcto}.")

    # Si todo ok, termina la función sin errores (válido).