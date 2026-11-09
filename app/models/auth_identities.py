from typing import Optional, TYPE_CHECKING
import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKeyConstraint, Identity, PrimaryKeyConstraint, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.users import Users


class AuthIdentities(Base):
    __tablename__ = 'auth_identities'
    __table_args__ = (
        CheckConstraint("provider = ANY (ARRAY['password'::text, 'google'::text])", name='auth_identities_provider_check'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='auth_identities_user_id_fkey'),
        PrimaryKeyConstraint('id', name='auth_identities_pkey'),
        UniqueConstraint('provider', 'provider_user_id', name='auth_identities_provider_provider_user_id_key'),
        UniqueConstraint('user_id', 'provider', name='auth_identities_user_id_provider_key')
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)           # 'password' | 'google'
    provider_user_id: Mapped[str] = mapped_column(Text, nullable=False)   # google: el "sub"; password: id del usuario
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    email: Mapped[Optional[str]] = mapped_column(CITEXT)

    user: Mapped['Users'] = relationship('Users', back_populates='auth_identities')