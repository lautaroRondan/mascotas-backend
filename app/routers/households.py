from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Households, HouseholdMembers, Users
from app.schemas import HouseholdCreate, HouseholdOut

router = APIRouter(prefix="/households", tags=["households"])


@router.post("", response_model=HouseholdOut, status_code=201)
def create_household(data: HouseholdCreate, db: Session = Depends(get_db),
                     user: Users = Depends(get_current_user)):
    house = Households(name=data.name, created_by=user.id)
    # Quien crea la casa es su dueño
    house.household_members.append(HouseholdMembers(user_id=user.id, role="owner"))
    db.add(house)
    db.commit()
    db.refresh(house)
    return HouseholdOut(id=house.id, name=house.name, role="owner")


@router.get("", response_model=list[HouseholdOut])
def my_households(db: Session = Depends(get_db), user: Users = Depends(get_current_user)):
    rows = db.execute(
        select(Households, HouseholdMembers.role)
        .join(HouseholdMembers, HouseholdMembers.household_id == Households.id)
        .where(HouseholdMembers.user_id == user.id)
        .order_by(Households.name)
    ).all()
    return [HouseholdOut(id=h.id, name=h.name, role=role) for h, role in rows]