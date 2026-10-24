import pytest
from datetime import date, timedelta
from decimal import Decimal
from health_insurance_claims.models import Policy, Member, Plan, User
from health_insurance_claims.services import calculate_policy_premium, validate_and_purchase_policy

def test_premium_calculation_actuarial_rules(app, seeded_db):
    """Test audited actuarial premium calculation including dependent additions and 18% GST."""
    with app.app_context():
        plan1 = Plan.query.get(1)  # Essential Care: 1L, base 4,800
        plan2 = Plan.query.get(2)  # Plus Care: 2L, base 8,500

        # Self only on Essential Care
        res_self = calculate_policy_premium(plan1, ["self"])
        assert res_self["base_premium"] == Decimal("4800.00")
        assert res_self["dependent_premium"] == Decimal("0.00")
        assert res_self["net_premium"] == Decimal("4800.00")
        assert res_self["gst_amount"] == Decimal("864.00")  # 4800 * 0.18
        assert res_self["total_annual_premium"] == Decimal("5664.00")

        # Self + Spouse (+2500) + Child (+1500) on Plus Care (base 8,500)
        res_family = calculate_policy_premium(plan2, ["self", "spouse", "child"])
        assert res_family["base_premium"] == Decimal("8500.00")
        assert res_family["dependent_premium"] == Decimal("4000.00")  # 2500 + 1500
        assert res_family["net_premium"] == Decimal("12500.00")
        assert res_family["gst_amount"] == Decimal("2250.00")  # 12500 * 0.18
        assert res_family["total_annual_premium"] == Decimal("14750.00")
        assert res_family["total_members"] == 3

def test_buy_policy_page_accessible_for_policyholder(client, seeded_db):
    """Ensure authenticated policyholder can view available plans and purchase page."""
    # Login as policyholder Aasha Rao
    client.post("/login", data={"username": "aasha", "password": "Password123!"})
    resp = client.get("/buy-policy")
    assert resp.status_code == 200
    assert b"Purchase Health Insurance Policy" in resp.data
    assert b"Essential Care" in resp.data
    assert b"Plus Care" in resp.data

def test_buy_policy_forbidden_for_other_roles(client, seeded_db):
    """Ensure hospital desk and claims officer are forbidden from purchasing policies (403)."""
    # Hospital desk
    client.post("/login", data={"username": "city_hospital", "password": "Password123!"})
    resp = client.get("/buy-policy")
    assert resp.status_code == 403

    # Claims officer
    client.post("/login", data={"username": "officer_meera", "password": "Password123!"})
    resp = client.get("/buy-policy")
    assert resp.status_code == 403

def test_unauthenticated_redirect_to_login(client, seeded_db):
    """Ensure guest users cannot access policy purchase without authentication."""
    resp = client.get("/buy-policy")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

def test_successful_policy_purchase_workflow(client, app, seeded_db):
    """Test complete policy purchase flow: submission, DB persistence, member creation, and receipt."""
    client.post("/login", data={"username": "bilal", "password": "Password123!"})
    
    start_str = date.today().strftime("%Y-%m-%d")
    post_data = {
        "plan_id": 1,
        "start_date": start_str,
        "primary_member_name": "Bilal Khan",
        "nominee_name": "Fatima Khan",
        "nominee_relationship": "spouse",
        "include_spouse": "y",
        "spouse_name": "Fatima Khan",
        "include_child1": "y",
        "child1_name": "Zaid Khan",
        "payment_method": "simulated_upi",
        "agree_terms": "y"
    }
    
    resp = client.post("/buy-policy", data=post_data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Policy Issued & Confirmed" in resp.data or b"Congratulations" in resp.data

    # Verify DB records
    with app.app_context():
        user = User.query.filter_by(username="bilal").first()
        new_pol = Policy.query.filter_by(holder_user_id=user.user_id, plan_id=1).order_by(Policy.policy_id.desc()).first()
        assert new_pol is not None
        assert new_pol.status == "active"
        assert new_pol.start_date == date.today()
        assert new_pol.end_date == date.today() + timedelta(days=365)

        # Check members
        members = Member.query.filter_by(policy_id=new_pol.policy_id).all()
        assert len(members) == 3
        member_names = [m.display_name for m in members]
        assert "Bilal Khan" in member_names
        assert "Fatima Khan" in member_names
        assert "Zaid Khan" in member_names

def test_duplicate_policy_purchase_prevention(app, seeded_db):
    """Ensure users cannot purchase duplicate overlapping active policies under same plan."""
    with app.app_context():
        user = User.query.filter_by(username="aasha").first()  # Aasha already has active policy 101 under plan 1
        
        success, msg, pol, _ = validate_and_purchase_policy(
            user=user,
            plan_id=1,
            start_date=date.today(),
            primary_member_name="Aasha Rao"
        )
        assert success is False
        assert "already hold an active policy" in msg
        assert pol is None

def test_invalid_plan_rejection(app, seeded_db):
    """Ensure invalid plan IDs are rejected gracefully."""
    with app.app_context():
        user = User.query.filter_by(username="bilal").first()
        success, msg, pol, _ = validate_and_purchase_policy(
            user=user,
            plan_id=99999,  # Non-existent
            start_date=date.today(),
            primary_member_name="Bilal Khan"
        )
        assert success is False
        assert "does not exist" in msg
        assert pol is None

def test_start_date_in_past_rejected(app, seeded_db):
    """Ensure policy cannot be backdated to the past."""
    with app.app_context():
        user = User.query.filter_by(username="bilal").first()
        past_date = date.today() - timedelta(days=10)
        success, msg, pol, _ = validate_and_purchase_policy(
            user=user,
            plan_id=2,
            start_date=past_date,
            primary_member_name="Bilal Khan"
        )
        assert success is False
        assert "cannot be in the past" in msg
        assert pol is None
