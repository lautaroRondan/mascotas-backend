from pydantic import BaseModel, Field

class HouseholdCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class HouseholdOut(BaseModel):
    id: int
    name: str
    role: str  # tu rol en esa casa