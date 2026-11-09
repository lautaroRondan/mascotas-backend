from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class InvitationCreate(BaseModel):
    role: Literal["member", "readonly"] = "member"
    email: EmailStr | None = None                       # opcional: invitación dirigida a un mail
    expires_in_days: int = Field(default=7, ge=1, le=30)


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str                                           # el front arma el link con este código
    role: str
    email: str | None
    expires_at: datetime
    created_at: datetime


class InvitationPreview(BaseModel):
    household_name: str
    role: str
    invited_by_name: str | None
    expires_at: datetime
    already_member: bool       # ya sos parte de esa casa
    email_mismatch: bool       # la invitación es para otro mail