"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Define la Matriz de Roles y Permisos (ACL/RBAC).
                       Centraliza la configuración de qué roles (Presidente, 
                       Vecino, etc.) pueden acceder a qué recursos (Noticias, 
                       Votaciones) y qué acciones pueden realizar (crear, ver, editar).
--------------------------------------------------------------------------------
"""

# Importa dataclass (aunque no se usa explícitamente en el código mostrado, se importa).
from dataclasses import dataclass
# Importa tipos para anotaciones de tipo (Type Hinting).
from typing import Dict, List
# Importa el modelo Perfil para obtener las constantes de roles.
from core.models import Perfil

# Alias para los nombres exactos del enum Perfil.Roles (evita errores de tipeo).
PRESIDENTE = Perfil.Roles.PRESIDENTE
SECRETARIA = Perfil.Roles.SECRETARIA
TESORERO   = Perfil.Roles.TESORERO
SUPLENTE   = Perfil.Roles.SUPLENTE
VECINO     = Perfil.Roles.VECINO 

# Agrupaciones de roles para simplificar la matriz.
# Roles administrativos/directiva.
ROL_DIRECTIVA = [PRESIDENTE, SECRETARIA, TESORERO, SUPLENTE]
# Roles de usuarios base.
ROL_VECINO    = [VECINO]

# MATRIZ DE PERMISOS
# Estructura: Diccionario { "Recurso": { "Acción": [Lista de Roles Permitidos] } }
ROLE_MATRIX: Dict[str, Dict[str, List[str]]] = {
    "usuarios": {
        "view":   [PRESIDENTE, SECRETARIA, SUPLENTE, TESORERO], # Ver lista usuarios
        "create": [PRESIDENTE],                                 # Crear usuario
        "edit":   [PRESIDENTE],                                 # Editar usuario
        "delete": [PRESIDENTE],                                 # Borrar usuario
        "assign": [PRESIDENTE],                                 # Asignar roles
    },
    
    # --- BLOQUE DE REUNIONES MODIFICADO ---
    "reuniones": {
        "view":   ROL_DIRECTIVA + ROL_VECINO, # Todos (incluso vecinos) ven la lista
        "create": [PRESIDENTE, SECRETARIA, SUPLENTE], # Solo directiva crea
        "edit":   [PRESIDENTE, SECRETARIA, SUPLENTE], # Directiva edita
        "delete": [PRESIDENTE],                       # Solo Presidente borra
        "cancel": ROL_DIRECTIVA,                      # Nueva acción para cancelar
        "change_estado": ROL_DIRECTIVA,               # Nueva acción para Iniciar/Finalizar
        "asistencia": [PRESIDENTE, SECRETARIA, SUPLENTE], # Tomar asistencia
    },
    # --------------------------------------

    "actas": {
        "view":   ROL_DIRECTIVA + ROL_VECINO, # Todos ven las actas
        "edit":   [PRESIDENTE, SECRETARIA, SUPLENTE],
        "approve":[PRESIDENTE],               # Solo presi aprueba final
        "delete": [PRESIDENTE],
        "send":   [PRESIDENTE, SECRETARIA],   # Permiso para enviar acta por correo
    },
    "talleres": {
        "view":   ROL_DIRECTIVA + ROL_VECINO,
        "create": [PRESIDENTE],
        "edit":   [PRESIDENTE],
        "delete": [PRESIDENTE],
    },
    "votaciones": {
        "view":   ROL_DIRECTIVA + ROL_VECINO,
        "create": [PRESIDENTE, TESORERO],     # Tesorero también puede (ej. gastos)
        "edit":   [PRESIDENTE],  
        "close":  [PRESIDENTE, TESORERO],     # Cerrar votación
        "delete": [PRESIDENTE],  
        "preview":ROL_DIRECTIVA,              # Ver antes de publicar
        "vote":   ROL_VECINO,                 # Vecinos votan (generalmente via API)
        "results":ROL_DIRECTIVA,              # Ver resultados detallados
    },
    "recursos": {
        "view":   ROL_DIRECTIVA + ROL_VECINO, # Ver recursos (sedes, parrillas)
        "create": [PRESIDENTE],
        "edit":   [PRESIDENTE],
        "manage_reservas": [PRESIDENTE, SECRETARIA, SUPLENTE], # Gestionar solicitudes
    },
    "reservas": {
        "view_own":   ROL_DIRECTIVA + ROL_VECINO, # Ver mis propias reservas
        "view_all":   ROL_DIRECTIVA,              # Ver todas las reservas
        "create":     ROL_VECINO,                 # Solicitar reserva
        "cancel_own": ROL_VECINO,                 # Cancelar mi solicitud
        "approve":    ROL_DIRECTIVA,              # Aprobar solicitud
        "reject":     ROL_DIRECTIVA,              # Rechazar solicitud
        "manage_all": ROL_DIRECTIVA,
    },
    "foro": {
        "view":     ROL_DIRECTIVA + ROL_VECINO,
        "create":   ROL_VECINO,
        "comment":  ROL_VECINO,
        "moderar":  ROL_DIRECTIVA,  # <-- CORREGIDO: Permiso para ocultar/moderar posts
        "delete":   [PRESIDENTE],   # Solo el presi borra definitivamente
    },
    "anuncios": {
        "view":   ROL_DIRECTIVA + ROL_VECINO, # Todos ven noticias
        "create": ROL_DIRECTIVA,              # Toda la directiva comunica
        "edit":   ROL_DIRECTIVA,
        "delete": ROL_DIRECTIVA,
    }
}