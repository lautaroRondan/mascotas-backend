from typing import Optional, TYPE_CHECKING
import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKeyConstraint, Identity, Index, PrimaryKeyConstraint, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.medications import Medications
    from app.models.pets import Pets
    from app.models.users import Users
    from app.models.veterinary import Vaccines, VetVisits


class Reminders(Base):
    __tablename__ = 'reminders'
    __table_args__ = (
        CheckConstraint("(kind = ANY (ARRAY['medication'::text, 'medication_followup'::text, 'stock_low'::text, 'prescription_expiry'::text, 'concentration_change'::text])) = (medication_id IS NOT NULL)", name='chk_reminder_ref'),
        CheckConstraint("channel = ANY (ARRAY['email'::text, 'push'::text])", name='reminders_channel_check'),
        CheckConstraint("kind = ANY (ARRAY['vet_visit'::text, 'vaccine'::text, 'medication'::text, 'medication_followup'::text, 'stock_low'::text, 'prescription_expiry'::text, 'concentration_change'::text])", name='reminders_kind_check'),
        CheckConstraint("status = ANY (ARRAY['pending'::text, 'sent'::text, 'cancelled'::text])", name='reminders_status_check'),
        ForeignKeyConstraint(['medication_id'], ['medications.id'], ondelete='CASCADE', name='reminders_medication_id_fkey'),
        ForeignKeyConstraint(['pet_id'], ['pets.id'], ondelete='CASCADE', name='reminders_pet_id_fkey'),
        ForeignKeyConstraint(['recipient_id'], ['users.id'], ondelete='CASCADE', name='reminders_recipient_id_fkey'),
        ForeignKeyConstraint(['vaccine_id'], ['vaccines.id'], ondelete='CASCADE', name='reminders_vaccine_id_fkey'),
        ForeignKeyConstraint(['vet_visit_id'], ['vet_visits.id'], ondelete='CASCADE', name='reminders_vet_visit_id_fkey'),
        PrimaryKeyConstraint('id', name='reminders_pkey'),
        UniqueConstraint('action_token_hash', name='reminders_action_token_hash_key'),
        UniqueConstraint('dedupe_key', name='reminders_dedupe_key_key'),
        Index('idx_reminders_due', 'send_at', postgresql_where="(status = 'pending'::text)"),
        Index('idx_reminders_med', 'medication_id', 'scheduled_for', postgresql_where='(medication_id IS NOT NULL)')
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    recipient_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pet_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    scheduled_for: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    send_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'email'::text"))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'::text"))
    dedupe_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    medication_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    vet_visit_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    vaccine_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    sent_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    action_token_hash: Mapped[Optional[str]] = mapped_column(Text)
    action_expires_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    action_used_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    medication: Mapped[Optional['Medications']] = relationship('Medications', back_populates='reminders')
    pet: Mapped['Pets'] = relationship('Pets', back_populates='reminders')
    recipient: Mapped['Users'] = relationship('Users', back_populates='reminders')
    vaccine: Mapped[Optional['Vaccines']] = relationship('Vaccines', back_populates='reminders')
    vet_visit: Mapped[Optional['VetVisits']] = relationship('VetVisits', back_populates='reminders')