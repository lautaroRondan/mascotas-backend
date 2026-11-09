from typing import Optional, TYPE_CHECKING
import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, PrimaryKeyConstraint, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.auth_identities import AuthIdentities
    from app.models.households import HouseholdInvitations, HouseholdMembers, Households
    from app.models.medications import MedicationLogs, Medications
    from app.models.reminders import Reminders
    from app.models.veterinary import Vaccines, VetVisits


class Users(Base):
    __tablename__ = 'users'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='users_pkey'),
        UniqueConstraint('email', name='users_email_key')
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(Text)  # opcional: quien entra solo con Google no tiene
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    timezone: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'America/Argentina/Buenos_Aires'::text"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))

    auth_identities: Mapped[list['AuthIdentities']] = relationship('AuthIdentities', back_populates='user')
    households: Mapped[list['Households']] = relationship('Households', back_populates='users')
    household_invitations_invited_by: Mapped[list['HouseholdInvitations']] = relationship('HouseholdInvitations', foreign_keys='[HouseholdInvitations.invited_by]', back_populates='users')
    household_invitations_used_by: Mapped[list['HouseholdInvitations']] = relationship('HouseholdInvitations', foreign_keys='[HouseholdInvitations.used_by]', back_populates='users_')
    household_members: Mapped[list['HouseholdMembers']] = relationship('HouseholdMembers', back_populates='user')
    medications: Mapped[list['Medications']] = relationship('Medications', back_populates='users')
    vet_visits: Mapped[list['VetVisits']] = relationship('VetVisits', back_populates='users')
    vaccines: Mapped[list['Vaccines']] = relationship('Vaccines', back_populates='users')
    medication_logs: Mapped[list['MedicationLogs']] = relationship('MedicationLogs', back_populates='users')
    reminders: Mapped[list['Reminders']] = relationship('Reminders', back_populates='recipient')