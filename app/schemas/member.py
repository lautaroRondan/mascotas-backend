from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class MemberOut(BaseModel):
    user_id: int
    display_name: str
    email: str | None          # solo lo ven los dueños de la casa
    role: str
    joined_at: datetime
    is_me: bool


class MemberUpdate(BaseModel):
    role: Literal["owner", "member", "readonly"]