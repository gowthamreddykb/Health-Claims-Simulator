import pytest
from datetime import date
from decimal import Decimal
from health_insurance_claims.models import Claim, Plan, Policy, Settlement, User
from health_insurance_claims.services import (
    calculate_remaining_cover, calculate_claim_payout,
    process_review_decision, record_simulated_settlement
)

def test_payout_formula_exact(app, seeded_db):
    with app.app_context():
        # Plan 1: deductible = 2000, copay = 10%
        plan1 = Plan.query.get(1)
        res = calculate_claim_payout(Decimal("26000.00"), plan1)
        # (26000 - 2000) * (1 - 0.10) = 24000 * 0.90 = 21600.00
        assert res["calculated_payout"] == Decimal("21600.00")

        # Plan 2: deductible = 1000, copay = 5%
        plan2 = Plan.query.get(2)
        res2 = calculate_claim_payout(Decimal("18000.00"), plan2)
        # (18000 - 1000) * (1 - 0.05) = 17000 * 0.95 = 16150.00
        assert res2["calculated_payout"] == Decimal("16150.00")

def test_remaining_cover_calculation(app, seeded_db):
    with app.app_context():
        # Policy 101 has annual limit 100000.00, claim 1001 paid settlement 21600.00
        pol1 = Policy.query.get(101)
        rem = calculate_remaining_cover(pol1)
        assert rem == Decimal("78400.00")

def test_reject_approval_above_requested_amount(app, seeded_db):
    with app.app_context():
        officer = User.query.filter_by(username="officer_meera").first()
        # Claim 1004 has requested amount 42000.00
        ok, msg = process_review_decision(
            claim_id=1004,
            officer=officer,
            action="approve",
            decision_reason="Approving full amount",
            eligible_amount=Decimal("50000.00")
        )
        assert ok is False
        assert "cannot exceed requested amount" in msg

def test_reject_approval_without_reason(app, seeded_db):
    with app.app_context():
        officer = User.query.filter_by(username="officer_meera").first()
        ok, msg = process_review_decision(
            claim_id=1004,
            officer=officer,
            action="approve",
            decision_reason="",
            eligible_amount=Decimal("35000.00")
        )
        assert ok is False
        assert "written reason" in msg

def test_settlement_creates_record_and_updates_status(app, seeded_db):
    with app.app_context():
        officer = User.query.filter_by(username="officer_meera").first()
        admin = User.query.filter_by(username="admin_demo").first()
        
        # Approve claim 1004 first
        ok, _ = process_review_decision(
            claim_id=1004,
            officer=officer,
            action="approve",
            decision_reason="Valid inpatient treatment under policy cover.",
            eligible_amount=Decimal("30000.00")
        )
        assert ok is True
        
        # Record settlement as Admin
        settled, msg = record_simulated_settlement(1004, admin)
        assert settled is True
        
        claim = Claim.query.get(1004)
        assert claim.status == "paid"
        assert claim.payment_recorded_date is not None
        assert claim.settlement is not None
        # Claim 1004 is reimbursement -> payee is policyholder
        assert claim.settlement.payee_type == "policyholder"
        # Formula: (30000 - 2000) * 0.9 = 25200.00
        assert claim.settlement.amount_inr == Decimal("25200.00")
