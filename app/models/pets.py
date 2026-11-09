from typing import Optional, TYPE_CHECKING
import datetime
import decimal

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKeyConstraint, Identity, Index, Numeric, PrimaryKeyConstraint, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.households import Households
    from app.models.medications import Medications
    from app.models.reminders import Reminders
    from app.models.veterinary import Vaccines, VetVisits


class Pets(Base):
    __tablename__ = 'pets'
    __table_args__ = (
        CheckConstraint('weight_kg > 0::numeric', name='pets_weight_kg_check'),
        ForeignKeyConstraint(['household_id'], ['households.id'], ondelete='CASCADE', name='pets_household_id_fkey'),
        PrimaryKeyConstraint('id', name='pets_pkey'),
        Index('idx_pets_household', 'household_id')
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    household_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    species: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    breed: Mapped[Optional[str]] = mapped_column(Text)
    birth_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    weight_kg: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(6, 2))
    photo_url: Mapped[Optional[str]] = mapped_column(Text)

    household: Mapped['Households'] = relationship('Households', back_populates='pets')
    medications: Mapped[list['Medications']] = relationship('Medications', back_populates='pet')
    vet_visits: Mapped[list['VetVisits']] = relationship('VetVisits', back_populates='pet')
    vaccines: Mapped[list['Vaccines']] = relationship('Vaccines', back_populates='pet')
    reminders: Mapped[list['Reminders']] = relationship('Reminders', back_populates='pet')
