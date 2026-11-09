from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import OWNERS, WRITERS, get_current_user, get_membership, require_role
from app.models import Pets, Users
from app.schemas import PetCreate, PetOut, PetUpdate

router = APIRouter(tags=["pets"])


def _get_pet(db: Session, pet_id: int) -> Pets:
    pet = db.get(Pets, pet_id)
    if pet is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    return pet


@router.post("/households/{household_id}/pets", response_model=PetOut, status_code=201)
def create_pet(household_id: int, data: PetCreate, db: Session = Depends(get_db),
               user: Users = Depends(get_current_user)):
    require_role(db, household_id, user, WRITERS)
    pet = Pets(household_id=household_id, **data.model_dump())
    db.add(pet)
    db.commit()
    db.refresh(pet)
    return pet


@router.get("/households/{household_id}/pets", response_model=list[PetOut])
def list_pets(household_id: int, db: Session = Depends(get_db),
              user: Users = Depends(get_current_user)):
    get_membership(db, household_id, user)
    return db.scalars(
        select(Pets).where(Pets.household_id == household_id).order_by(Pets.name)
    ).all()


@router.get("/pets/{pet_id}", response_model=PetOut)
def get_pet(pet_id: int, db: Session = Depends(get_db), user: Users = Depends(get_current_user)):
    pet = _get_pet(db, pet_id)
    get_membership(db, pet.household_id, user)
    return pet


@router.patch("/pets/{pet_id}", response_model=PetOut)
def update_pet(pet_id: int, data: PetUpdate, db: Session = Depends(get_db),
               user: Users = Depends(get_current_user)):
    pet = _get_pet(db, pet_id)
    require_role(db, pet.household_id, user, WRITERS)
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
    pet = _get_pet(db, pet_id)
    require_role(db, pet.household_id, user, OWNERS)
    db.delete(pet)
    db.commit()