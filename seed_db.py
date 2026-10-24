#!/usr/bin/env python3
"""
Direct Database Seeding Script for Health Insurance Claims System
Creates all tables using SQLAlchemy ORM and populates the database records directly.
Usage:
  python seed_db.py
  python -m health_insurance_claims.seed_db
"""

import sys
import os
from datetime import date
from decimal import Decimal
from werkzeug.security import generate_password_hash

# Ensure directory is on sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

if __package__:
    from .app import create_app
    from .extensions import db
    from .models import (
        User, Hospital, Plan, Policy, Member, Claim,
        ClaimDocument, ClaimHistory, Settlement
    )
else:
    from app import create_app
    from extensions import db
    from models import (
        User, Hospital, Plan, Policy, Member, Claim,
        ClaimDocument, ClaimHistory, Settlement
    )

def seed_database(reset_existing: bool = False):
    app = create_app()
    with app.app_context():
        try:
            if reset_existing:
                print("[DB] Dropping existing database tables...")
                db.drop_all()

            print("[DB] Creating database tables (db.create_all())...")
            db.create_all()
        except Exception as conn_err:
            print(f"[DB] MySQL notice: {conn_err}")
            print("[DB] Falling back to local SQLite database 'health_claims.db'...")
            sqlite_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "health_claims.db")
            app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_db_path}"
            db.engine.dispose()
            if reset_existing:
                db.drop_all()
            db.create_all()

        if Hospital.query.count() > 0 and not reset_existing:
            print("[DB] Database already initialized with records. Skipping seed.")
            return

        print("[DB] Inserting records directly into database...")

        # 1. Hospitals
        hospitals = [
            Hospital(hospital_id=1, name="CityCare Hospital", city="Puttaparthi", network_status=True),
            Hospital(hospital_id=2, name="Lotus Medical Centre", city="Anantapur", network_status=True),
            Hospital(hospital_id=3, name="Green Valley Hospital", city="Kadiri", network_status=False),
            Hospital(hospital_id=4, name="Sri Sai Super Specialty Hospital", city="Puttaparthi", network_status=True),
            Hospital(hospital_id=5, name="Anantha Institute of Medical Sciences", city="Anantapur", network_status=True),
            Hospital(hospital_id=6, name="Dharmavaram Community Hospital", city="Dharmavaram", network_status=False),
            Hospital(hospital_id=7, name="Hindupur Care Clinic", city="Hindupur", network_status=True)
        ]
        db.session.add_all(hospitals)
        db.session.flush()

        # 2. Plans
        plans = [
            Plan(plan_id=1, plan_name="Essential Care", covered_treatment_types="inpatient", annual_limit_inr=Decimal("100000.00"), deductible_inr=Decimal("2000.00"), copay_percent=Decimal("10.00")),
            Plan(plan_id=2, plan_name="Plus Care", covered_treatment_types="inpatient|daycare", annual_limit_inr=Decimal("200000.00"), deductible_inr=Decimal("1000.00"), copay_percent=Decimal("5.00")),
            Plan(plan_id=3, plan_name="Comprehensive Shield", covered_treatment_types="inpatient|daycare", annual_limit_inr=Decimal("500000.00"), deductible_inr=Decimal("0.00"), copay_percent=Decimal("0.00"))
        ]
        db.session.add_all(plans)
        db.session.flush()

        # 3. Users
        pwd_hash = generate_password_hash("Password123!")
        users = [
            User(user_id=1, username="aasha", display_name="Aasha Rao", role="policyholder", password_hash=pwd_hash),
            User(user_id=2, username="bilal", display_name="Bilal Khan", role="policyholder", password_hash=pwd_hash),
            User(user_id=3, username="charan", display_name="Charan Reddy", role="policyholder", password_hash=pwd_hash),
            User(user_id=4, username="deepa", display_name="Deepa Nair", role="policyholder", password_hash=pwd_hash),
            User(user_id=5, username="eshan", display_name="Eshan Verma", role="policyholder", password_hash=pwd_hash),
            User(user_id=6, username="farida", display_name="Farida Parveen", role="policyholder", password_hash=pwd_hash),
            User(user_id=7, username="girish", display_name="Girish Kulkarni", role="policyholder", password_hash=pwd_hash),
            User(user_id=8, username="harini", display_name="Harini Iyer", role="policyholder", password_hash=pwd_hash),
            User(user_id=9, username="city_hospital", display_name="CityCare Desk", role="hospital", hospital_id=1, password_hash=pwd_hash),
            User(user_id=10, username="lotus_desk", display_name="Lotus Desk", role="hospital", hospital_id=2, password_hash=pwd_hash),
            User(user_id=11, username="green_desk", display_name="Green Valley Desk", role="hospital", hospital_id=3, password_hash=pwd_hash),
            User(user_id=12, username="officer_meera", display_name="Meera Shah", role="claims_officer", password_hash=pwd_hash),
            User(user_id=13, username="officer_rahul", display_name="Rahul Sen", role="claims_officer", password_hash=pwd_hash),
            User(user_id=14, username="admin_demo", display_name="Demo Administrator", role="admin", password_hash=pwd_hash)
        ]
        db.session.add_all(users)
        db.session.flush()

        # 4. Policies
        policies = [
            Policy(policy_id=101, holder_user_id=1, plan_id=1, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), status="active"),
            Policy(policy_id=102, holder_user_id=2, plan_id=2, start_date=date(2026, 4, 1), end_date=date(2027, 3, 31), status="active"),
            Policy(policy_id=103, holder_user_id=3, plan_id=3, start_date=date(2026, 6, 1), end_date=date(2027, 5, 31), status="active"),
            Policy(policy_id=104, holder_user_id=1, plan_id=1, start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), status="expired"),
            Policy(policy_id=105, holder_user_id=4, plan_id=2, start_date=date(2026, 2, 1), end_date=date(2027, 1, 31), status="active"),
            Policy(policy_id=106, holder_user_id=5, plan_id=1, start_date=date(2026, 3, 1), end_date=date(2027, 2, 28), status="active"),
            Policy(policy_id=107, holder_user_id=6, plan_id=3, start_date=date(2026, 1, 15), end_date=date(2027, 1, 14), status="active")
        ]
        db.session.add_all(policies)
        db.session.flush()

        # 5. Members
        members = [
            Member(member_id=201, policy_id=101, display_name="Aasha Rao", relationship="self"),
            Member(member_id=202, policy_id=101, display_name="Nikhil Rao", relationship="spouse"),
            Member(member_id=203, policy_id=102, display_name="Bilal Khan", relationship="self"),
            Member(member_id=204, policy_id=102, display_name="Zainab Khan", relationship="daughter"),
            Member(member_id=205, policy_id=103, display_name="Charan Reddy", relationship="self"),
            Member(member_id=206, policy_id=105, display_name="Deepa Nair", relationship="self"),
            Member(member_id=207, policy_id=106, display_name="Eshan Verma", relationship="self"),
            Member(member_id=208, policy_id=107, display_name="Farida Parveen", relationship="self")
        ]
        db.session.add_all(members)
        db.session.flush()

        # 6. Claims
        claims = [
            Claim(claim_id=1001, policy_id=101, member_id=201, hospital_id=1, claim_type="cashless", treatment_type="inpatient", admission_date=date(2026, 8, 10), discharge_date=date(2026, 8, 13), requested_amount_inr=Decimal("28000.00"), status="paid", eligible_amount_inr=Decimal("26000.00"), officer_user_id=12, payment_recorded_date=date(2026, 8, 14)),
            Claim(claim_id=1002, policy_id=102, member_id=203, hospital_id=2, claim_type="cashless", treatment_type="daycare", admission_date=date(2026, 9, 5), discharge_date=date(2026, 9, 5), requested_amount_inr=Decimal("15000.00"), status="paid", eligible_amount_inr=Decimal("15000.00"), officer_user_id=12, payment_recorded_date=date(2026, 9, 6)),
            Claim(claim_id=1003, policy_id=103, member_id=205, hospital_id=3, claim_type="reimbursement", treatment_type="inpatient", admission_date=date(2026, 9, 15), discharge_date=date(2026, 9, 18), requested_amount_inr=Decimal("54000.00"), status="approved", eligible_amount_inr=Decimal("50000.00"), officer_user_id=13),
            Claim(claim_id=1004, policy_id=101, member_id=202, hospital_id=1, claim_type="reimbursement", treatment_type="inpatient", admission_date=date(2026, 10, 2), discharge_date=date(2026, 10, 5), requested_amount_inr=Decimal("42000.00"), status="in_review", officer_user_id=12),
            Claim(claim_id=1005, policy_id=102, member_id=204, hospital_id=3, claim_type="reimbursement", treatment_type="inpatient", admission_date=date(2026, 10, 8), discharge_date=date(2026, 10, 10), requested_amount_inr=Decimal("18000.00"), status="more_info", officer_user_id=13),
            Claim(claim_id=1006, policy_id=103, member_id=205, hospital_id=1, claim_type="cashless", treatment_type="inpatient", admission_date=date(2026, 10, 12), discharge_date=date(2026, 10, 15), requested_amount_inr=Decimal("65000.00"), status="rejected", officer_user_id=12),
            Claim(claim_id=1007, policy_id=101, member_id=201, hospital_id=1, claim_type="reimbursement", treatment_type="inpatient", admission_date=date(2026, 10, 10), discharge_date=date(2026, 10, 14), requested_amount_inr=Decimal("30000.00"), status="submitted")
        ]
        db.session.add_all(claims)
        db.session.flush()

        # 7. Claim Documents
        docs = [
            ClaimDocument(claim_id=1001, document_type="hospital_bill", checklist_status="received"),
            ClaimDocument(claim_id=1001, document_type="discharge_summary", checklist_status="received"),
            ClaimDocument(claim_id=1002, document_type="hospital_bill", checklist_status="received"),
            ClaimDocument(claim_id=1003, document_type="hospital_bill", checklist_status="received"),
            ClaimDocument(claim_id=1003, document_type="discharge_summary", checklist_status="received"),
            ClaimDocument(claim_id=1004, document_type="hospital_bill", checklist_status="received"),
            ClaimDocument(claim_id=1004, document_type="discharge_summary", checklist_status="received"),
            ClaimDocument(claim_id=1005, document_type="hospital_bill", checklist_status="received"),
            ClaimDocument(claim_id=1005, document_type="discharge_summary", checklist_status="missing"),
            ClaimDocument(claim_id=1006, document_type="hospital_bill", checklist_status="received"),
            ClaimDocument(claim_id=1007, document_type="hospital_bill", checklist_status="received"),
            ClaimDocument(claim_id=1007, document_type="discharge_summary", checklist_status="missing")
        ]
        db.session.add_all(docs)

        # 8. Claim History
        histories = [
            ClaimHistory(claim_id=1001, sequence_no=1, from_status=None, to_status="submitted", actor_user_id=9, note="Cashless request submitted by hospital desk", event_date=date(2026, 8, 10)),
            ClaimHistory(claim_id=1001, sequence_no=2, from_status="submitted", to_status="in_review", actor_user_id=12, note="Officer Meera picked up claim", event_date=date(2026, 8, 11)),
            ClaimHistory(claim_id=1001, sequence_no=3, from_status="in_review", to_status="approved", actor_user_id=12, note="Approved eligible amount INR 26,000", event_date=date(2026, 8, 12)),
            ClaimHistory(claim_id=1001, sequence_no=4, from_status="approved", to_status="paid", actor_user_id=14, note="Simulated settlement payout completed to hospital", event_date=date(2026, 8, 14)),
            ClaimHistory(claim_id=1002, sequence_no=1, from_status=None, to_status="submitted", actor_user_id=10, note="Daycare cataract surgery cashless request", event_date=date(2026, 9, 5)),
            ClaimHistory(claim_id=1002, sequence_no=2, from_status="submitted", to_status="paid", actor_user_id=12, note="Fast-track approved and disbursed", event_date=date(2026, 9, 6)),
            ClaimHistory(claim_id=1003, sequence_no=1, from_status=None, to_status="submitted", actor_user_id=3, note="Reimbursement claim submitted post-discharge", event_date=date(2026, 9, 19)),
            ClaimHistory(claim_id=1003, sequence_no=2, from_status="submitted", to_status="approved", actor_user_id=13, note="Deductible 0 on Comprehensive Shield", event_date=date(2026, 9, 21)),
            ClaimHistory(claim_id=1004, sequence_no=1, from_status=None, to_status="submitted", actor_user_id=1, note="Submitted with bills and discharge summary", event_date=date(2026, 10, 6)),
            ClaimHistory(claim_id=1004, sequence_no=2, from_status="submitted", to_status="in_review", actor_user_id=12, note="Officer review in progress", event_date=date(2026, 10, 7)),
            ClaimHistory(claim_id=1005, sequence_no=1, from_status=None, to_status="submitted", actor_user_id=2, note="Submitted via policyholder portal", event_date=date(2026, 10, 11)),
            ClaimHistory(claim_id=1005, sequence_no=2, from_status="submitted", to_status="more_info", actor_user_id=13, note="Discharge summary is missing stamp from attending physician", event_date=date(2026, 10, 12)),
            ClaimHistory(claim_id=1006, sequence_no=1, from_status=None, to_status="submitted", actor_user_id=9, note="Pre-auth cashless requested", event_date=date(2026, 10, 12)),
            ClaimHistory(claim_id=1006, sequence_no=2, from_status="submitted", to_status="rejected", actor_user_id=12, note="Cosmetic procedure excluded under policy guidelines", event_date=date(2026, 10, 13)),
            ClaimHistory(claim_id=1007, sequence_no=1, from_status=None, to_status="submitted", actor_user_id=1, note="Emergency appendectomy reimbursement claim", event_date=date(2026, 10, 15))
        ]
        db.session.add_all(histories)

        # 9. Settlements
        settlements = [
            Settlement(claim_id=1001, payee_type="hospital", amount_inr=Decimal("21600.00"), recorded_by_user_id=14, recorded_date=date(2026, 8, 14)),
            Settlement(claim_id=1002, payee_type="hospital", amount_inr=Decimal("13300.00"), recorded_by_user_id=14, recorded_date=date(2026, 9, 6))
        ]
        db.session.add_all(settlements)

        db.session.commit()
        print("[DB] Database seeding completed successfully with all 9 entity models!")

if __name__ == "__main__":
    reset = "--reset" in sys.argv
    seed_database(reset_existing=reset)
