from datetime import datetime, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user
from app.permissions import get_pet_with_permission, require_permission
from app.models import HouseholdMembers, MedicationSchedules, Medications, Pets, Reminders, Users
from app.schemas import MedicationCreate, MedicationOut, MedicationUpdate, ScheduleChange

router = APIRouter(tags=["medications"])


def _out(med: Medications) -> MedicationOut:
    out = MedicationOut.model_validate(med)
    out.schedules.sort(key=lambda s: s.valid_from, reverse=True)  # el vigente primero
    return out


def _get_med(db: Session, med_id: int) -> Medications:
    med = db.get(Medications, med_id)
    if med is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    return med


def _today(user: Users):
    return datetime.now(ZoneInfo(user.timezone)).date()


@router.post("/pets/{pet_id}/medications", response_model=MedicationOut, status_code=201)
def create_medication(pet_id: int, data: MedicationCreate, db: Session = Depends(get_db),
                      user: Users = Depends(get_current_user)):
    get_pet_with_permission(db, pet_id, user, "edit")
    med = Medications(
        pet_id=pet_id,
        name=data.name,
        presentation=data.presentation,
        is_chronic=data.is_chronic,
        start_date=data.start_date,
        end_date=data.end_date,
        stock_quantity=data.stock_quantity,
        prescription_expires_on=data.prescription_expires_on,
        notes=data.notes,
        created_by=user.id,
    )
    # El primer tramo (frecuencia, horarios y dosis) rige desde la fecha de inicio
    med.medication_schedules.append(
        MedicationSchedules(valid_from=data.start_date, **data.schedule.model_dump())
    )
    db.add(med)
    db.commit()
    db.refresh(med)
    return _out(med)


@router.get("/pets/{pet_id}/medications", response_model=list[MedicationOut])
def list_medications(pet_id: int, status: Literal["active", "paused", "finished"] | None = None,
                     db: Session = Depends(get_db), user: Users = Depends(get_current_user)):
    get_pet_with_permission(db, pet_id, user, "read")
    query = (
        select(Medications)
        .options(selectinload(Medications.medication_schedules))
        .where(Medications.pet_id == pet_id)
        .order_by(Medications.status, Medications.name)
    )
    if status:
        query = query.where(Medications.status == status)
    return [_out(m) for m in db.scalars(query).all()]


@router.get("/medications/{med_id}", response_model=MedicationOut)
def get_medication(med_id: int, db: Session = Depends(get_db), user: Users = Depends(get_current_user)):
    med = _get_med(db, med_id)
    get_pet_with_permission(db, med.pet_id, user, "read")
    return _out(med)


@router.patch("/medications/{med_id}", response_model=MedicationOut)
def update_medication(med_id: int, data: MedicationUpdate, db: Session = Depends(get_db),
                      user: Users = Depends(get_current_user)):
    med = _get_med(db, med_id)
    pet = get_pet_with_permission(db, med.pet_id, user, "edit")
    changes = data.model_dump(exclude_unset=True)

    # Pausar y reanudar lo puede hacer un miembro; finalizar o reabrir, solo un dueño
    new_status = changes.get("status")
    if new_status is not None and (new_status == "finished") != (med.status == "finished"):
        require_permission(db, pet.household_id, user, "finish_medication")

    if med.is_chronic and changes.get("end_date") is not None and changes.get("is_chronic") is not False:
        raise HTTPException(status_code=422, detail="Un tratamiento crónico no lleva fecha de fin")

    for field, value in changes.items():
        if value is None and field in ("name", "status", "is_chronic"):
            continue  # estas columnas no admiten vacío
        setattr(med, field, value)

    if med.is_chronic:
        med.end_date = None  # si pasa a crónico, se borra la fecha de fin
    elif med.end_date is None or med.end_date < med.start_date:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail="Si no es crónico, necesita end_date igual o posterior a start_date",
        )
    db.commit()
    db.refresh(med)
    return _out(med)


@router.post("/medications/{med_id}/schedules", response_model=MedicationOut, status_code=201)
def change_schedule(med_id: int, data: ScheduleChange, db: Session = Depends(get_db),
                    user: Users = Depends(get_current_user)):
    """Cambia dosis, frecuencia u horarios sin perder el historial:
    cierra el tramo vigente y abre uno nuevo desde valid_from (por defecto, hoy)."""
    med = _get_med(db, med_id)
    pet = get_pet_with_permission(db, med.pet_id, user, "edit")
    if med.status == "finished":
        raise HTTPException(status_code=422, detail="El tratamiento está finalizado")

    valid_from = data.valid_from or _today(user)
    current = db.scalar(
        select(MedicationSchedules).where(
            MedicationSchedules.medication_id == med.id,
            MedicationSchedules.valid_to.is_(None),
        )
    )
    if current is not None:
        if valid_from <= current.valid_from:
            raise HTTPException(
                status_code=422,
                detail=f"valid_from tiene que ser posterior al inicio del tramo vigente ({current.valid_from})",
            )
        concentration_changed = (
            current.concentration_amount is not None
            and current.concentration_amount != data.concentration_amount
        )
        if concentration_changed and not data.confirm_dose:
            # Cambió la concentración: hay que confirmar que la dosis es la correcta
            raise HTTPException(status_code=409, detail={
                "code": "confirm_dose_required",
                "message": "Cambió la concentración. Confirmá la dosis para continuar (confirm_dose: true).",
                "previous_concentration": str(current.concentration_amount),
                "new_concentration": str(data.concentration_amount) if data.concentration_amount is not None else None,
                "dose_amount": str(data.dose_amount),
                "dose_unit": data.dose_unit,
            })
        current.valid_to = valid_from - timedelta(days=1)
    else:
        concentration_changed = False

    new_schedule = MedicationSchedules(
        medication_id=med.id,
        valid_from=valid_from,
        **data.model_dump(exclude={"valid_from", "confirm_dose"}),
    )
    db.add(new_schedule)
    db.flush()  # para tener el id del tramo nuevo

    if concentration_changed and med.status != "finished":
        # Aviso a los demás miembros de la casa. Queda pendiente en `reminders`;
        # el envío del mail lo hace el proceso de avisos (paso pendiente).
        now = datetime.now(timezone.utc)
        member_ids = db.scalars(
            select(HouseholdMembers.user_id).where(
                HouseholdMembers.household_id == pet.household_id,
                HouseholdMembers.user_id != user.id,
            )
        ).all()
        for member_id in member_ids:
            db.add(Reminders(
                kind="concentration_change",
                recipient_id=member_id,
                pet_id=med.pet_id,
                medication_id=med.id,
                scheduled_for=now,
                send_at=now,
                dedupe_key=f"conc:{med.id}:{new_schedule.id}:u{member_id}",
            ))
    db.commit()
    db.refresh(med)
    return _out(med)