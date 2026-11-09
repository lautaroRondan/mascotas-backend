from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class PetCreate(BaseModel):
    name: str = Field(min_length=1)
    species: str = Field(min_length=1)
    breed: str | None = None
    birth_date: date | None = None
    weight_kg: Decimal | None = Field(default=None, gt=0, max_digits=6, decimal_places=2)
    photo_url: str | None = None

class PetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    species: str | None = Field(default=None, min_length=1)
    breed: str | None = None
    birth_date: date | None = None
    weight_kg: Decimal | None = Field(default=None, gt=0, max_digits=6, decimal_places=2)
    photo_url: str | None = None

class PetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    household_id: int
    name: str
    species: str
    breed: str | None
    birth_date: date | None
    weight_kg: Decimal | None
    photo_url: str | None