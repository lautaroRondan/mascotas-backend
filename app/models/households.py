from typing import Optional, TYPE_CHECKING
import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKeyConstraint, Identity, Index, PrimaryKeyConstraint, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.pets import Pets
    from app.models.users import Users


class Households(Base):
    __tablename__ = 'households'
    __table_args__ = (
        ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL', name='households_created_by_fkey'),
        PrimaryKeyConstraint('id', name='households_pkey')
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger)

    users: Mapped[Optional['Users']] = relationship('Users', back_populates='households')
    household_invitations: Mapped[list['HouseholdInvitations']] = relationship('HouseholdInvitations', back_populates='household')
    household_members: Mapped[list['HouseholdMembers']] = relationship('HouseholdMembers', back_populates='household')
    pets: Mapped[list['Pets']] = relationship('Pets', back_populates='household')


class HouseholdMembers(Base):
    __tablename__ = 'household_members'
    __table_args__ = (
        CheckConstraint("role = ANY (ARRAY['owner'::text, 'member'::text, 'readonly'::text])", name='household_members_role_check'),
        ForeignKeyConstraint(['household_id'], ['households.id'], ondelete='CASCADE', name='household_members_household_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='household_members_user_id_fkey'),
        PrimaryKeyConstraint('household_id', 'user_id', name='household_members_pkey'),
        Index('idx_household_members_user', 'user_id')
    )

    household_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    joined_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))

    household: Mapped['Households'] = relationship('Households', back_populates='household_members')
    user: Mapped['Users'] = relationship('Users', back_populates='household_members')


class HouseholdInvitations(Base):
    __tablename__ = 'household_invitations'
    __table_args__ = (
        CheckConstraint("role = ANY (ARRAY['member'::text, 'readonly'::text])", name='household_invitations_role_check'),
        ForeignKeyConstraint(['household_id'], ['households.id'], ondelete='CASCADE', name='household_invitations_household_id_fkey'),
        ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='SET NULL', name='household_invitations_invited_by_fkey'),
        ForeignKeyConstraint(['used_by'], ['users.id'], ondelete='SET NULL', name='household_invitations_used_by_fkey'),
        PrimaryKeyConstraint('id', name='household_invitations_pkey'),
        UniqueConstraint('code', name='household_invitations_code_key'),
        Index('idx_invitations_household', 'household_id')
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    household_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'member'::text"))
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    email: Mapped[Optional[str]] = mapped_column(CITEXT)
    invited_by: Mapped[Optional[int]] = mapped_column(BigInteger)
    used_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    used_by: Mapped[Optional[int]] = mapped_column(BigInteger)

    household: Mapped['Households'] = relationship('Households', back_populates='household_invitations')
    users: Mapped[Optional['Users']] = relationship('Users', foreign_keys=[invited_by], back_populates='household_invitations_invited_by')
    users_: Mapped[Optional['Users']] = relationship('Users', foreign_keys=[used_by], back_populates='household_invitations_used_by')
