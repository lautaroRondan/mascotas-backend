from datetime import date, datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import WRITERS, get_current_user, get_pet_with_access
from app.models import MedicationLogs, Medications, Users
from app.schemas import LogCreate, LogOut, SlotOut
from app.services.schedule import slots_for_day

router = APIRouter(tags=["medication_logs"])


def _get_med(db: Session, med_id: int) -> Medications:
    med = db.get(Medications, med_id)
    if med is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    return med


def _log_out(log: MedicationLogs) -> LogOut:
    out = LogOut.model_validate(log)
    out.given_by_name = log.users.display_name if log.users else None
    return out


def _aware(value: datetime, tz: ZoneInfo) -> datetime:
    return value.replace(tzinfo=tz) if value.tzinfo is None else value


@router.get("/medications/{med_id}/slots", response_model=list[SlotOut])
def day_slots(med_id: int, day: date | None = None, db: Session = Depends(get_db),
              user: Users = Depends(get_current_user)):
    """Tomas programadas de un día (por defecto hoy) y si ya se registraron."""
    med = _get_med(db, med_id)
    get_pet_with_access(db, med.pet_id, user)
    tz = ZoneInfo(user.timezone)
    day = day or datetime.now(tz).date()
    slots = slots_for_day(med, day, tz)
    if not slots:
        return []
    logs = db.scalars(
        select(MedicationLogs).where(
            MedicationLogs.medication_id == med.id,
            MedicationLogs.scheduled_at.in_([dt for dt, _ in slots]),
        )
    ).all()
    by_time = {l.scheduled_at: l for l in logs}
    return [
        SlotOut(
            scheduled_at=dt,
            dose_amount=s.dose_amount,
            dose_unit=s.dose_unit,
            dose_note=s.dose_note,
            concentration_amount=s.concentration_amount,
            concentration_unit=s.concentration_unit,
            log=_log_out(by_time[dt]) if dt in by_time else None,
        )
        for dt, s in slots
    ]


@router.post("/medications/{med_id}/logs", response_model=LogOut, status_code=201)
def register_dose(med_id: int, data: LogCreate, db: Session = Depends(get_db),
                  user: Users = Depends(get_current_user)):
    """Registra una toma ("ya se la di") o la salteada. No permite duplicar la misma toma."""
    med = _get_med(db, med_id)
    get_pet_with_access(db, med.pet_id, user, WRITERS)
    tz = ZoneInfo(user.timezone)

    scheduled_at = _aware(data.scheduled_at, tz)
    day_slots_ = slots_for_day(med, scheduled_at.astimezone(tz).date(), tz)
    slot = next((s for dt, s in day_slots_ if dt == scheduled_at), None)
    if slot is None:
        horarios = ", ".join(dt.strftime("%H:%M") for dt, _ in day_slots_) or "ninguna"
        raise HTTPException(
            status_code=422,
            detail=f"No hay una toma programada a esa hora. Tomas de ese día: {horarios}",
        )

    existing = db.scalar(
        select(MedicationLogs).where(
            MedicationLogs.medication_id == med.id,
            MedicationLogs.scheduled_at == scheduled_at,
        )
    )
    if existing is not None:
        quien = existing.users.display_name if existing.users else "alguien"
        raise HTTPException(
            status_code=409,
            detail=f"Esa toma ya está registrada ({existing.status}) por {quien}",
        )

    log = MedicationLogs(
        medication_id=med.id,
        schedule_id=slot.id,
        scheduled_at=scheduled_at,
        status=data.status,
        notes=data.notes,
    )
    if data.status == "given":
        log.given_at = _aware(data.given_at, tz) if data.given_at else datetime.now(timezone.utc)
        log.given_by = user.id
        log.dose_amount = slot.dose_amount   # se guarda la dosis de ese momento
        log.dose_unit = slot.dose_unit
        log.concentration_amount = slot.concentration_amount   # concentración de ese momento
        log.concentration_unit = slot.concentration_unit
        # Stock: solo se descuenta en comprimidos (no se puede restar ml de pastillas)
        if med.stock_quantity is not None and slot.dose_unit == "comprimido":
            med.stock_quantity = max(Decimal(0), med.stock_quantity - slot.dose_amount)

    db.add(log)
    try:
        db.commit()
    except IntegrityError:
        # Dos personas la marcaron al mismo tiempo: gana la primera
        db.rollback()
        raise HTTPException(status_code=409, detail="Esa toma ya está registrada")
    db.refresh(log)
    return _log_out(log)


@router.get("/medications/{med_id}/logs", response_model=list[LogOut])
def list_logs(med_id: int, limit: int = 50, db: Session = Depends(get_db),
              user: Users = Depends(get_current_user)):
    med = _get_med(db, med_id)
    get_pet_with_access(db, med.pet_id, user)
    logs = db.scalars(
        select(MedicationLogs)
        .where(MedicationLogs.medication_id == med.id)
        .order_by(MedicationLogs.scheduled_at.desc())
        .limit(min(max(limit, 1), 200))
    ).all()
    return [_log_out(l) for l in logs]