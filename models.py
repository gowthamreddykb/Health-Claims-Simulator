from datetime import datetime, date
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime, Numeric,
    ForeignKey, Text, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship

if __package__:
    from .extensions import db
else:
    from extensions import db

class AnonymousUser:
    """Represents an unauthenticated guest session."""
    user_id = None
    username = ""
    display_name = "Guest"
    role = ""
    hospital_id = None

    @property
    def is_authenticated(self) -> bool:
        return False

    @property
    def is_anonymous(self) -> bool:
        return True

    @property
    def is_active(self) -> bool:
        return False

    @property
    def is_policyholder(self) -> bool:
        return False

    @property
    def is_hospital_desk(self) -> bool:
        return False

    @property
    def is_claims_officer(self) -> bool:
        return False

    @property
    def is_admin(self) -> bool:
        return False


class User(db.Model):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    display_name = Column(String(120), nullable=False)
    role = Column(String(30), nullable=False)  # policyholder, hospital, claims_officer, admin
    hospital_id = Column(Integer, ForeignKey("hospitals.hospital_id"), nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_active_user = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="staff_users")
    policies = relationship("Policy", back_populates="holder", foreign_keys="Policy.holder_user_id")
    assigned_claims = relationship("Claim", back_populates="officer", foreign_keys="Claim.officer_user_id")
    history_events = relationship("ClaimHistory", back_populates="actor", foreign_keys="ClaimHistory.actor_user_id")
    recorded_settlements = relationship("Settlement", back_populates="recorded_by", foreign_keys="Settlement.recorded_by_user_id")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan", order_by="Notification.created_at.desc()")

    def get_id(self):
        return str(self.user_id)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    @property
    def is_active(self) -> bool:
        return self.is_active_user

    @property
    def is_policyholder(self) -> bool:
        return self.role == "policyholder"

    @property
    def is_hospital_desk(self) -> bool:
        return self.role == "hospital"

    @property
    def is_claims_officer(self) -> bool:
        return self.role == "claims_officer"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class Hospital(db.Model):
    __tablename__ = "hospitals"
    
    hospital_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    city = Column(String(100), nullable=False)
    network_status = Column(Boolean, nullable=False, default=True)  # True = Network, False = Non-Network
    document_id = Column(Integer) 
    
    # Relationships
    staff_users = relationship("User", back_populates="hospital")
    claims = relationship("Claim", back_populates="hospital")


class Plan(db.Model):
    __tablename__ = "plans"
    
    plan_id = Column(Integer, primary_key=True, autoincrement=True)
    plan_name = Column(String(100), nullable=False)
    covered_treatment_types = Column(String(120), nullable=False)  # pipe-separated e.g. "inpatient|daycare"
    annual_limit_inr = Column(Numeric(12, 2), nullable=False)
    deductible_inr = Column(Numeric(10, 2), nullable=False)
    copay_percent = Column(Numeric(5, 2), nullable=False)
    
    # Relationships
    policies = relationship("Policy", back_populates="plan")

    def is_treatment_covered(self, treatment_type: str) -> bool:
        if not treatment_type or not self.covered_treatment_types:
            return False
        types = [t.strip().lower() for t in self.covered_treatment_types.split("|")]
        return treatment_type.strip().lower() in types


class Policy(db.Model):
    __tablename__ = "policies"
    
    policy_id = Column(Integer, primary_key=True, autoincrement=True)
    holder_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.plan_id"), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(30), nullable=False, default="active")  # active, expired, cancelled
    
    # Relationships
    holder = relationship("User", back_populates="policies")
    plan = relationship("Plan", back_populates="policies")
    members = relationship("Member", back_populates="policy", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="policy")

    def is_active_on(self, target_date: date) -> bool:
        if not target_date:
            return False
        return self.status == "active" and (self.start_date <= target_date <= self.end_date)


class Member(db.Model):
    __tablename__ = "members"
    
    member_id = Column(Integer, primary_key=True, autoincrement=True)
    policy_id = Column(Integer, ForeignKey("policies.policy_id"), nullable=False, index=True)
    display_name = Column(String(120), nullable=False)
    relationship_type = Column("relationship", String(50), nullable=False)  # self, spouse, child, parent
    
    # Relationships
    policy = relationship("Policy", back_populates="members")
    claims = relationship("Claim", back_populates="member")


class Claim(db.Model):
    __tablename__ = "claims"
    
    claim_id = Column(Integer, primary_key=True, autoincrement=True)
    policy_id = Column(Integer, ForeignKey("policies.policy_id"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.member_id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.hospital_id"), nullable=False)
    claim_type = Column(String(30), nullable=False)  # cashless, reimbursement
    treatment_type = Column(String(50), nullable=False)  # inpatient, daycare
    admission_date = Column(Date, nullable=False)
    discharge_date = Column(Date, nullable=False)
    requested_amount_inr = Column(Numeric(12, 2), nullable=False)
    status = Column(String(30), nullable=False, default="draft")  # draft, submitted, in_review, more_info, approved, rejected, paid, withdrawn
    eligible_amount_inr = Column(Numeric(12, 2), nullable=True)
    officer_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    payment_recorded_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    decision_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("idx_claims_policy_status", "policy_id", "status"),
        Index("idx_claims_officer_status", "officer_user_id", "status"),
    )
    
    # Relationships
    policy = relationship("Policy", back_populates="claims")
    member = relationship("Member", back_populates="claims")
    hospital = relationship("Hospital", back_populates="claims")
    officer = relationship("User", back_populates="assigned_claims", foreign_keys=[officer_user_id])
    documents = relationship("ClaimDocument", back_populates="claim", cascade="all, delete-orphan")
    history_events = relationship("ClaimHistory", back_populates="claim", cascade="all, delete-orphan", order_by="ClaimHistory.sequence_no")
    settlement = relationship("Settlement", back_populates="claim", uselist=False, cascade="all, delete-orphan")

    @property
    def formatted_claim_id(self) -> str:
        return f"CLM-{self.claim_id:06d}"


class ClaimDocument(db.Model):
    __tablename__ = "claim_documents"
    
    claim_id = Column(Integer, ForeignKey("claims.claim_id"), primary_key=True) 
    document_type = Column(String(50), primary_key=True)  # hospital_bill, discharge_summary
    checklist_status = Column(String(30), nullable=False, default="received")  # received, missing
    document_id = Column(Integer)  # Optional: If you have a separate document storage system

    # Enhanced document management fields
    original_filename = Column(String(255), nullable=True)
    storage_key = Column(String(255), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    verification_status = Column(String(30), nullable=False, default="verified")  # pending, verified, rejected
    rejection_reason = Column(Text, nullable=True)
    
    __table_args__ = (
        UniqueConstraint("claim_id", "document_type", name="uq_claim_document_type"),
    )
    
    # Relationships
    claim = relationship("Claim", back_populates="documents")
    uploader = relationship("User", foreign_keys=[uploaded_by_user_id])


class ClaimHistory(db.Model):
    __tablename__ = "claim_history"
    
    history_id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(Integer, ForeignKey("claims.claim_id"), nullable=False, index=True)
    sequence_no = Column(Integer, nullable=False)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    note = Column(Text, nullable=True)
    event_date = Column(Date, nullable=False, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("idx_claim_history_lookup", "claim_id", "event_date"),
        UniqueConstraint("claim_id", "sequence_no", name="uq_claim_sequence"),
    )
    
    # Relationships
    claim = relationship("Claim", back_populates="history_events")
    actor = relationship("User", back_populates="history_events")


class Settlement(db.Model):
    __tablename__ = "settlements"
    
    settlement_id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(Integer, ForeignKey("claims.claim_id"), nullable=False, unique=True)
    payee_type = Column(String(30), nullable=False)  # hospital, policyholder
    amount_inr = Column(Numeric(12, 2), nullable=False)
    recorded_by_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    recorded_date = Column(Date, nullable=False, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    claim = relationship("Claim", back_populates="settlement")
    recorded_by = relationship("User", back_populates="recorded_settlements")


class Notification(db.Model):
    __tablename__ = "notifications"
    
    notification_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(30), nullable=False, default="info")  # info, success, warning, danger
    claim_id = Column(Integer, ForeignKey("claims.claim_id"), nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User", back_populates="notifications")
    claim = relationship("Claim")
