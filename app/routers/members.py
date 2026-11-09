from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import OWNERS, get_current_user, get_membership, require_role
from app.models import HouseholdMembers, Pets, Reminders, Users
from app.schemas import MemberOut, MemberUpdate

router = APIRouter(tags=["members"])


def _ensure_other_owner(db: Session, household_id: int, leaving_user_id: int) -> None:
    """La casa no puede quedarse sin dueño."""
    others = db.scalar(
        select(func.count()).select_from(HouseholdMembers).where(
            HouseholdMembers.household_id == household_id,
            HouseholdMembers.role == "owner",
            HouseholdMembers.user_id != leaving_user_id,
        )
    )
    if not others:
        raise HTTPException(
            status_code=409,
            detail="Es el único dueño de la casa. Primero nombrá a otra persona como dueño.",
        )


def _member_out(m: HouseholdMembers, u: Users, viewer: Users, viewer_is_owner: bool) -> MemberOut:
    return MemberOut(
        user_id=u.id,
        display_name=u.display_name,
        email=u.email if viewer_is_owner else None,
        role=m.role,
        joined_at=m.joined_at,
        is_me=u.id == viewer.id,
    )


@router.get("/households/{household_id}/members", response_model=list[MemberOut])
def list_members(household_id: int, db: Session = Depends(get_db),
                 user: Users = Depends(get_current_user)):
    me = get_membership(db, household_id, user)
    rows = db.execute(
        select(HouseholdMembers, Users)
        .join(Users, Users.id == HouseholdMembers.user_id)
        .where(HouseholdMembers.household_id == household_id)
        .order_by(HouseholdMembers.joined_at)
    ).all()
    return [_member_out(m, u, user, me.role == "owner") for m, u in rows]


@router.patch("/households/{household_id}/members/{user_id}", response_model=MemberOut)
def change_role(household_id: int, user_id: int, data: MemberUpdate, db: Session = Depends(get_db),
                user: Users = Depends(get_current_user)):
    require_role(db, household_id, user, OWNERS)
    target = db.get(HouseholdMembers, (household_id, user_id))
    if target is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    if target.role == "owner" and data.role != "owner":
        _ensure_other_owner(db, household_id, user_id)
    target.role = data.role
    db.commit()
    db.refresh(target)
    return _member_out(target, db.get(Users, user_id), user, True)


@router.delete("/households/{household_id}/members/{user_id}", status_code=204)
def remove_member(household_id: int, user_id: int, db: Session = Depends(get_db),
                  user: Users = Depends(get_current_user)):
    """Un dueño puede sacar a cualquiera; cualquiera puede salirse él mismo."""
    me = get_membership(db, household_id, user)
    if user_id != user.id and me.role != "owner":
        raise HTTPException(status_code=403, detail="No tenés permiso para hacer esto")
    target = db.get(HouseholdMembers, (household_id, user_id))
    if target is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    if target.role == "owner":
        _ensure_other_owner(db, household_id, user_id)

    # Quien se va deja de recibir los avisos pendientes de las mascotas de esta casa
    house_pets = select(Pets.id).where(Pets.household_id == household_id)
    db.execute(
        update(Reminders)
        .where(
            Reminders.recipient_id == user_id,
            Reminders.status == "pending",
            Reminders.pet_id.in_(house_pets),
        )
        .values(status="cancelled")
    )
    db.delete(target)
    db.commit()