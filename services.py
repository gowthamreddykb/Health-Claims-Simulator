from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
import os
import uuid
from typing import Optional, Tuple, Dict, Any, List
from werkzeug.utils import secure_filename
from sqlalchemy import func, and_, or_

if __package__:
    from .extensions import db
    from .models import (
        User, Hospital, Plan, Policy, Member, Claim,
        ClaimDocument, ClaimHistory, Settlement, Notification
    )
else:
    from extensions import db
    from models import (
        User, Hospital, Plan, Policy, Member, Claim,
        ClaimDocument, ClaimHistory, Settlement, Notification
    )

VALID_STATUS_TRANSITIONS = {
    "draft": ["submitted", "withdrawn"],
    "submitted": ["in_review", "withdrawn"],
    "in_review": ["more_info", "approved", "rejected"],
    "more_info": ["submitted", "withdrawn"],
    "approved": ["paid"],
    "rejected": [],
    "paid": [],
    "withdrawn": []
}

def round_inr(value: Decimal) -> Decimal:
    """Format and round INR monetary amounts with 2 decimal precision."""
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def get_next_history_sequence(claim_id: int) -> int:
    max_seq = db.session.query(func.max(ClaimHistory.sequence_no)).filter(
        ClaimHistory.claim_id == claim_id
    ).scalar()
    return (max_seq or 0) + 1

def add_claim_history(
    claim_id: int,
    from_status: Optional[str],
    to_status: str,
    actor_user_id: int,
    note: str,
    event_date: Optional[date] = None
) -> ClaimHistory:
    seq_no = get_next_history_sequence(claim_id)
    history = ClaimHistory(
        claim_id=claim_id,
        sequence_no=seq_no,
        from_status=from_status,
        to_status=to_status,
        actor_user_id=actor_user_id,
        note=note,
        event_date=event_date or date.today()
    )
    db.session.add(history)
    return history

def create_notification(
    user_id: int,
    title: str,
    message: str,
    category: str = "info",
    claim_id: Optional[int] = None
) -> Optional[Notification]:
    """Persist an in-app notification for a user."""
    try:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            claim_id=claim_id
        )
        db.session.add(notif)
        return notif
    except Exception as e:
        print(f"[Notification Error] Failed to create notification: {e}")
        return None

def calculate_remaining_cover(policy: Policy, admission_date: Optional[date] = None) -> Decimal:
    """
    Remaining cover is annual_limit minus prior settled payouts on this policy.
    Uses strictly Decimal arithmetic.
    """
    if not policy or not policy.plan:
        return Decimal("0.00")
        
    annual_limit = Decimal(str(policy.plan.annual_limit_inr))
    
    # Sum paid settlement payouts on this policy
    paid_sum = db.session.query(func.coalesce(func.sum(Settlement.amount_inr), 0)).join(
        Claim, Settlement.claim_id == Claim.claim_id
    ).filter(
        Claim.policy_id == policy.policy_id,
        Claim.status == "paid"
    ).scalar()
    
    prior_paid = Decimal(str(paid_sum or 0))
    remaining = annual_limit - prior_paid
    return max(Decimal("0.00"), round_inr(remaining))

def calculate_claim_payout(eligible_amount: Decimal, plan: Plan) -> Dict[str, Decimal]:
    """
    Calculates audited approved payout using:
    payout = round((eligible_amount - min(eligible_amount, deductible)) * (1 - copay_percent / 100), 2)
    All operations use Decimal.
    """
    eligible = Decimal(str(eligible_amount))
    deductible = Decimal(str(plan.deductible_inr))
    copay_pct = Decimal(str(plan.copay_percent))
    
    deductible_applied = min(eligible, deductible)
    amount_after_deductible = max(Decimal("0.00"), eligible - deductible_applied)
    copay_fraction = copay_pct / Decimal("100.00")
    copay_deduction = round_inr(amount_after_deductible * copay_fraction)
    payout = round_inr(amount_after_deductible * (Decimal("1.00") - copay_fraction))
    
    return {
        "eligible_amount": eligible,
        "deductible_applied": deductible_applied,
        "amount_after_deductible": amount_after_deductible,
        "copay_deduction": copay_deduction,
        "calculated_payout": payout
    }

def detect_potential_duplicates(claim: Claim) -> List[Claim]:
    """
    Flags other claims only when the whole claim record is identical:
    same member, same policy, same hospital, same admission date,
    same discharge date, same claim type, same treatment type,
    and same requested amount.
    If the whole record is not identical, it is not flagged as a duplicate.
    """
    if not claim:
        return []

    query = Claim.query.filter(
        Claim.member_id == claim.member_id,
        Claim.claim_id != (claim.claim_id or -1)
    )
    duplicates = []
    try:
        claim_amt = Decimal(str(claim.requested_amount_inr or 0))
    except Exception:
        claim_amt = Decimal("0")

    for other in query.all():
        if other.status == "withdrawn":
            continue

        same_policy = (other.policy_id == claim.policy_id)
        same_hospital = (other.hospital_id == claim.hospital_id)
        same_adm = (other.admission_date == claim.admission_date)
        same_dis = (other.discharge_date == claim.discharge_date)
        same_claim_type = (other.claim_type == claim.claim_type)
        same_treatment_type = (other.treatment_type == claim.treatment_type)

        try:
            other_amt = Decimal(str(other.requested_amount_inr or 0))
            same_amt = (abs(other_amt - claim_amt) < Decimal("0.01"))
        except Exception:
            same_amt = False

        # Flag only when the whole record matches
        if (same_policy and same_hospital and same_adm and same_dis and
                same_claim_type and same_treatment_type and same_amt):
            duplicates.append(other)

    return duplicates

def can_user_view_claim(user: User, claim: Claim) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_admin or user.is_claims_officer:
        return True
    if user.is_policyholder:
        return claim.policy.holder_user_id == user.user_id
    if user.is_hospital_desk:
        return claim.hospital_id == user.hospital_id
    return False

def can_user_edit_claim(user: User, claim: Claim) -> bool:
    if not user.is_authenticated:
        return False
    if claim.status not in ["draft", "more_info"]:
        return False
    if user.is_policyholder:
        return claim.policy.holder_user_id == user.user_id
    if user.is_hospital_desk:
        return claim.hospital_id == user.hospital_id
    return False

def assign_claim_to_officer(claim_id: int, officer: User) -> Tuple[bool, str]:
    if not officer.is_claims_officer:
        return False, "Only a claims officer can be assigned to a claim."
        
    claim = Claim.query.get(claim_id)
    if not claim:
        return False, "Claim not found."
        
    if claim.status != "submitted":
        return False, f"Cannot assign claim in '{claim.status}' status."
        
    if claim.officer_user_id and claim.officer_user_id != officer.user_id:
        return False, f"Claim is already assigned to officer {claim.officer.display_name}."
        
    try:
        old_status = claim.status
        claim.officer_user_id = officer.user_id
        claim.status = "in_review"
        claim.updated_at = datetime.utcnow()
        
        add_claim_history(
            claim_id=claim.claim_id,
            from_status=old_status,
            to_status="in_review",
            actor_user_id=officer.user_id,
            note=f"Assigned to {officer.display_name} and moved to In Review."
        )
        
        # Notify policyholder
        create_notification(
            user_id=claim.policy.holder_user_id,
            title="Claim Assigned for Review",
            message=f"Your claim CLM-{claim.claim_id:06d} has been assigned to Claims Officer {officer.display_name}.",
            category="info",
            claim_id=claim.claim_id
        )
        
        db.session.commit()
        return True, "Claim assigned and moved to In Review."
    except Exception as e:
        db.session.rollback()
        return False, f"Failed to assign claim: {str(e)}"

def process_review_decision(
    claim_id: int,
    officer: User,
    action: str,
    decision_reason: str,
    eligible_amount: Optional[Decimal] = None
) -> Tuple[bool, str]:
    if not officer.is_claims_officer:
        return False, "Only claims officers can review claims."
        
    claim = Claim.query.get(claim_id)
    if not claim:
        return False, "Claim not found."
        
    if claim.status != "in_review":
        return False, f"Claim is in '{claim.status}' status and cannot be decided on."
        
    if claim.officer_user_id != officer.user_id:
        return False, "You can only review claims assigned to you."
        
    if not decision_reason or len(decision_reason.strip()) < 5:
        return False, "A clear written reason is required."

    try:
        if action == "more_info":
            old_status = claim.status
            claim.status = "more_info"
            claim.decision_reason = decision_reason.strip()
            claim.updated_at = datetime.utcnow()
            add_claim_history(
                claim_id=claim.claim_id,
                from_status=old_status,
                to_status="more_info",
                actor_user_id=officer.user_id,
                note=f"Information Requested: {decision_reason.strip()}"
            )
            # Notify policyholder
            create_notification(
                user_id=claim.policy.holder_user_id,
                title="Action Required: Additional Information Requested",
                message=f"Claims Officer requested information on claim CLM-{claim.claim_id:06d}: {decision_reason.strip()}",
                category="warning",
                claim_id=claim.claim_id
            )
            db.session.commit()
            return True, "Information request sent to submitter."

        elif action == "reject":
            old_status = claim.status
            claim.status = "rejected"
            claim.eligible_amount_inr = Decimal("0.00")
            claim.decision_reason = decision_reason.strip()
            claim.updated_at = datetime.utcnow()
            add_claim_history(
                claim_id=claim.claim_id,
                from_status=old_status,
                to_status="rejected",
                actor_user_id=officer.user_id,
                note=f"Claim Rejected: {decision_reason.strip()}"
            )
            # Notify policyholder
            create_notification(
                user_id=claim.policy.holder_user_id,
                title="Claim Assessment: Rejected",
                message=f"Claim CLM-{claim.claim_id:06d} was rejected: {decision_reason.strip()}",
                category="danger",
                claim_id=claim.claim_id
            )
            db.session.commit()
            return True, "Claim has been rejected."

        elif action == "approve":
            if eligible_amount is None or eligible_amount <= Decimal("0.00"):
                return False, "Eligible amount must be greater than zero for approval."
                
            req_amount = Decimal(str(claim.requested_amount_inr))
            if eligible_amount > req_amount:
                return False, f"Eligible amount (₹{eligible_amount}) cannot exceed requested amount (₹{req_amount})."
                
            policy = claim.policy
            if not policy.is_active_on(claim.admission_date):
                return False, f"Policy was not active on admission date {claim.admission_date}."
                
            if not policy.plan.is_treatment_covered(claim.treatment_type):
                return False, f"Treatment type '{claim.treatment_type}' is not covered under plan '{policy.plan.plan_name}'."
                
            rem_cover = calculate_remaining_cover(policy)
            if eligible_amount > rem_cover:
                return False, f"Eligible amount (₹{eligible_amount}) exceeds remaining policy cover (₹{rem_cover})."

            old_status = claim.status
            claim.status = "approved"
            claim.eligible_amount_inr = round_inr(eligible_amount)
            claim.decision_reason = decision_reason.strip()
            claim.updated_at = datetime.utcnow()
            
            payout_info = calculate_claim_payout(eligible_amount, policy.plan)
            calc_payout = payout_info["calculated_payout"]
            
            add_claim_history(
                claim_id=claim.claim_id,
                from_status=old_status,
                to_status="approved",
                actor_user_id=officer.user_id,
                note=f"Approved with eligible amount ₹{eligible_amount:,.2f} (Calculated Payout: ₹{calc_payout:,.2f}). Reason: {decision_reason.strip()}"
            )
            # Notify policyholder
            create_notification(
                user_id=claim.policy.holder_user_id,
                title="Claim Approved!",
                message=f"Claim CLM-{claim.claim_id:06d} has been approved for ₹{eligible_amount:,.2f}. Estimated payout: ₹{calc_payout:,.2f}.",
                category="success",
                claim_id=claim.claim_id
            )
            db.session.commit()
            return True, f"Claim approved for ₹{eligible_amount:,.2f}."
            
        else:
            return False, f"Invalid action: {action}"

    except Exception as e:
        db.session.rollback()
        return False, f"Decision processing failed: {str(e)}"

def record_simulated_settlement(claim_id: int, admin_user: User) -> Tuple[bool, str]:
    if not admin_user.is_admin:
        return False, "Only administrators can record simulated settlements."
        
    claim = Claim.query.get(claim_id)
    if not claim:
        return False, "Claim not found."
        
    if claim.status != "approved":
        return False, f"Only approved claims can be settled. Current status is '{claim.status}'."
        
    if claim.settlement:
        return False, "A settlement has already been recorded for this claim."
        
    if not claim.eligible_amount_inr or claim.eligible_amount_inr <= Decimal("0.00"):
        return False, "Claim has no valid eligible amount."

    try:
        payout_info = calculate_claim_payout(Decimal(str(claim.eligible_amount_inr)), claim.policy.plan)
        payout_amount = payout_info["calculated_payout"]
        payee_type = "hospital" if claim.claim_type == "cashless" else "policyholder"
        
        today = date.today()
        settlement = Settlement(
            claim_id=claim.claim_id,
            payee_type=payee_type,
            amount_inr=payout_amount,
            recorded_by_user_id=admin_user.user_id,
            recorded_date=today
        )
        db.session.add(settlement)
        
        old_status = claim.status
        claim.status = "paid"
        claim.payment_recorded_date = today
        claim.updated_at = datetime.utcnow()
        
        add_claim_history(
            claim_id=claim.claim_id,
            from_status=old_status,
            to_status="paid",
            actor_user_id=admin_user.user_id,
            note=f"Simulated settlement recorded: ₹{payout_amount:,.2f} payable to {payee_type}."
        )
        
        # Notify policyholder
        create_notification(
            user_id=claim.policy.holder_user_id,
            title="Settlement Recorded & Paid",
            message=f"Simulated settlement of ₹{payout_amount:,.2f} for claim CLM-{claim.claim_id:06d} was processed to {payee_type}.",
            category="success",
            claim_id=claim.claim_id
        )
        
        db.session.commit()
        return True, f"Simulated settlement of ₹{payout_amount:,.2f} recorded for {payee_type}."
    except Exception as e:
        db.session.rollback()
        return False, f"Failed to record settlement: {str(e)}"

def withdraw_claim(claim_id: int, user: User, reason: str) -> Tuple[bool, str]:
    claim = Claim.query.get(claim_id)
    if not claim:
        return False, "Claim not found."
        
    if not can_user_edit_claim(user, claim) and claim.status != "submitted":
        return False, "You do not have permission to withdraw this claim."
        
    if claim.status in ["approved", "rejected", "paid", "withdrawn"]:
        return False, f"Cannot withdraw claim in '{claim.status}' status."
        
    try:
        old_status = claim.status
        claim.status = "withdrawn"
        claim.decision_reason = f"Withdrawn by user: {reason}"
        claim.updated_at = datetime.utcnow()
        
        add_claim_history(
            claim_id=claim.claim_id,
            from_status=old_status,
            to_status="withdrawn",
            actor_user_id=user.user_id,
            note=f"Claim withdrawn: {reason}"
        )
        db.session.commit()
        return True, "Claim has been withdrawn successfully."
    except Exception as e:
        db.session.rollback()
        return False, f"Failed to withdraw claim: {str(e)}"

def save_uploaded_document(
    claim: Claim,
    doc_type: str,
    file_storage,
    uploader: User,
    upload_folder: str
) -> Tuple[bool, str]:
    """Securely store an uploaded document and record metadata in database."""
    try:
        os.makedirs(upload_folder, exist_ok=True)
        orig_name = secure_filename(file_storage.filename)
        ext = os.path.splitext(orig_name)[1].lower()
        unique_key = f"doc_{claim.claim_id}_{doc_type}_{uuid.uuid4().hex[:8]}{ext}"
        target_path = os.path.join(upload_folder, unique_key)
        
        file_storage.save(target_path)
        file_size = os.path.getsize(target_path)
        mime = file_storage.mimetype or "application/octet-stream"
        
        # Check if ClaimDocument already exists for this type
        existing = ClaimDocument.query.filter_by(claim_id=claim.claim_id, document_type=doc_type).first()
        if existing:
            existing.original_filename = orig_name
            existing.storage_key = unique_key
            existing.file_size_bytes = file_size
            existing.mime_type = mime
            existing.uploaded_by_user_id = uploader.user_id
            existing.uploaded_at = datetime.utcnow()
            existing.checklist_status = "received"
            existing.verification_status = "verified"
        else:
            new_doc = ClaimDocument(
                claim_id=claim.claim_id,
                document_type=doc_type,
                checklist_status="received",
                original_filename=orig_name,
                storage_key=unique_key,
                file_size_bytes=file_size,
                mime_type=mime,
                uploaded_by_user_id=uploader.user_id,
                uploaded_at=datetime.utcnow(),
                verification_status="verified"
            )
            db.session.add(new_doc)
            
        add_claim_history(
            claim_id=claim.claim_id,
            from_status=claim.status,
            to_status=claim.status,
            actor_user_id=uploader.user_id,
            note=f"Document uploaded: {doc_type.replace('_', ' ').title()} ({orig_name})"
        )
        db.session.commit()
        return True, f"Document '{orig_name}' successfully uploaded."
    except Exception as e:
        db.session.rollback()
        return False, f"Failed to upload document: {str(e)}"

def get_dashboard_metrics(user: User) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {}
    
    if user.is_policyholder:
        user_policies = Policy.query.filter_by(holder_user_id=user.user_id).all()
        policy_ids = [p.policy_id for p in user_policies]
        
        metrics["active_policies"] = sum(1 for p in user_policies if p.status == "active")
        metrics["covered_members"] = Member.query.filter(Member.policy_id.in_(policy_ids)).count() if policy_ids else 0
        
        own_claims = Claim.query.filter(Claim.policy_id.in_(policy_ids)) if policy_ids else None
        metrics["total_claims"] = own_claims.count() if own_claims else 0
        metrics["pending_actions"] = own_claims.filter(Claim.status.in_(["more_info", "draft"])).count() if own_claims else 0
        metrics["recent_claims"] = own_claims.order_by(Claim.created_at.desc()).limit(5).all() if own_claims else []
        
    elif user.is_hospital_desk:
        h_claims = Claim.query.filter_by(hospital_id=user.hospital_id)
        metrics["total_hospital_claims"] = h_claims.count()
        metrics["draft_claims"] = h_claims.filter_by(status="draft").count()
        metrics["submitted_claims"] = h_claims.filter_by(status="submitted").count()
        metrics["in_review_claims"] = h_claims.filter_by(status="in_review").count()
        metrics["missing_docs_claims"] = h_claims.join(ClaimDocument).filter(ClaimDocument.checklist_status == "missing").distinct().count()
        metrics["recent_claims"] = h_claims.order_by(Claim.created_at.desc()).limit(5).all()
        
    elif user.is_claims_officer:
        metrics["assigned_to_me"] = Claim.query.filter_by(officer_user_id=user.user_id, status="in_review").count()
        metrics["awaiting_assignment"] = Claim.query.filter_by(status="submitted", officer_user_id=None).count()
        metrics["more_info"] = Claim.query.filter_by(officer_user_id=user.user_id, status="more_info").count()
        metrics["awaiting_decision"] = Claim.query.filter_by(officer_user_id=user.user_id, status="in_review").count()
        metrics["recent_claims"] = Claim.query.filter(
            or_(Claim.officer_user_id == user.user_id, Claim.status == "submitted")
        ).order_by(Claim.updated_at.desc()).limit(5).all()
        
    elif user.is_admin:
        metrics["total_claims"] = Claim.query.count()
        metrics["approved_claims"] = Claim.query.filter_by(status="approved").count()
        metrics["rejected_claims"] = Claim.query.filter_by(status="rejected").count()
        metrics["paid_settlements"] = Claim.query.filter_by(status="paid").count()
        
        req_sum = db.session.query(func.coalesce(func.sum(Claim.requested_amount_inr), 0)).scalar()
        elig_sum = db.session.query(func.coalesce(func.sum(Claim.eligible_amount_inr), 0)).scalar()
        paid_sum = db.session.query(func.coalesce(func.sum(Settlement.amount_inr), 0)).scalar()
        
        metrics["total_requested"] = Decimal(str(req_sum or 0))
        metrics["total_eligible"] = Decimal(str(elig_sum or 0))
        metrics["total_paid"] = Decimal(str(paid_sum or 0))
        metrics["recent_claims"] = Claim.query.order_by(Claim.updated_at.desc()).limit(5).all()

    return metrics


def calculate_policy_premium(plan: Plan, member_relationships: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Calculates audited annual insurance premium strictly using plan attributes and actuarial business rules.
    - Base Plan Premium:
        Essential Care (1L): ₹4,800.00
        Plus Care (2L): ₹8,500.00
        Family Care (3L): ₹12,000.00
        Custom Plans: 4% of annual limit + (100 - copay%) * ₹20
    - Dependent Member Additions:
        Spouse: +₹2,500.00
        Child: +₹1,500.00
        Parent: +₹3,500.00
        Other: +₹2,000.00
    - Statutory GST: 18.00%
    All monetary operations use Decimal arithmetic.
    """
    if not plan:
        raise ValueError("A valid insurance plan is required to calculate premium.")

    # 1. Base Plan Premium Calculation
    limit = Decimal(str(plan.annual_limit_inr))
    copay = Decimal(str(plan.copay_percent))
    
    # Exact known baseline tiers
    if plan.plan_id == 1 or abs(limit - Decimal("100000.00")) < Decimal("1.00"):
        base_premium = Decimal("4800.00")
    elif plan.plan_id == 2 or abs(limit - Decimal("200000.00")) < Decimal("1.00"):
        base_premium = Decimal("8500.00")
    elif plan.plan_id == 3 or abs(limit - Decimal("300000.00")) < Decimal("1.00"):
        base_premium = Decimal("12000.00")
    else:
        # Dynamic formula for administrator-added custom plans
        calculated = (limit * Decimal("0.04")) + ((Decimal("100.00") - copay) * Decimal("20.00"))
        base_premium = round_inr(calculated)

    # 2. Dependent Loading Breakdown
    dependent_premium = Decimal("0.00")
    dependent_breakdown = []
    
    if member_relationships:
        for rel in member_relationships:
            r = rel.strip().lower()
            if r == "self":
                continue  # Primary insured already covered in base premium
            elif r == "spouse":
                charge = Decimal("2500.00")
                label = "Spouse Cover"
            elif r == "child":
                charge = Decimal("1500.00")
                label = "Child Cover"
            elif r == "parent":
                charge = Decimal("3500.00")
                label = "Senior Parent Cover"
            else:
                charge = Decimal("2000.00")
                label = f"{r.title()} Cover"

            dependent_premium += charge
            dependent_breakdown.append({
                "relationship": r,
                "label": label,
                "amount": charge
            })

    # 3. Subtotal & GST
    net_premium = round_inr(base_premium + dependent_premium)
    gst_rate = Decimal("0.18")
    gst_amount = round_inr(net_premium * gst_rate)
    total_annual_premium = round_inr(net_premium + gst_amount)

    total_members = 1 + len(dependent_breakdown)

    return {
        "plan_id": plan.plan_id,
        "plan_name": plan.plan_name,
        "annual_limit_inr": limit,
        "deductible_inr": Decimal(str(plan.deductible_inr)),
        "copay_percent": copay,
        "base_premium": base_premium,
        "dependent_premium": dependent_premium,
        "dependent_breakdown": dependent_breakdown,
        "net_premium": net_premium,
        "gst_rate_percent": Decimal("18.00"),
        "gst_amount": gst_amount,
        "total_annual_premium": total_annual_premium,
        "total_members": total_members
    }


def validate_and_purchase_policy(
    user: User,
    plan_id: int,
    start_date: date,
    primary_member_name: str,
    dependents: Optional[List[Dict[str, str]]] = None,
    payment_mode: str = "simulated_upi"
) -> Tuple[bool, str, Optional[Policy], Optional[Dict[str, Any]]]:
    """
    Validates server-side business rules, enforces role authorization, prevents duplicate coverage,
    calculates official premium, persists Policy and Member records, and records an in-app confirmation notification.
    """
    # 1. Enforce Authentication & Role Authorization
    if not user or not user.is_authenticated:
        return False, "Authentication is required to purchase a policy.", None, None

    if not user.is_policyholder:
        return False, "Only users with the Policyholder role are permitted to purchase policies.", None, None

    # 2. Plan Validation
    plan = db.session.get(Plan, plan_id)
    if not plan:
        return False, "The selected insurance plan does not exist or is inactive.", None, None

    # 3. Date Validation
    if not start_date:
        start_date = date.today()
    elif start_date < date.today():
        return False, "Policy start date cannot be in the past.", None, None

    from datetime import timedelta
    end_date = start_date + timedelta(days=365)

    # 4. Duplicate Active Policy Prevention
    # Prevent duplicate active policies for the exact same user and plan covering the same start date
    existing_policy = Policy.query.filter(
        Policy.holder_user_id == user.user_id,
        Policy.plan_id == plan.plan_id,
        Policy.status == "active",
        Policy.start_date <= start_date,
        Policy.end_date >= start_date
    ).first()

    if existing_policy:
        return False, (
            f"You already hold an active policy (#{existing_policy.policy_id}) under the '{plan.plan_name}' plan "
            f"valid through {existing_policy.end_date.strftime('%d %b %Y')}. You cannot purchase duplicate coverage."
        ), None, None

    # 5. Primary Member Validation
    primary_name = (primary_member_name or user.display_name or "").strip()
    if not primary_name:
        return False, "Primary insured member name is required.", None, None

    # 6. Sanitize Dependents
    valid_dependents = []
    relationships_list = ["self"]
    if dependents:
        for dep in dependents:
            name = (dep.get("name") or "").strip()
            rel = (dep.get("relationship") or "").strip().lower()
            if name and rel:
                valid_dependents.append({"name": name, "relationship": rel})
                relationships_list.append(rel)

    # 7. Audited Server-Side Premium Calculation
    premium_breakdown = calculate_policy_premium(plan, relationships_list)

    # 8. Persist Policy Record
    status = "active" if payment_mode in ["simulated_upi", "netbanking", "corporate_card"] else "pending_payment"
    
    new_policy = Policy(
        holder_user_id=user.user_id,
        plan_id=plan.plan_id,
        start_date=start_date,
        end_date=end_date,
        status=status
    )
    db.session.add(new_policy)
    db.session.flush()  # Allocate policy_id

    # 9. Persist Covered Member Records
    primary_member = Member(
        policy_id=new_policy.policy_id,
        display_name=primary_name,
        relationship_type="self"
    )
    db.session.add(primary_member)

    for dep in valid_dependents:
        dep_member = Member(
            policy_id=new_policy.policy_id,
            display_name=dep["name"],
            relationship_type=dep["relationship"]
        )
        db.session.add(dep_member)

    # 10. Generate In-App Notification for Policyholder
    create_notification(
        user_id=user.user_id,
        title=f"Policy Activated: {plan.plan_name}",
        message=(
            f"Your new policy No. HP{new_policy.policy_id:04d}456 has been issued with ₹"
            f"{plan.annual_limit_inr:,.0f} annual coverage covering {len(relationships_list)} member(s). "
            f"Valid from {start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}."
        ),
        category="success"
    )

    db.session.commit()
    return True, f"Policy HP{new_policy.policy_id:04d}456 successfully purchased and activated!", new_policy, premium_breakdown

