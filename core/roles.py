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
# Recurso -> Acción -> [roles permitidos]
ROLE_MATRIX: Dict[str, Dict[str, List[str]]] = {
    "usuarios": {
        "view":   [PRESIDENTE, SECRETARIA, SUPLENTE, TESORERO],
        "create": [PRESIDENTE],
        "edit":   [PRESIDENTE],
        "delete": [PRESIDENTE],
        "assign": [PRESIDENTE],
    },
    "reuniones": {
        "view":   [PRESIDENTE, SECRETARIA, TESORERO, SUPLENTE,VECINO],
        "create": [PRESIDENTE, SECRETARIA, SUPLENTE],
        "edit":   [PRESIDENTE, SECRETARIA, SUPLENTE],
        "close":  [PRESIDENTE, SECRETARIA],
        "asistencia": [PRESIDENTE, SECRETARIA, SUPLENTE],
    },
    "actas": {
        "view":   [PRESIDENTE, SECRETARIA, TESORERO, SUPLENTE,VECINO],
        "create": [PRESIDENTE, SECRETARIA, SUPLENTE],
        "edit":   [PRESIDENTE, SECRETARIA, SUPLENTE],
        "approve":[PRESIDENTE],
        "delete": [PRESIDENTE],
    },
    "talleres": {
        "view":   [PRESIDENTE, SECRETARIA, TESORERO, SUPLENTE,VECINO],
        "create": [PRESIDENTE],
        "edit":   [PRESIDENTE],
        "delete": [PRESIDENTE],
    },
    "votaciones": {
        "view":   [PRESIDENTE, SECRETARIA, TESORERO, SUPLENTE,VECINO],
        "create": [PRESIDENTE, TESORERO],
        "edit":   [PRESIDENTE],  # <-- CORREGIDO: Solo Presidente
        "close":  [PRESIDENTE, TESORERO],
        "delete": [PRESIDENTE],  # <-- CORREGIDO: Solo Presidente
        "preview":[PRESIDENTE, SECRETARIA, TESORERO, SUPLENTE],
        "vote":   [],
        "results":[PRESIDENTE, SECRETARIA, TESORERO, SUPLENTE],
    },
    "notas": {
        "admin":  [PRESIDENTE],
    },
}