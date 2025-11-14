# core/roles.py
from dataclasses import dataclass
from typing import Dict, List
from core.models import Perfil

# Nombres exactos de tu enum Perfil.Roles
PRESIDENTE = Perfil.Roles.PRESIDENTE
SECRETARIA = Perfil.Roles.SECRETARIA
TESORERO   = Perfil.Roles.TESORERO
SUPLENTE   = Perfil.Roles.SUPLENTE
VECINO    = Perfil.Roles.VECINO 

# Agrupaciones
ROL_DIRECTIVA = [PRESIDENTE, SECRETARIA, TESORERO, SUPLENTE]
ROL_VECINO    = [VECINO]

# Recurso -> Acción -> [roles permitidos]
ROLE_MATRIX: Dict[str, Dict[str, List[str]]] = {
    "usuarios": {
        "view":   [PRESIDENTE, SECRETARIA, SUPLENTE, TESORERO],
        "create": [PRESIDENTE],
        "edit":   [PRESIDENTE],
        "delete": [PRESIDENTE],
        "assign": [PRESIDENTE],
    },
    
    # --- BLOQUE DE REUNIONES MODIFICADO ---
    "reuniones": {
        "view":   ROL_DIRECTIVA + ROL_VECINO, # Vecinos pueden ver la lista
        "create": [PRESIDENTE, SECRETARIA, SUPLENTE],
        "edit":   [PRESIDENTE, SECRETARIA, SUPLENTE],
        "delete": [PRESIDENTE], # Eliminar de la BD
        "cancel": ROL_DIRECTIVA, # Nueva acción para cancelar
        "change_estado": ROL_DIRECTIVA, # Nueva acción para Iniciar/Finalizar
        "asistencia": [PRESIDENTE, SECRETARIA, SUPLENTE],
    },
    # --------------------------------------

    "actas": {
        "view":   ROL_DIRECTIVA + ROL_VECINO,
        "edit":   [PRESIDENTE, SECRETARIA, SUPLENTE],
        "approve":[PRESIDENTE],
        "delete": [PRESIDENTE],
        "send":   [PRESIDENTE, SECRETARIA], # Añadí 'send' para el correo
    },
    "talleres": {
        "view":   ROL_DIRECTIVA + ROL_VECINO,
        "create": [PRESIDENTE],
        "edit":   [PRESIDENTE],
        "delete": [PRESIDENTE],
    },
    "votaciones": {
        "view":   ROL_DIRECTIVA + ROL_VECINO,
        "create": [PRESIDENTE, TESORERO],
        "edit":   [PRESIDENTE],  
        "close":  [PRESIDENTE, TESORERO],
        "delete": [PRESIDENTE],  
        "preview":ROL_DIRECTIVA,
        "vote":   ROL_VECINO, # Vecinos votan (via API)
        "results":ROL_DIRECTIVA,
    },
    "recursos": {
        "view":   ROL_DIRECTIVA + ROL_VECINO,
        "create": [PRESIDENTE],
        "edit":   [PRESIDENTE],
        "manage_reservas": [PRESIDENTE, SECRETARIA, SUPLENTE], 
    },
    "reservas": {
        "view_own":   ROL_DIRECTIVA + ROL_VECINO,
        "view_all":   ROL_DIRECTIVA,
        "create":     ROL_VECINO,
        "cancel_own": ROL_VECINO,
        "approve":    ROL_DIRECTIVA,
        "reject":     ROL_DIRECTIVA,
    },
    "foro": {
        "view":    ROL_DIRECTIVA + ROL_VECINO,
        "create":  ROL_VECINO,
        "comment": ROL_VECINO,
        "moderate":ROL_DIRECTIVA,
        "delete": [PRESIDENTE], # Solo el presi borra
    },
    "anuncios": {
        "view":   ROL_DIRECTIVA + ROL_VECINO,
        "create": ROL_DIRECTIVA,
        "edit":   ROL_DIRECTIVA,
        "delete": ROL_DIRECTIVA,
    }
}