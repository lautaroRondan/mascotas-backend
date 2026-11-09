from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, computed_field

from app.services.dose import mg_per_dose


class LogCreate(BaseModel):
    # Si no incluye zona horaria, se toma la del usuario (ej: "2026-10-12T20:00:00")
    scheduled_at: datetime
    status: Literal["given", "skipped"] = "given"
    given_at: datetime | None = None      # por defecto, ahora
    notes: str | None = None


class LogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    medication_id: int
    schedule_id: int | None
    scheduled_at: datetime
    status: str                           # given | skipped | missed
    given_at: datetime | None
    given_by: int | None
    given_by_name: str | None = None
    dose_amount: Decimal | None
    dose_unit: str | None
    concentration_amount: Decimal | None
    concentration_unit: str | None
    notes: str | None

    @computed_field
    @property
    def mg_given(self) -> Decimal | None:
        return mg_per_dose(self.dose_amount, self.dose_unit, self.concentration_amount)


class SlotOut(BaseModel):
    scheduled_at: datetime
    dose_amount: Decimal
    dose_unit: str
    dose_note: str | None
    concentration_amount: Decimal | None
    concentration_unit: str | None
    log: LogOut | None   # None = todavía sin registrar

    @computed_field
    @property
    def mg_per_dose(self) -> Decimal | None:
        return mg_per_dose(self.dose_amount, self.dose_unit, self.concentration_amount)