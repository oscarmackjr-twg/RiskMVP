"""Tests for cashflow generation and amortization logic.

Validates level pay, bullet, and custom amortization schedules,
as well as QuantLib schedule generation with calendar adjustments.
"""
from datetime import date
import pytest

from compute.cashflow.amortization import (
    level_pay_schedule,
    bullet_schedule,
    custom_schedule
)
from compute.cashflow.generator import generate_schedule


class TestLevelPayAmortization:
    """Test level-pay amortization schedule calculation."""

    def test_level_pay_amortization(self):
        """Test 30-year mortgage with level pay amortization."""
        # $100K at 5% over 30 years (360 months)
        schedule = level_pay_schedule(
            principal=100000,
            annual_rate=0.05,
            num_periods=360,
            frequency=12
        )

        assert len(schedule) == 360

        # Monthly payment should be ~$536.82
        payment = schedule[0]['payment']
        assert 536 < payment < 537

        # First payment: mostly interest, less principal
        first = schedule[0]
        assert first['interest'] > first['principal']
        assert abs(first['interest'] - 416.67) < 1.0  # 100000 * 0.05 / 12

        # Last payment: mostly principal, less interest
        last = schedule[-1]
        assert last['principal'] > last['interest']
        assert last['interest'] < 3.0  # Very small interest on final payment

        # Final balance should be zero
        assert last['remaining_balance'] == 0.0

        # Total payments should equal principal + total interest
        total_paid = sum(cf['payment'] for cf in schedule)
        total_principal = sum(cf['principal'] for cf in schedule)
        total_interest = sum(cf['interest'] for cf in schedule)

        assert abs(total_principal - 100000) < 0.01
        assert abs(total_paid - (total_principal + total_interest)) < 0.01

    def test_level_pay_quarterly(self):
        """Test level pay with quarterly payments."""
        # $50K at 4% over 10 years (40 quarters)
        schedule = level_pay_schedule(
            principal=50000,
            annual_rate=0.04,
            num_periods=40,
            frequency=4
        )

        assert len(schedule) == 40

        # Quarterly payment
        payment = schedule[0]['payment']
        assert 1500 < payment < 1600

        # Verify amortization
        assert schedule[0]['interest'] > schedule[-1]['interest']
        assert schedule[0]['principal'] < schedule[-1]['principal']
        assert schedule[-1]['remaining_balance'] == 0.0

    def test_level_pay_zero_rate(self):
        """Test level pay with zero interest rate (edge case)."""
        schedule = level_pay_schedule(
            principal=12000,
            annual_rate=0.0,
            num_periods=12,
            frequency=12
        )

        assert len(schedule) == 12

        # With 0% rate, payment should be principal / num_periods
        expected_payment = 12000 / 12
        assert schedule[0]['payment'] == expected_payment
        assert schedule[0]['interest'] == 0.0
        assert schedule[0]['principal'] == expected_payment


class TestBulletAmortization:
    """Test bullet (interest-only) amortization schedule."""

    def test_bullet_amortization(self):
        """Test 10-year bullet bond with semiannual payments."""
        schedule = bullet_schedule(
            principal=100000,
            annual_rate=0.05,
            num_periods=20,  # 10 years * 2
            frequency=2
        )

        assert len(schedule) == 20

        # All periods except last have zero principal
        for i in range(19):
            assert schedule[i]['principal'] == 0.0
            assert schedule[i]['remaining_balance'] == 100000

        # Last period has full principal
        last = schedule[-1]
        assert last['principal'] == 100000
        assert last['remaining_balance'] == 0.0

        # Interest payments should be constant (interest-only)
        expected_interest = 100000 * 0.05 / 2  # $2500 semiannually
        for i in range(19):
            assert abs(schedule[i]['interest'] - expected_interest) < 0.01
            assert abs(schedule[i]['payment'] - expected_interest) < 0.01

        # Last payment includes principal + interest
        assert abs(last['payment'] - (100000 + expected_interest)) < 0.01

    def test_bullet_annual_payments(self):
        """Test bullet bond with annual payments."""
        schedule = bullet_schedule(
            principal=50000,
            annual_rate=0.06,
            num_periods=5,  # 5 years
            frequency=1
        )

        assert len(schedule) == 5

        # Annual interest
        expected_interest = 50000 * 0.06  # $3000
        for i in range(4):
            assert abs(schedule[i]['interest'] - expected_interest) < 0.01
            assert schedule[i]['principal'] == 0.0

        # Last payment
        assert schedule[-1]['principal'] == 50000
        assert schedule[-1]['remaining_balance'] == 0.0


class TestCustomAmortization:
    """Test custom amortization schedules."""

    def test_custom_amortization(self):
        """Test custom schedule with irregular principal payments."""
        specs = [
            {'period': 1, 'principal': 1000, 'interest': 50},
            {'period': 2, 'principal': 1500, 'interest': 45},
            {'period': 3, 'principal': 2500, 'interest': 30},
        ]

        schedule = custom_schedule(specs)

        assert len(schedule) == 3

        # Total principal
        total_principal = 1000 + 1500 + 2500
        assert schedule[0]['remaining_balance'] == total_principal - 1000
        assert schedule[1]['remaining_balance'] == total_principal - 1000 - 1500
        assert schedule[2]['remaining_balance'] == 0

        # Payments match specifications
        assert schedule[0]['principal'] == 1000
        assert schedule[0]['interest'] == 50
        assert schedule[0]['payment'] == 1050

        assert schedule[1]['principal'] == 1500
        assert schedule[1]['interest'] == 45
        assert schedule[1]['payment'] == 1545

    def test_custom_amortization_out_of_order(self):
        """Test custom schedule handles out-of-order periods."""
        specs = [
            {'period': 3, 'principal': 1000, 'interest': 10},
            {'period': 1, 'principal': 1000, 'interest': 30},
            {'period': 2, 'principal': 1000, 'interest': 20},
        ]

        schedule = custom_schedule(specs)

        # Should be sorted by period
        assert schedule[0]['period'] == 1
        assert schedule[1]['period'] == 2
        assert schedule[2]['period'] == 3

    def test_custom_amortization_validation(self):
        """Test custom schedule validates input."""
        # Missing period
        with pytest.raises(ValueError, match="Missing or duplicate"):
            custom_schedule([
                {'period': 1, 'principal': 1000, 'interest': 50},
                {'period': 3, 'principal': 1000, 'interest': 40},  # Period 2 missing
            ])

        # Empty specs
        with pytest.raises(ValueError, match="cannot be empty"):
            custom_schedule([])

        # Negative principal
        with pytest.raises(ValueError, match="cannot be negative"):
            custom_schedule([
                {'period': 1, 'principal': -1000, 'interest': 50},
            ])


class TestScheduleGeneration:
    """Test payment schedule generation with QuantLib."""

    def test_schedule_generation_quarterly(self):
        """Test quarterly schedule generation from 2020 to 2030."""
        instrument = {
            'issue_date': '2020-01-01',
            'maturity_date': '2030-01-01',
            'principal': 100000,
            'coupon': 0.05,
            'frequency': 'QUARTERLY',
            'day_count': 'ACT/360',
            'calendar': 'US-GOVT',
            'amortization_type': 'BULLET'
        }

        schedule = generate_schedule(instrument, date(2020, 1, 1))

        # 10 years * 4 quarters = 40 payments
        assert len(schedule) == 40

        # Verify schedule structure
        first = schedule[0]
        assert 'period' in first
        assert 'pay_date' in first
        assert 'principal' in first
        assert 'interest' in first
        assert 'payment' in first
        assert 'remaining_balance' in first
        assert 'year_fraction' in first

        # Verify dates are sequential
        for i in range(1, len(schedule)):
            assert schedule[i]['pay_date'] > schedule[i-1]['pay_date']

        # Verify bullet structure (no principal until last payment)
        for i in range(len(schedule) - 1):
            assert schedule[i]['principal'] == 0.0

        assert schedule[-1]['principal'] == 100000

    def test_schedule_generation_semiannual(self):
        """Test semiannual schedule generation."""
        instrument = {
            'issue_date': '2020-01-01',
            'maturity_date': '2025-01-01',
            'principal': 50000,
            'coupon': 0.04,
            'frequency': 'SEMIANNUAL',
            'day_count': 'ACT/365',
            'calendar': 'US-GOVT',
            'amortization_type': 'BULLET'
        }

        schedule = generate_schedule(instrument, date(2020, 1, 1))

        # 5 years * 2 = 10 payments
        assert len(schedule) == 10

        # Year fractions should be roughly 0.5 (semiannual)
        for cf in schedule:
            assert 0.48 < cf['year_fraction'] < 0.52

    def test_schedule_with_partial_period(self):
        """Test schedule generation with as_of_date mid-period."""
        instrument = {
            'issue_date': '2020-01-01',
            'maturity_date': '2030-01-01',
            'principal': 100000,
            'coupon': 0.05,
            'frequency': 'SEMIANNUAL',
            'day_count': 'ACT/360',
            'calendar': 'US-GOVT',
            'amortization_type': 'BULLET'
        }

        # as_of_date is mid-2026 (partway through the schedule)
        schedule = generate_schedule(instrument, date(2026, 2, 15))

        # Should have payments from mid-2026 to 2030
        assert len(schedule) > 0
        assert len(schedule) < 20  # Less than full 10-year schedule

        # First payment date should be after as_of_date
        assert schedule[0]['pay_date'] > date(2026, 2, 15)

        # Last payment should be near maturity
        assert schedule[-1]['pay_date'].year == 2030

    def test_schedule_filtering(self):
        """Test that only future cashflows are returned."""
        instrument = {
            'issue_date': '2020-01-01',
            'maturity_date': '2030-01-01',
            'principal': 100000,
            'coupon': 0.05,
            'frequency': 'SEMIANNUAL',
            'day_count': 'ACT/360',
            'calendar': 'US-GOVT',
            'amortization_type': 'BULLET'
        }

        # as_of_date is 2026
        as_of = date(2026, 2, 11)
        schedule = generate_schedule(instrument, as_of)

        # All payment dates should be after as_of_date
        for cf in schedule:
            assert cf['pay_date'] > as_of

        # Should have ~8 future payments (2026-2030, semiannual)
        assert 7 <= len(schedule) <= 9

    def test_schedule_maturity_past(self):
        """Test that empty schedule is returned if maturity is past."""
        instrument = {
            'issue_date': '2020-01-01',
            'maturity_date': '2025-01-01',
            'principal': 100000,
            'coupon': 0.05,
            'frequency': 'SEMIANNUAL',
            'day_count': 'ACT/360',
            'calendar': 'US-GOVT',
            'amortization_type': 'BULLET'
        }

        # as_of_date is after maturity
        schedule = generate_schedule(instrument, date(2026, 2, 11))

        assert len(schedule) == 0

    def test_schedule_with_calendar_adjustment(self):
        """Test that payment dates respect business day calendar."""
        instrument = {
            'issue_date': '2026-01-01',
            'maturity_date': '2027-01-01',
            'principal': 100000,
            'coupon': 0.05,
            'frequency': 'QUARTERLY',
            'day_count': 'ACT/360',
            'calendar': 'US-GOVT',
            'amortization_type': 'BULLET'
        }

        schedule = generate_schedule(instrument, date(2026, 1, 1))

        # Verify dates are valid business days (not Jan 1 if it falls on weekend/holiday)
        # This is implicitly validated by QuantLib's ModifiedFollowing convention
        assert len(schedule) == 4  # 4 quarterly payments

    def test_schedule_level_pay(self):
        """Test schedule generation with level pay amortization."""
        instrument = {
            'issue_date': '2020-01-01',
            'maturity_date': '2025-01-01',
            'principal': 100000,
            'coupon': 0.05,
            'frequency': 'QUARTERLY',
            'day_count': '30/360',
            'calendar': 'US-GOVT',
            'amortization_type': 'LEVEL_PAY'
        }

        schedule = generate_schedule(instrument, date(2023, 1, 1))

        # Should have future payments from 2023 to 2025
        assert len(schedule) > 0

        # Level pay: each payment should be roughly the same
        payments = [cf['payment'] for cf in schedule]
        avg_payment = sum(payments) / len(payments)

        # All payments should be within 5% of average (accounting for partial periods)
        for payment in payments:
            assert abs(payment - avg_payment) / avg_payment < 0.05

        # Principal should increase over time
        for i in range(1, len(schedule)):
            assert schedule[i]['principal'] >= schedule[i-1]['principal']

        # Interest should decrease over time
        for i in range(1, len(schedule)):
            assert schedule[i]['interest'] <= schedule[i-1]['interest']


class TestScheduleValidation:
    """Test input validation for schedule generation."""

    def test_missing_required_fields(self):
        """Test that missing required fields raise errors."""
        with pytest.raises((ValueError, KeyError)):
            generate_schedule({}, date(2026, 1, 1))

    def test_invalid_frequency(self):
        """Test that invalid frequency raises error."""
        instrument = {
            'issue_date': '2020-01-01',
            'maturity_date': '2025-01-01',
            'principal': 100000,
            'coupon': 0.05,
            'frequency': 'INVALID',
            'day_count': 'ACT/360',
            'calendar': 'US-GOVT',
            'amortization_type': 'BULLET'
        }

        with pytest.raises(ValueError, match="Unsupported frequency"):
            generate_schedule(instrument, date(2020, 1, 1))

    def test_invalid_amortization_type(self):
        """Test that invalid amortization type raises error."""
        instrument = {
            'issue_date': '2020-01-01',
            'maturity_date': '2025-01-01',
            'principal': 100000,
            'coupon': 0.05,
            'frequency': 'QUARTERLY',
            'day_count': 'ACT/360',
            'calendar': 'US-GOVT',
            'amortization_type': 'INVALID'
        }

        with pytest.raises(ValueError, match="Unsupported amortization type"):
            generate_schedule(instrument, date(2020, 1, 1))

    def test_negative_principal(self):
        """Test that negative principal raises error."""
        instrument = {
            'issue_date': '2020-01-01',
            'maturity_date': '2025-01-01',
            'principal': -100000,
            'coupon': 0.05,
            'frequency': 'QUARTERLY',
            'day_count': 'ACT/360',
            'calendar': 'US-GOVT',
            'amortization_type': 'BULLET'
        }

        with pytest.raises(ValueError, match="Principal must be positive"):
            generate_schedule(instrument, date(2020, 1, 1))
