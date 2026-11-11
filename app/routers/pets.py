from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Pets, Users
from app.permissions import get_pet_with_permission, require_permission
from app.schemas import PetCreate, PetOut, PetUpdate

router = APIRouter(tags=["pets"])


@router.post("/households/{household_id}/pets", response_model=PetOut, status_code=201)
def create_pet(household_id: int, data: PetCreate, db: Session = Depends(get_db),
               user: Users = Depends(get_current_user)):
    require_permission(db, household_id, user, "edit")
    pet = Pets(household_id=household_id, **data.model_dump())
    db.add(pet)
    db.commit()
    db.refresh(pet)
    return pet


@router.get("/households/{household_id}/pets", response_model=list[PetOut])
def list_pets(household_id: int, db: Session = Depends(get_db),
              user: Users = Depends(get_current_user)):
    require_permission(db, household_id, user, "read")
    return db.scalars(
        select(Pets).where(Pets.household_id == household_id).order_by(Pets.name)
    ).all()


@router.get("/pets/{pet_id}", response_model=PetOut)
def get_pet(pet_id: int, db: Session = Depends(get_db), user: Users = Depends(get_current_user)):
    return get_pet_with_permission(db, pet_id, user, "read")


@router.patch("/pets/{pet_id}", response_model=PetOut)
def update_pet(pet_id: int, data: PetUpdate, db: Session = Depends(get_db),
               user: Users = Depends(get_current_user)):
    pet = get_pet_with_permission(db, pet_id, user, "edit")
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is None and field in ("name", "species"):
            continue  # estas columnas no admiten vacío
        setattr(pet, field, value)
    db.commit()
    db.refresh(pet)
    return pet


@router.delete("/pets/{pet_id}", status_code=204)
def delete_pet(pet_id: int, db: Session = Depends(get_db), user: Users = Depends(get_current_user)):
    pet = get_pet_with_permission(db, pet_id, user, "delete_pet")
    db.delete(pet)
    db.commit()