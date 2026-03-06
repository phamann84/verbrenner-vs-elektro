from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class LoanSchedule:
    annual_payments: list[float]
    remaining_balance_at_horizon: float


def _d(value: float | int | str | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def annuity_monthly_payment(principal: float, annual_interest_rate: float, months: int) -> float:
    if months <= 0:
        raise ValueError("months muss > 0 sein")
    if principal <= 0:
        return 0.0
    principal_dec = _d(principal)
    monthly_rate = _d(annual_interest_rate) / _d(12)
    if monthly_rate == 0:
        return float(principal_dec / _d(months))
    factor = (_d(1) + monthly_rate) ** months
    return float(principal_dec * monthly_rate * factor / (factor - _d(1)))


def annual_loan_cashflows(
    *,
    principal: float,
    annual_interest_rate: float,
    term_years: int,
    horizon_years: int,
) -> LoanSchedule:
    if principal <= 0 or term_years <= 0 or horizon_years <= 0:
        return LoanSchedule(annual_payments=[0.0] * max(horizon_years, 0), remaining_balance_at_horizon=0.0)

    total_months = term_years * 12
    horizon_months = horizon_years * 12
    monthly_payment = _d(annuity_monthly_payment(principal, annual_interest_rate, total_months))
    monthly_rate = _d(annual_interest_rate) / _d(12)

    annual_payments = [Decimal("0") for _ in range(horizon_years)]
    balance = _d(principal)

    for month in range(1, min(total_months, horizon_months) + 1):
        interest = balance * monthly_rate
        principal_paid = monthly_payment - interest
        if principal_paid > balance:
            principal_paid = balance
            monthly_effective_payment = interest + principal_paid
        else:
            monthly_effective_payment = monthly_payment

        balance -= principal_paid
        year_idx = (month - 1) // 12
        annual_payments[year_idx] += monthly_effective_payment

        if balance <= _d("1e-9"):
            balance = Decimal("0")
            break

    return LoanSchedule(
        annual_payments=[float(payment) for payment in annual_payments],
        remaining_balance_at_horizon=float(max(Decimal("0"), balance)),
    )
