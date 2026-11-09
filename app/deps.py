import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import HouseholdMembers, Pets, Users

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Roles que pueden hacer cada cosa
WRITERS = {"owner", "member"}   # cargar y editar
OWNERS = {"owner"}              # acciones delicadas (borrar mascota, etc.)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Users:
    error = HTTPException(
        status_code=401,
        detail="Token inválido o vencido",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise error
    user = db.get(Users, user_id)
    if user is None:
        raise error
    return user


def get_membership(db: Session, household_id: int, user: Users) -> HouseholdMembers:
    m = db.get(HouseholdMembers, (household_id, user.id))
    if m is None:
        # 404 y no 403: no revelamos si la casa existe
        raise HTTPException(status_code=404, detail="No encontrado")
    return m


def require_role(db: Session, household_id: int, user: Users, allowed: set[str]) -> HouseholdMembers:
    m = get_membership(db, household_id, user)
    if m.role not in allowed:
        raise HTTPException(status_code=403, detail="No tenés permiso para hacer esto")
    return m


def get_pet_with_access(db: Session, pet_id: int, user: Users, allowed: set[str] | None = None) -> Pets:
    """Devuelve la mascota si el usuario es de su casa.
    Si se pasa `allowed`, además exige uno de esos roles."""
    pet = db.get(Pets, pet_id)
    if pet is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    if allowed is None:
        get_membership(db, pet.household_id, user)
    else:
        require_role(db, pet.household_id, user, allowed)
    return pet