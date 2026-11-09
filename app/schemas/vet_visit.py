from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class VetVisitCreate(BaseModel):
    visited_on: date
    reason: str = Field(min_length=1)
    notes: str | None = None
    cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    next_visit_on: date | None = None


class VetVisitUpdate(BaseModel):
    visited_on: date | None = None
    reason: str | None = Field(default=None, min_length=1)
    notes: str | None = None
    cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    next_visit_on: date | None = None


class VetVisitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    pet_id: int
    visited_on: date
    reason: str
    notes: str | None
    cost: Decimal | None
    next_visit_on: date | None
