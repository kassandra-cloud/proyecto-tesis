"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Funciones utilitarias para el manejo del Rol Único 
                       Tributario (RUT) chileno. Incluye cálculo de dígito 
                       verificador (Módulo 11), normalización de formato y 
                       validación completa.
--------------------------------------------------------------------------------
"""

# Importa expresiones regulares.
import re

def dv_mod11(cuerpo: int) -> str:
    """Calcula el dígito verificador usando el algoritmo Módulo 11."""
    suma, factor = 0, 2
    # Recorre los dígitos del cuerpo de derecha a izquierda multiplicando por la serie 2-7.
    for d in reversed(str(cuerpo)):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    
    # Calcula el resto.
    resto = 11 - (suma % 11)
    
    # Convierte casos especiales.
    if resto == 11: return "0"
    if resto == 10: return "K"
    return str(resto)

def normalizar_rut(rut: str) -> str:
    """Limpia el RUT (quita puntos/espacios) y lo formatea como '12345678-K'."""
    if rut is None:
        raise ValueError("RUT no puede ser None.")
    
    # Quita puntos y espacios, convierte a mayúsculas.
    rut = rut.replace(".", "").replace(" ", "").upper()
    
    # Verifica formato básico con Regex (números + guion opcional + número/K).
    m = re.fullmatch(r"(\d{7,9})-([\dK])", rut)
    if not m:
        raise ValueError("Formato de RUT inválido. Ej: 12345678-9")
    
    cuerpo, dv = m.groups()
    # Retorna formato limpio.
    return f"{int(cuerpo)}-{dv}"

def validar_rut(rut: str) -> None:
    """Valida formato y consistencia matemática del RUT. Lanza error si es inválido."""
    import re
    # Verifica patrón regex.
    m = re.fullmatch(r"(\d{7,9})-([\dK])", rut.upper())
    if not m:
        raise ValueError("Formato de RUT inválido. Ej: 12345678-9")
    
    cuerpo, dv = m.groups()
    # Verifica que el DV calculado coincida con el DV entregado.
    if dv_mod11(int(cuerpo)) != dv:
        raise ValueError("Dígito verificador incorrecto.")