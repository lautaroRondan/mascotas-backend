from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import WRITERS, get_current_user, get_pet_with_access
from app.models import Users, VetVisits
from app.schemas import VetVisitCreate, VetVisitOut, VetVisitUpdate

router = APIRouter(tags=["vet_visits"])


def _get_visit(db: Session, visit_id: int) -> VetVisits:
    visit = db.get(VetVisits, visit_id)
    if visit is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    return visit


@router.post("/pets/{pet_id}/visits", response_model=VetVisitOut, status_code=201)
def create_visit(pet_id: int, data: VetVisitCreate, db: Session = Depends(get_db),
                 user: Users = Depends(get_current_user)):
    get_pet_with_access(db, pet_id, user, WRITERS)
    visit = VetVisits(pet_id=pet_id, created_by=user.id, **data.model_dump())
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


@router.get("/pets/{pet_id}/visits", response_model=list[VetVisitOut])
def list_visits(pet_id: int, db: Session = Depends(get_db),
                user: Users = Depends(get_current_user)):
    get_pet_with_access(db, pet_id, user)
    return db.scalars(
        select(VetVisits).where(VetVisits.pet_id == pet_id).order_by(VetVisits.visited_on.desc())
    ).all()


@router.patch("/visits/{visit_id}", response_model=VetVisitOut)
def update_visit(visit_id: int, data: VetVisitUpdate, db: Session = Depends(get_db),
                 user: Users = Depends(get_current_user)):
    visit = _get_visit(db, visit_id)
    get_pet_with_access(db, visit.pet_id, user, WRITERS)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None and field in ("visited_on", "reason"):
            continue  # estas columnas no admiten vacío
        setattr(visit, field, value)
    db.commit()
    db.refresh(visit)
    return visit


@router.delete("/visits/{visit_id}", status_code=204)
def delete_visit(visit_id: int, db: Session = Depends(get_db),
                 user: Users = Depends(get_current_user)):
    visit = _get_visit(db, visit_id)
    get_pet_with_access(db, visit.pet_id, user, WRITERS)
    db.delete(visit)
    db.commit()
