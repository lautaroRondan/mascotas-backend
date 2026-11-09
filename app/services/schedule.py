"""Calcula qué tomas le tocan a un tratamiento en un día.

Lo usan el registro de tomas y, más adelante, el generador de avisos.
"""
from datetime import date, datetime, tzinfo

from app.models import MedicationSchedules, Medications


def applies_on(s: MedicationSchedules, day: date, start_date: date) -> bool:
    """¿Este tramo (frecuencia + horarios + dosis) rige ese día?"""
    if day < s.valid_from or (s.valid_to is not None and day > s.valid_to):
        return False
    if s.recurrence_type == "daily":
        return True
    if s.recurrence_type == "every_n_days":
        # Se cuenta desde el inicio del tratamiento (medications.start_date),
        # así un cambio de dosis no reinicia el ciclo.
        return (day - start_date).days % s.interval_days == 0
    # weekdays: 1 = lunes ... 7 = domingo
    return day.isoweekday() in (s.days_of_week or [])


def slots_for_day(med: Medications, day: date, tz: tzinfo) -> list[tuple[datetime, MedicationSchedules]]:
    """Tomas programadas de ese día, como (instante con zona horaria, tramo)."""
    if day < med.start_date or (med.end_date is not None and day > med.end_date):
        return []
    slots = []
    for s in med.medication_schedules:
        if applies_on(s, day, med.start_date):
            for t in s.times:
                slots.append((datetime.combine(day, t.replace(second=0, microsecond=0), tzinfo=tz), s))
    return sorted(slots, key=lambda item: item[0])