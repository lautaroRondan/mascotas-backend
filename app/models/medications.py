from typing import Optional, TYPE_CHECKING
import datetime
import decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKeyConstraint, Identity, Index, Numeric, PrimaryKeyConstraint, SmallInteger, Text, Time, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.pets import Pets
    from app.models.reminders import Reminders
    from app.models.users import Users


class Medications(Base):
    __tablename__ = 'medications'
    __table_args__ = (
        CheckConstraint('is_chronic AND end_date IS NULL OR NOT is_chronic AND end_date IS NOT NULL AND end_date >= start_date', name='chk_medication_duration'),
        CheckConstraint("presentation = ANY (ARRAY['comprimido'::text, 'jarabe'::text, 'gotas'::text])", name='medications_presentation_check'),
        CheckConstraint("status = ANY (ARRAY['active'::text, 'paused'::text, 'finished'::text])", name='medications_status_check'),
        CheckConstraint('stock_quantity >= 0::numeric', name='medications_stock_quantity_check'),
        ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL', name='medications_created_by_fkey'),
        ForeignKeyConstraint(['pet_id'], ['pets.id'], ondelete='CASCADE', name='medications_pet_id_fkey'),
        PrimaryKeyConstraint('id', name='medications_pkey'),
        Index('idx_medications_active', 'pet_id', postgresql_where="(status = 'active'::text)"),
        Index('idx_medications_pet', 'pet_id')
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    is_chronic: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'::text"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    catalog_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    presentation: Mapped[Optional[str]] = mapped_column(Text)   # comprimido | jarabe | gotas
    end_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    stock_quantity: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(8, 2))
    prescription_expires_on: Mapped[Optional[datetime.date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger)

    users: Mapped[Optional['Users']] = relationship('Users', back_populates='medications')
    pet: Mapped['Pets'] = relationship('Pets', back_populates='medications')
    medication_schedules: Mapped[list['MedicationSchedules']] = relationship('MedicationSchedules', back_populates='medication')
    medication_logs: Mapped[list['MedicationLogs']] = relationship('MedicationLogs', back_populates='medication')
    reminders: Mapped[list['Reminders']] = relationship('Reminders', back_populates='medication')


class MedicationSchedules(Base):
    __tablename__ = 'medication_schedules'
    __table_args__ = (
        CheckConstraint('cardinality(times) >= 1', name='chk_schedule_times'),
        CheckConstraint('dose_amount > 0::numeric', name='medication_schedules_dose_amount_check'),
        CheckConstraint("dose_unit = ANY (ARRAY['comprimido'::text, 'ml'::text, 'gotas'::text])", name='medication_schedules_dose_unit_check'),
        CheckConstraint('concentration_amount > 0::numeric', name='medication_schedules_concentration_amount_check'),
        CheckConstraint("concentration_unit = 'mg'::text", name='medication_schedules_concentration_unit_check'),
        CheckConstraint('concentration_amount IS NULL = (concentration_unit IS NULL)', name='chk_schedule_concentration'),
        CheckConstraint("recurrence_type = 'daily'::text AND interval_days IS NULL AND days_of_week IS NULL OR recurrence_type = 'every_n_days'::text AND interval_days >= 2 AND days_of_week IS NULL OR recurrence_type = 'weekdays'::text AND interval_days IS NULL AND days_of_week IS NOT NULL AND cardinality(days_of_week) >= 1 AND cardinality(days_of_week) <= 7 AND days_of_week <@ ARRAY[1::smallint, 2::smallint, 3::smallint, 4::smallint, 5::smallint, 6::smallint, 7::smallint]", name='chk_schedule_recurrence'),
        CheckConstraint("recurrence_type = ANY (ARRAY['daily'::text, 'every_n_days'::text, 'weekdays'::text])", name='medication_schedules_recurrence_type_check'),
        CheckConstraint('valid_to IS NULL OR valid_to >= valid_from', name='chk_schedule_valid'),
        ForeignKeyConstraint(['medication_id'], ['medications.id'], ondelete='CASCADE', name='medication_schedules_medication_id_fkey'),
        PrimaryKeyConstraint('id', name='medication_schedules_pkey')
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    medication_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    recurrence_type: Mapped[str] = mapped_column(Text, nullable=False)
    times: Mapped[list[datetime.time]] = mapped_column(ARRAY(Time()), nullable=False)
    dose_amount: Mapped[decimal.Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    dose_unit: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    interval_days: Mapped[Optional[int]] = mapped_column(SmallInteger)
    days_of_week: Mapped[Optional[list[int]]] = mapped_column(ARRAY(SmallInteger()))
    dose_note: Mapped[Optional[str]] = mapped_column(Text)
    # Concentración de lo que hay en casa: mg por comprimido (o mg por ml en líquidos)
    concentration_amount: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 3))
    concentration_unit: Mapped[Optional[str]] = mapped_column(Text)
    valid_to: Mapped[Optional[datetime.date]] = mapped_column(Date)

    medication: Mapped['Medications'] = relationship('Medications', back_populates='medication_schedules')
    medication_logs: Mapped[list['MedicationLogs']] = relationship('MedicationLogs', back_populates='schedule')


class MedicationLogs(Base):
    __tablename__ = 'medication_logs'
    __table_args__ = (
        CheckConstraint("status <> 'given'::text OR given_at IS NOT NULL AND given_by IS NOT NULL AND dose_amount IS NOT NULL AND dose_unit IS NOT NULL", name='chk_log_given'),
        CheckConstraint("status = ANY (ARRAY['given'::text, 'skipped'::text, 'missed'::text])", name='medication_logs_status_check'),
        ForeignKeyConstraint(['given_by'], ['users.id'], name='medication_logs_given_by_fkey'),
        ForeignKeyConstraint(['medication_id'], ['medications.id'], ondelete='CASCADE', name='medication_logs_medication_id_fkey'),
        ForeignKeyConstraint(['schedule_id'], ['medication_schedules.id'], ondelete='SET NULL', name='medication_logs_schedule_id_fkey'),
        PrimaryKeyConstraint('id', name='medication_logs_pkey'),
        UniqueConstraint('medication_id', 'scheduled_at', name='uq_log_per_slot'),
        Index('idx_med_logs_time', 'medication_id', 'scheduled_at')
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    medication_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    scheduled_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    schedule_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    given_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    given_by: Mapped[Optional[int]] = mapped_column(BigInteger)
    dose_amount: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(8, 2))
    dose_unit: Mapped[Optional[str]] = mapped_column(Text)
    concentration_amount: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 3))  # vigente al dar la toma
    concentration_unit: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    users: Mapped[Optional['Users']] = relationship('Users', back_populates='medication_logs')
    medication: Mapped['Medications'] = relationship('Medications', back_populates='medication_logs')
    schedule: Mapped[Optional['MedicationSchedules']] = relationship('MedicationSchedules', back_populates='medication_logs')