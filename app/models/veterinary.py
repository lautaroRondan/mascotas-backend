from typing import Optional, TYPE_CHECKING
import datetime
import decimal

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKeyConstraint, Identity, Index, Numeric, PrimaryKeyConstraint, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.pets import Pets
    from app.models.reminders import Reminders
    from app.models.users import Users


class VetVisits(Base):
    __tablename__ = 'vet_visits'
    __table_args__ = (
        CheckConstraint('cost >= 0::numeric', name='vet_visits_cost_check'),
        ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL', name='vet_visits_created_by_fkey'),
        ForeignKeyConstraint(['pet_id'], ['pets.id'], ondelete='CASCADE', name='vet_visits_pet_id_fkey'),
        PrimaryKeyConstraint('id', name='vet_visits_pkey'),
        Index('idx_vet_visits_next', 'next_visit_on', postgresql_where='(next_visit_on IS NOT NULL)'),
        Index('idx_vet_visits_pet', 'pet_id', 'visited_on')
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    visited_on: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    cost: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(12, 2))
    next_visit_on: Mapped[Optional[datetime.date]] = mapped_column(Date)
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger)

    users: Mapped[Optional['Users']] = relationship('Users', back_populates='vet_visits')
    pet: Mapped['Pets'] = relationship('Pets', back_populates='vet_visits')
    vaccines: Mapped[list['Vaccines']] = relationship('Vaccines', back_populates='vet_visit')
    reminders: Mapped[list['Reminders']] = relationship('Reminders', back_populates='vet_visit')


class Vaccines(Base):
    __tablename__ = 'vaccines'
    __table_args__ = (
        CheckConstraint('next_due_on IS NULL OR next_due_on >= applied_on', name='vaccines_check'),
        ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL', name='vaccines_created_by_fkey'),
        ForeignKeyConstraint(['pet_id'], ['pets.id'], ondelete='CASCADE', name='vaccines_pet_id_fkey'),
        ForeignKeyConstraint(['vet_visit_id'], ['vet_visits.id'], ondelete='SET NULL', name='vaccines_vet_visit_id_fkey'),
        PrimaryKeyConstraint('id', name='vaccines_pkey'),
        Index('idx_vaccines_due', 'next_due_on', postgresql_where='(next_due_on IS NOT NULL)'),
        Index('idx_vaccines_pet', 'pet_id', 'applied_on')
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    applied_on: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    next_due_on: Mapped[Optional[datetime.date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    vet_visit_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger)

    users: Mapped[Optional['Users']] = relationship('Users', back_populates='vaccines')
    pet: Mapped['Pets'] = relationship('Pets', back_populates='vaccines')
    vet_visit: Mapped[Optional['VetVisits']] = relationship('VetVisits', back_populates='vaccines')
    reminders: Mapped[list['Reminders']] = relationship('Reminders', back_populates='vaccine')
