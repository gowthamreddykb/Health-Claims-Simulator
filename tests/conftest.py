import pytest
from datetime import date, timedelta
from decimal import Decimal
from werkzeug.security import generate_password_hash

from health_insurance_claims.app import create_app
from health_insurance_claims.config import TestConfig
from health_insurance_claims.extensions import db
from health_insurance_claims.models import (
    User, Hospital, Plan, Policy, Member, Claim,
    ClaimDocument, ClaimHistory, Settlement
)

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def seeded_db(app):
    """Seed test database with representative data for all 4 roles."""
    with app.app_context():
        # Hospitals
        h1 = Hospital(hospital_id=1, name="CityCare Hospital", city="Puttaparthi", network_status=True)
        h2 = Hospital(hospital_id=2, name="Lotus Medical Centre", city="Anantapur", network_status=True)
        h3 = Hospital(hospital_id=3, name="Green Valley Hospital", city="Kadiri", network_status=False)
        db.session.add_all([h1, h2, h3])
        
        # Plans
        p1 = Plan(
            plan_id=1,
            plan_name="Essential Care",
            covered_treatment_types="inpatient",
            annual_limit_inr=Decimal("100000.00"),
            deductible_inr=Decimal("2000.00"),
            copay_percent=Decimal("10.00")
        )
        p2 = Plan(
            plan_id=2,
            plan_name="Plus Care",
            covered_treatment_types="inpatient|daycare",
            annual_limit_inr=Decimal("200000.00"),
            deductible_inr=Decimal("1000.00"),
            copay_percent=Decimal("5.00")
        )
        db.session.add_all([p1, p2])
        
        # Users (all 4 roles)
        pwd_hash = generate_password_hash("Password123!")
        u_holder1 = User(user_id=1, username="aasha", display_name="Aasha Rao", role="policyholder", password_hash=pwd_hash)
        u_holder2 = User(user_id=2, username="bilal", display_name="Bilal Khan", role="policyholder", password_hash=pwd_hash)
        u_hosp = User(user_id=9, username="city_hospital", display_name="CityCare Desk", role="hospital", hospital_id=1, password_hash=pwd_hash)
        u_officer1 = User(user_id=12, username="officer_meera", display_name="Meera Shah", role="claims_officer", password_hash=pwd_hash)
        u_officer2 = User(user_id=13, username="officer_rahul", display_name="Rahul Sen", role="claims_officer", password_hash=pwd_hash)
        u_admin = User(user_id=14, username="admin_demo", display_name="Demo Administrator", role="admin", password_hash=pwd_hash)
        db.session.add_all([u_holder1, u_holder2, u_hosp, u_officer1, u_officer2, u_admin])
        db.session.flush()

        # Policies
        pol1 = Policy(policy_id=101, holder_user_id=1, plan_id=1, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), status="active")
        pol2 = Policy(policy_id=102, holder_user_id=2, plan_id=2, start_date=date(2026, 4, 1), end_date=date(2027, 3, 31), status="active")
        pol_expired = Policy(policy_id=104, holder_user_id=1, plan_id=1, start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), status="expired")
        db.session.add_all([pol1, pol2, pol_expired])
        db.session.flush()

        # Members
        m1 = Member(member_id=201, policy_id=101, display_name="Aasha Rao", relationship_type="self")
        m2 = Member(member_id=202, policy_id=101, display_name="Nikhil Rao", relationship_type="spouse")
        m3 = Member(member_id=203, policy_id=102, display_name="Bilal Khan", relationship_type="self")
        db.session.add_all([m1, m2, m3])
        db.session.flush()

        # Seed Claims
        c1 = Claim(
            claim_id=1001,
            policy_id=101,
            member_id=201,
            hospital_id=1,
            claim_type="cashless",
            treatment_type="inpatient",
            admission_date=date(2026, 8, 10),
            discharge_date=date(2026, 8, 13),
            requested_amount_inr=Decimal("28000.00"),
            status="paid",
            eligible_amount_inr=Decimal("26000.00"),
            officer_user_id=12,
            payment_recorded_date=date(2026, 8, 14)
        )
        s1 = Settlement(
            claim_id=1001,
            payee_type="hospital",
            amount_inr=Decimal("21600.00"),
            recorded_by_user_id=14,
            recorded_date=date(2026, 8, 14)
        )
        db.session.add_all([c1, s1])

        # Claim in submitted state ready for officer assignment
        c2 = Claim(
            claim_id=1007,
            policy_id=101,
            member_id=201,
            hospital_id=1,
            claim_type="reimbursement",
            treatment_type="inpatient",
            admission_date=date(2026, 10, 10),
            discharge_date=date(2026, 10, 14),
            requested_amount_inr=Decimal("30000.00"),
            status="submitted"
        )
        db.session.add(c2)

        # Claim in review assigned to officer 12
        c3 = Claim(
            claim_id=1004,
            policy_id=101,
            member_id=202,
            hospital_id=1,
            claim_type="reimbursement",
            treatment_type="inpatient",
            admission_date=date(2026, 10, 2),
            discharge_date=date(2026, 10, 5),
            requested_amount_inr=Decimal("42000.00"),
            status="in_review",
            officer_user_id=12
        )
        db.session.add(c3)

        db.session.commit()
    return app
