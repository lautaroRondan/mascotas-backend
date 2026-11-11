"""Permisos por rol. Es el único lugar donde se decide qué puede hacer cada rol.

Roles de una casa: owner (dueño), member (miembro) y readonly (solo lectura).

Para cambiar quién puede qué, se toca solo la tabla ROLES_BY_PERMISSION.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import HouseholdMembers, Pets, Users

ROLES_BY_PERMISSION: dict[str, set[str]] = {
    # Ver todo: mascotas, visitas, vacunas, medicación, tomas y miembros
    "read":              {"owner", "member", "readonly"},
    # Registrar una toma ("ya se la di"): lo puede hacer cualquiera de la casa
    "log_dose":          {"owner", "member", "readonly"},
    # Crear y editar mascotas, visitas, vacunas y medicaciones; cambiar dosis y horarios;
    # pausar y reanudar una medicación; borrar visitas y vacunas
    "edit":              {"owner", "member"},
    # Solo dueños
    "delete_pet":        {"owner"},
    "finish_medication": {"owner"},   # finalizar (y reabrir) una medicación
    "manage_house":      {"owner"},   # invitaciones y miembros
}

# Mensajes de 403: cortos y en español
DENIED_MESSAGES: dict[str, str] = {
    "edit": "Con tu rol (solo lectura) no podés crear ni modificar datos.",
    "delete_pet": "Solo los dueños de la casa pueden eliminar mascotas.",
    "finish_medication": "Solo los dueños de la casa pueden finalizar o reabrir una medicación.",
    "manage_house": "Solo los dueños de la casa pueden gestionar invitaciones y miembros.",
}
DEFAULT_DENIED_MESSAGE = "No tenés permiso para hacer esto."


def get_membership(db: Session, household_id: int, user: Users) -> HouseholdMembers:
    """La membresía del usuario en la casa. Si no es de esa casa: 404
    (no se revela si la casa existe)."""
    membership = db.get(HouseholdMembers, (household_id, user.id))
    if membership is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    return membership


def require_permission(db: Session, household_id: int, user: Users, permission: str) -> HouseholdMembers:
    """Exige que el rol del usuario en la casa tenga ese permiso.
    Si no lo tiene: 403 (nunca 401: el front lo tomaría como sesión vencida)."""
    membership = get_membership(db, household_id, user)
    if membership.role not in ROLES_BY_PERMISSION[permission]:
        raise HTTPException(
            status_code=403,
            detail=DENIED_MESSAGES.get(permission, DEFAULT_DENIED_MESSAGE),
        )
    return membership


def get_pet_with_permission(db: Session, pet_id: int, user: Users, permission: str = "read") -> Pets:
    """Devuelve la mascota si el usuario es de su casa y tiene ese permiso."""
    pet = db.get(Pets, pet_id)
    if pet is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    require_permission(db, pet.household_id, user, permission)
    return pet