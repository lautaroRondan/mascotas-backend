from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.permissions import get_pet_with_permission
from app.models import Users, Vaccines, VetVisits
from app.schemas import VaccineCreate, VaccineOut, VaccineUpdate

router = APIRouter(tags=["vaccines"])


def _get_vaccine(db: Session, vaccine_id: int) -> Vaccines:
    vaccine = db.get(Vaccines, vaccine_id)
    if vaccine is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    return vaccine


def _check_visit_belongs_to_pet(db: Session, visit_id: int | None, pet_id: int) -> None:
    """La visita vinculada tiene que ser de la misma mascota."""
    if visit_id is None:
        return
    visit = db.get(VetVisits, visit_id)
    if visit is None or visit.pet_id != pet_id:
        raise HTTPException(status_code=422, detail="La visita indicada no corresponde a esta mascota")


@router.post("/pets/{pet_id}/vaccines", response_model=VaccineOut, status_code=201)
def create_vaccine(pet_id: int, data: VaccineCreate, db: Session = Depends(get_db),
                   user: Users = Depends(get_current_user)):
    get_pet_with_permission(db, pet_id, user, "edit")
    _check_visit_belongs_to_pet(db, data.vet_visit_id, pet_id)
    vaccine = Vaccines(pet_id=pet_id, created_by=user.id, **data.model_dump())
    db.add(vaccine)
    db.commit()
    db.refresh(vaccine)
    return vaccine


@router.get("/pets/{pet_id}/vaccines", response_model=list[VaccineOut])
def list_vaccines(pet_id: int, db: Session = Depends(get_db),
                  user: Users = Depends(get_current_user)):
    get_pet_with_permission(db, pet_id, user, "read")
    return db.scalars(
        select(Vaccines).where(Vaccines.pet_id == pet_id).order_by(Vaccines.applied_on.desc())
    ).all()


@router.patch("/vaccines/{vaccine_id}", response_model=VaccineOut)
def update_vaccine(vaccine_id: int, data: VaccineUpdate, db: Session = Depends(get_db),
                   user: Users = Depends(get_current_user)):
    vaccine = _get_vaccine(db, vaccine_id)
    get_pet_with_permission(db, vaccine.pet_id, user, "edit")
    changes = data.model_dump(exclude_unset=True)
    if "vet_visit_id" in changes:
        _check_visit_belongs_to_pet(db, changes["vet_visit_id"], vaccine.pet_id)
    for field, value in changes.items():
        if value is None and field in ("name", "applied_on"):
            continue  # estas columnas no admiten vacío
        setattr(vaccine, field, value)
    if vaccine.next_due_on is not None and vaccine.next_due_on < vaccine.applied_on:
        db.rollback()
        raise HTTPException(status_code=422, detail="next_due_on no puede ser anterior a applied_on")
    db.commit()
    db.refresh(vaccine)
    return vaccine


@router.delete("/vaccines/{vaccine_id}", status_code=204)
def delete_vaccine(vaccine_id: int, db: Session = Depends(get_db),
                   user: Users = Depends(get_current_user)):
    vaccine = _get_vaccine(db, vaccine_id)
    get_pet_with_permission(db, vaccine.pet_id, user, "edit")
    db.delete(vaccine)
    db.commit()