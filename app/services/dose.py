from decimal import Decimal


def mg_per_dose(dose_amount: Decimal | None, dose_unit: str | None,
                concentration_amount: Decimal | None) -> Decimal | None:
    """Miligramos de una toma: 0,5 comprimidos de 75 mg = 37,5 mg.

    Solo se calcula en comprimidos (mg por comprimido) y en ml (mg por ml).
    En gotas no se puede, porque la equivalencia gotas/ml depende del frasco.
    """
    if dose_amount is None or concentration_amount is None:
        return None
    if dose_unit not in ("comprimido", "ml"):
        return None
    return (Decimal(dose_amount) * Decimal(concentration_amount)).quantize(Decimal("0.01"))