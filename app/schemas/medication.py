from datetime import date, time, timedelta
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator,
)

from app.services.dose import mg_per_dose

Recurrence = Literal["daily", "every_n_days", "weekdays"]
DoseUnit = Literal["comprimido", "ml", "gotas"]            # unidad de administración
Presentation = Literal["comprimido", "jarabe", "gotas"]    # lo que hay en casa
MedStatus = Literal["active", "paused", "finished"]


# ---------- Frecuencia, horarios, dosis y concentración (un "tramo" con vigencia) ----------

class ScheduleCreate(BaseModel):
    recurrence_type: Recurrence                      # daily | every_n_days | weekdays
    times: list[time] = Field(min_length=1)          # ej: ["08:00", "20:00"]
    # Dosis por toma (la indica el veterinario)
    dose_amount: Decimal = Field(gt=0, max_digits=8, decimal_places=2)
    dose_unit: DoseUnit
    dose_note: str | None = None                     # ej: "con comida"
    # Concentración de lo que hay en casa: mg por comprimido (o mg por ml en líquidos)
    concentration_amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=3)
    concentration_unit: Literal["mg"] | None = None
    interval_days: int | None = Field(default=None, ge=2, le=365)   # solo every_n_days
    days_of_week: list[int] | None = None            # solo weekdays: 1=lunes ... 7=domingo

    @field_validator("times")
    @classmethod
    def sort_times(cls, v: list[time]) -> list[time]:
        return sorted(set(v))

    @model_validator(mode="after")
    def check_concentration(self):
        if self.concentration_amount is not None and self.concentration_unit is None:
            self.concentration_unit = "mg"   # hoy es la única unidad posible
        if self.concentration_amount is None and self.concentration_unit is not None:
            raise ValueError("Si indicás concentration_unit, falta concentration_amount")
        return self

    @model_validator(mode="after")
    def check_recurrence(self):
        if self.recurrence_type == "daily":
            if self.interval_days is not None or self.days_of_week is not None:
                raise ValueError("daily no lleva interval_days ni days_of_week")
        elif self.recurrence_type == "every_n_days":
            if self.interval_days is None:
                raise ValueError("every_n_days necesita interval_days (2 o más)")
            if self.days_of_week is not None:
                raise ValueError("every_n_days no lleva days_of_week")
        else:  # weekdays
            if self.interval_days is not None:
                raise ValueError("weekdays no lleva interval_days")
            if not self.days_of_week:
                raise ValueError("weekdays necesita days_of_week (1=lunes ... 7=domingo)")
            if any(d < 1 or d > 7 for d in self.days_of_week):
                raise ValueError("days_of_week solo admite valores de 1 a 7")
            self.days_of_week = sorted(set(self.days_of_week))
        return self


class ScheduleChange(ScheduleCreate):
    """Cambio de dosis, concentración u horario: crea un tramo nuevo desde valid_from (por defecto, hoy)."""
    valid_from: date | None = None
    # Si cambia la concentración, hay que confirmar que la dosis es la correcta
    confirm_dose: bool = False


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    recurrence_type: str
    times: list[time]
    dose_amount: Decimal
    dose_unit: str
    dose_note: str | None
    concentration_amount: Decimal | None
    concentration_unit: str | None
    interval_days: int | None
    days_of_week: list[int] | None
    valid_from: date
    valid_to: date | None

    @computed_field
    @property
    def mg_per_dose(self) -> Decimal | None:
        return mg_per_dose(self.dose_amount, self.dose_unit, self.concentration_amount)


# ---------- Medicación ----------

class MedicationCreate(BaseModel):
    name: str = Field(min_length=1)
    presentation: Presentation | None = None
    is_chronic: bool = False
    start_date: date
    end_date: date | None = None
    duration_days: int | None = Field(default=None, ge=1, le=3650)   # alternativa a end_date
    stock_quantity: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    prescription_expires_on: date | None = None
    notes: str | None = None
    schedule: ScheduleCreate

    @model_validator(mode="after")
    def check_duration(self):
        if self.is_chronic:
            if self.end_date is not None or self.duration_days is not None:
                raise ValueError("Un tratamiento crónico no lleva end_date ni duration_days")
        else:
            if (self.end_date is None) == (self.duration_days is None):
                raise ValueError("Si no es crónico, indicá end_date o duration_days (solo uno)")
            if self.duration_days is not None:
                # "durante 10 días" desde el día de inicio: termina 9 días después
                self.end_date = self.start_date + timedelta(days=self.duration_days - 1)
            if self.end_date < self.start_date:
                raise ValueError("end_date no puede ser anterior a start_date")
        return self


class MedicationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    presentation: Presentation | None = None
    status: MedStatus | None = None
    is_chronic: bool | None = None
    end_date: date | None = None
    stock_quantity: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    prescription_expires_on: date | None = None
    notes: str | None = None


class MedicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    pet_id: int
    name: str
    presentation: str | None
    is_chronic: bool
    start_date: date
    end_date: date | None
    status: str
    stock_quantity: Decimal | None
    prescription_expires_on: date | None
    notes: str | None
    schedules: list[ScheduleOut] = Field(default_factory=list, validation_alias="medication_schedules")