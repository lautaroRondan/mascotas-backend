from datetime import date
from pydantic import BaseModel, ConfigDict, Field, model_validator


class VaccineCreate(BaseModel):
    name: str = Field(min_length=1)
    applied_on: date
    next_due_on: date | None = None
    notes: str | None = None
    vet_visit_id: int | None = None

    @model_validator(mode="after")
    def check_dates(self):
        if self.next_due_on is not None and self.next_due_on < self.applied_on:
            raise ValueError("next_due_on no puede ser anterior a applied_on")
        return self


class VaccineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    applied_on: date | None = None
    next_due_on: date | None = None
    notes: str | None = None
    vet_visit_id: int | None = None


class VaccineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    pet_id: int
    name: str
    applied_on: date
    next_due_on: date | None
    notes: str | None
    vet_visit_id: int | None
