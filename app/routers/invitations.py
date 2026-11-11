import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.permissions import require_permission
from app.models import HouseholdInvitations, HouseholdMembers, Households, Users
from app.schemas import HouseholdOut, InvitationCreate, InvitationOut, InvitationPreview

router = APIRouter(tags=["invitations"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_usable_invitation(db: Session, code: str, lock: bool = False) -> HouseholdInvitations:
    """Devuelve la invitación si existe, no venció y no fue usada."""
    query = select(HouseholdInvitations).where(HouseholdInvitations.code == code)
    if lock:
        query = query.with_for_update()   # evita que dos personas usen el mismo código a la vez
    inv = db.scalar(query)
    if inv is None:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    if inv.used_at is not None or inv.expires_at <= _now():
        raise HTTPException(status_code=410, detail="La invitación venció o ya fue usada")
    return inv


# ---------- Del lado de la casa (solo dueños) ----------

@router.post("/households/{household_id}/invitations", response_model=InvitationOut, status_code=201)
def create_invitation(household_id: int, data: InvitationCreate, db: Session = Depends(get_db),
                      user: Users = Depends(get_current_user)):
    require_permission(db, household_id, user, "manage_house")
    inv = HouseholdInvitations(
        household_id=household_id,
        code=secrets.token_urlsafe(16),
        email=data.email,
        role=data.role,
        invited_by=user.id,
        expires_at=_now() + timedelta(days=data.expires_in_days),
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


@router.get("/households/{household_id}/invitations", response_model=list[InvitationOut])
def list_invitations(household_id: int, db: Session = Depends(get_db),
                     user: Users = Depends(get_current_user)):
    """Invitaciones pendientes (sin usar y sin vencer)."""
    require_permission(db, household_id, user, "manage_house")
    return db.scalars(
        select(HouseholdInvitations)
        .where(
            HouseholdInvitations.household_id == household_id,
            HouseholdInvitations.used_at.is_(None),
            HouseholdInvitations.expires_at > _now(),
        )
        .order_by(HouseholdInvitations.created_at.desc())
    ).all()


@router.delete("/households/{household_id}/invitations/{invitation_id}", status_code=204)
def revoke_invitation(household_id: int, invitation_id: int, db: Session = Depends(get_db),
                      user: Users = Depends(get_current_user)):
    require_permission(db, household_id, user, "manage_house")
    inv = db.get(HouseholdInvitations, invitation_id)
    if inv is None or inv.household_id != household_id:
        raise HTTPException(status_code=404, detail="No encontrado")
    if inv.used_at is not None:
        raise HTTPException(status_code=409, detail="Esa invitación ya fue usada")
    db.delete(inv)
    db.commit()


# ---------- Del lado de quien recibe el link (hay que estar logueado) ----------

@router.get("/invitations/{code}", response_model=InvitationPreview)
def preview_invitation(code: str, db: Session = Depends(get_db),
                       user: Users = Depends(get_current_user)):
    """Para mostrar "Te invitaron a la casa X" antes de aceptar."""
    inv = _get_usable_invitation(db, code)
    house = db.get(Households, inv.household_id)
    inviter = db.get(Users, inv.invited_by) if inv.invited_by else None
    return InvitationPreview(
        household_name=house.name,
        role=inv.role,
        invited_by_name=inviter.display_name if inviter else None,
        expires_at=inv.expires_at,
        already_member=db.get(HouseholdMembers, (inv.household_id, user.id)) is not None,
        email_mismatch=inv.email is not None and inv.email.lower() != user.email.lower(),
    )


@router.post("/invitations/{code}/accept", response_model=HouseholdOut)
def accept_invitation(code: str, db: Session = Depends(get_db),
                      user: Users = Depends(get_current_user)):
    inv = _get_usable_invitation(db, code, lock=True)
    if inv.email is not None and inv.email.lower() != user.email.lower():
        raise HTTPException(status_code=403, detail="Esta invitación es para otro mail")
    if db.get(HouseholdMembers, (inv.household_id, user.id)) is not None:
        raise HTTPException(status_code=409, detail="Ya sos parte de esta casa")
    db.add(HouseholdMembers(household_id=inv.household_id, user_id=user.id, role=inv.role))
    inv.used_at = _now()
    inv.used_by = user.id
    db.commit()
    house = db.get(Households, inv.household_id)
    return HouseholdOut(id=house.id, name=house.name, role=inv.role)