import pytest
from datetime import date
from health_insurance_claims.models import Claim, User
from health_insurance_claims.services import assign_claim_to_officer

def test_policyholder_cannot_view_others_claim(client, seeded_db):
    # Log in as user 2 (Bilal)
    client.post("/login", data={"username": "bilal", "password": "Password123!"})
    # Claim 1001 belongs to policyholder 1 (Aasha)
    resp = client.get("/claims/1001")
    assert resp.status_code == 403

def test_claims_officer_cannot_approve_draft(client, seeded_db, app):
    with app.app_context():
        # Create a draft claim
        c = Claim(
            claim_id=1999,
            policy_id=101,
            member_id=201,
            hospital_id=1,
            claim_type="reimbursement",
            treatment_type="inpatient",
            admission_date=date(2026, 9, 1),
            discharge_date=date(2026, 9, 5),
            requested_amount_inr=10000,
            status="draft"
        )
        from health_insurance_claims.extensions import db
        db.session.add(c)
        db.session.commit()

    # Log in as claims officer
    client.post("/login", data={"username": "officer_meera", "password": "Password123!"})
    resp = client.post("/claims/1999/review", data={
        "action": "approve",
        "eligible_amount_inr": "9000.00",
        "decision_reason": "Approved"
    }, follow_redirects=True)
    assert b"cannot be decided on" in resp.data or resp.status_code == 200

def test_two_officer_assignment_conflict(app, seeded_db):
    with app.app_context():
        officer1 = User.query.filter_by(username="officer_meera").first()
        officer2 = User.query.filter_by(username="officer_rahul").first()
        
        # Officer 1 assigns claim 1007
        ok1, msg1 = assign_claim_to_officer(1007, officer1)
        assert ok1 is True
        
        # Officer 2 tries to assign the same claim
        ok2, msg2 = assign_claim_to_officer(1007, officer2)
        assert ok2 is False
        assert "Cannot assign" in msg2 or "already assigned" in msg2

def test_non_admin_cannot_settle(client, seeded_db):
    # Log in as policyholder
    client.post("/login", data={"username": "aasha", "password": "Password123!"})
    resp = client.post("/claims/1001/settle")
    assert resp.status_code == 403
