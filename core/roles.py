# core/roles.py
from dataclasses import dataclass
from typing import Dict, List
from core.models import Perfil

# Nombres exactos de tu enum Perfil.Roles (ajusta si difieren)
PRESIDENTE = Perfil.Roles.PRESIDENTE
SECRETARIA = Perfil.Roles.SECRETARIA
TESORERO   = Perfil.Roles.TESORERO
SUPLENTE   = Perfil.Roles.SUPLENTE


# Recurso -> Acción -> [roles permitidos]
ROLE_MATRIX: Dict[str, Dict[str, List[str]]] = {
    "usuarios": {
        "view":   [PRESIDENTE,SECRETARIA,SUPLENTE,TESORERO],  # solo Presidente ve/gestiona usuarios
        "create": [PRESIDENTE],
        "edit":   [PRESIDENTE],
        "delete": [PRESIDENTE],
        "assign": [PRESIDENTE],  # asignar roles
    },
    "reuniones": {
        "view":   [PRESIDENTE, SECRETARIA, TESORERO, SUPLENTE],
        "create": [PRESIDENTE, SECRETARIA, SUPLENTE],
        "edit":   [PRESIDENTE, SECRETARIA, SUPLENTE],
        "close":  [PRESIDENTE, SECRETARIA],
        "asistencia": [PRESIDENTE, SECRETARIA, SUPLENTE],  # registrar asistencia
    },
    "actas": {
        "view":   [PRESIDENTE, SECRETARIA, TESORERO, SUPLENTE],  # ojo: Vecino ve solo aprobadas (se filtra en la vista)
        "create": [PRESIDENTE, SECRETARIA, SUPLENTE],
        "edit":   [PRESIDENTE, SECRETARIA, SUPLENTE],
        "approve":[PRESIDENTE],                      # aprobar
        "delete": [PRESIDENTE],                      # eliminar
    },
    "talleres": {
        "view":   [PRESIDENTE, SECRETARIA, TESORERO, SUPLENTE],
        "create": [PRESIDENTE],
        "edit":   [PRESIDENTE],
        "delete": [PRESIDENTE],
       
    },
    "votaciones": {
        "view":   [PRESIDENTE, SECRETARIA, TESORERO, SUPLENTE],
        "create": [PRESIDENTE, TESORERO],           # “Crear/editar votaciones” para tesorero también
        "edit":   [PRESIDENTE, TESORERO],
        "close":  [PRESIDENTE, TESORERO],                    
        "results":[PRESIDENTE, SECRETARIA, TESORERO, SUPLENTE],
    },
    "notas": {
        "admin":  [PRESIDENTE],                      # “Administrador del sitio”
    },
}
