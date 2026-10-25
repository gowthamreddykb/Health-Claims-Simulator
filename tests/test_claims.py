import pytest
from datetime import date, timedelta
from decimal import Decimal
from health_insurance_claims.models import Claim, Policy, Member
from health_insurance_claims.services import detect_potential_duplicates

def test_create_reimbursement_draft(client, seeded_db):
    client.post("/login", data={"username": "aasha", "password": "Password123!"})
    resp = client.post("/claims/new", data={
        "policy_id": 101,
        "member_id": 201,
        "hospital_id": 1,
        "claim_type": "reimbursement",
        "treatment_type": "inpatient",
        "admission_date": "2026-09-01",
        "discharge_date": "2026-09-05",
        "requested_amount_inr": "15000.00",
        "description": "Fever and infection treatment",
        "save_draft": "Save Draft"
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Draft" in resp.data

def test_reject_cross_policy_member(client, seeded_db):
    client.post("/login", data={"username": "aasha", "password": "Password123!"})
    # Member 203 belongs to policy 102, not policy 101!
    resp = client.post("/claims/new", data={
        "policy_id": 101,
        "member_id": 203,
        "hospital_id": 1,
        "claim_type": "reimbursement",
        "treatment_type": "inpatient",
        "admission_date": "2026-09-01",
        "discharge_date": "2026-09-05",
        "requested_amount_inr": "15000.00",
        "submit_claim": "Submit Claim"
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Selected member does not belong to the selected policy" in resp.data

def test_reject_cashless_at_non_network_hospital(client, seeded_db):
    client.post("/login", data={"username": "city_hospital", "password": "Password123!"})
    # Hospital 3 is non-network
    resp = client.post("/claims/new", data={
        "policy_id": 101,
        "member_id": 201,
        "hospital_id": 3,
        "claim_type": "cashless",
        "treatment_type": "inpatient",
        "admission_date": "2026-09-01",
        "discharge_date": "2026-09-05",
        "requested_amount_inr": "20000.00",
        "submit_claim": "Submit Claim"
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"only create claims for their own hospital" in resp.data or b"network" in resp.data

def test_detect_duplicate_claim(app, seeded_db):
    with app.app_context():
        # Claim 1007 is for member 201 on 2026-10-10, hosp 1, 30000.00
        existing = Claim.query.get(1007)
        new_claim = Claim(
            policy_id=101,
            member_id=201,
            hospital_id=1,
            claim_type="reimbursement",
            treatment_type="inpatient",
            admission_date=date(2026, 10, 10),
            discharge_date=date(2026, 10, 14),
            requested_amount_inr=Decimal("30000.00"),
            status="draft"
        )
        dups = detect_potential_duplicates(new_claim)
        assert len(dups) > 0
        assert dups[0].claim_id == 1007

        # Case 1: Same member, same dates, but different hospital -> NOT duplicate
        diff_hosp_claim = Claim(
            policy_id=101,
            member_id=201,
            hospital_id=2,
            claim_type="reimbursement",
            treatment_type="inpatient",
            admission_date=date(2026, 10, 10),
            discharge_date=date(2026, 10, 14),
            requested_amount_inr=Decimal("30000.00"),
            status="draft"
        )
        assert len(detect_potential_duplicates(diff_hosp_claim)) == 0

        # Case 2: Same member, same hospital, but different amount -> NOT duplicate
        diff_amt_claim = Claim(
            policy_id=101,
            member_id=201,
            hospital_id=1,
            claim_type="reimbursement",
            treatment_type="inpatient",
            admission_date=date(2026, 10, 10),
            discharge_date=date(2026, 10, 14),
            requested_amount_inr=Decimal("50000.00"),
            status="draft"
        )
        assert len(detect_potential_duplicates(diff_amt_claim)) == 0

        # Case 3: Same member, same amount, but different dates -> NOT duplicate
        diff_date_claim = Claim(
            policy_id=101,
            member_id=201,
            hospital_id=1,
            claim_type="reimbursement",
            treatment_type="inpatient",
            admission_date=date(2026, 10, 20),
            discharge_date=date(2026, 10, 24),
            requested_amount_inr=Decimal("30000.00"),
            status="draft"
        )
        assert len(detect_potential_duplicates(diff_date_claim)) == 0
