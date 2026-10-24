from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (
    StringField, PasswordField, BooleanField, SelectField,
    DateField, DecimalField, TextAreaField, HiddenField, SubmitField
)
from wtforms.validators import DataRequired, Optional, NumberRange, Length, ValidationError
from datetime import date
from decimal import Decimal

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class ClaimForm(FlaskForm):
    claim_id = HiddenField("Claim ID")
    policy_id = SelectField("Policy", coerce=int, validators=[DataRequired()])
    member_id = SelectField("Covered Member", coerce=int, validators=[DataRequired()], validate_choice=False)
    hospital_id = SelectField("Hospital", coerce=int, validators=[DataRequired()], validate_choice=False)
    claim_type = SelectField(
        "Claim Type",
        choices=[("reimbursement", "Reimbursement"), ("cashless", "Cashless")],
        validators=[DataRequired()]
    )
    treatment_type = SelectField(
        "Treatment Type",
        choices=[("inpatient", "Inpatient"), ("daycare", "Day Care")],
        validators=[DataRequired()]
    )
    admission_date = DateField("Admission Date", format="%Y-%m-%d", validators=[DataRequired()])
    discharge_date = DateField("Discharge Date", format="%Y-%m-%d", validators=[DataRequired()])
    requested_amount_inr = DecimalField(
        "Requested Amount (₹)",
        places=2,
        validators=[DataRequired(), NumberRange(min=Decimal("1.00"), message="Requested amount must be greater than zero.")]
    )
    description = TextAreaField("Description & Medical Symptoms", validators=[Optional(), Length(max=1000)])
    save_draft = SubmitField("Save Draft")
    submit_claim = SubmitField("Submit Claim")

    def validate_discharge_date(self, field):
        if self.admission_date.data and field.data:
            if field.data < self.admission_date.data:
                raise ValidationError("Discharge date cannot be prior to admission date.")


class DocumentChecklistForm(FlaskForm):
    hospital_bill = SelectField(
        "Hospital Bill Status",
        choices=[("received", "Received"), ("missing", "Missing")],
        validators=[DataRequired()]
    )
    discharge_summary = SelectField(
        "Discharge Summary Status",
        choices=[("received", "Received"), ("missing", "Missing")],
        validators=[DataRequired()]
    )
    notes = TextAreaField("Audit / Update Note", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Update Documents Checklist")


class DocumentUploadForm(FlaskForm):
    document_type = SelectField(
        "Document Category",
        choices=[
            ("hospital_bill", "Hospital Bill & Itemized Invoices"),
            ("discharge_summary", "Official Discharge Summary"),
            ("prescription", "Attending Physician Prescription"),
            ("investigation_report", "Lab & Diagnostic Reports")
        ],
        validators=[DataRequired()]
    )
    document_file = FileField(
        "Upload File (PDF, PNG, JPG, JPEG)",
        validators=[
            FileRequired(message="Please select a document file to upload."),
            FileAllowed(["pdf", "png", "jpg", "jpeg"], "Allowed file types: PDF, PNG, JPG, JPEG (Max 10MB)")
        ]
    )
    notes = TextAreaField("Document Notes", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Upload Document")


class ReviewDecisionForm(FlaskForm):
    eligible_amount_inr = DecimalField(
        "Eligible Amount (₹)",
        places=2,
        validators=[Optional(), NumberRange(min=Decimal("0.00"), message="Eligible amount cannot be negative.")]
    )
    decision_reason = TextAreaField(
        "Decision Reason / Information Request Note",
        validators=[DataRequired(message="A written reason is required for any decision or info request."), Length(min=5, max=1000)]
    )
    action = HiddenField("Action", validators=[DataRequired()])
    submit = SubmitField("Submit Decision")


class MoreInfoResponseForm(FlaskForm):
    response_note = TextAreaField(
        "Information Response & Updates",
        validators=[DataRequired(message="Please provide the requested information or clarification."), Length(min=5, max=1000)]
    )
    submit = SubmitField("Submit Information & Resubmit Claim")


class SettlementForm(FlaskForm):
    submit = SubmitField("Record Simulated Settlement & Pay")


class WithdrawClaimForm(FlaskForm):
    reason = TextAreaField("Reason for Withdrawal", validators=[DataRequired(message="Please provide a withdrawal reason."), Length(min=5, max=500)])
    submit = SubmitField("Withdraw Claim")


class HospitalForm(FlaskForm):
    name = StringField("Hospital Name", validators=[DataRequired(), Length(max=150)])
    city = StringField("City", validators=[DataRequired(), Length(max=100)])
    network_status = SelectField(
        "Network Status",
        choices=[("1", "Network (Cashless Eligible)"), ("0", "Non-Network")],
        validators=[DataRequired()]
    )
    submit = SubmitField("Save Hospital")


class PlanForm(FlaskForm):
    plan_name = StringField("Plan Name", validators=[DataRequired(), Length(max=100)])
    covered_treatment_types = StringField("Covered Treatment Types (pipe-separated, e.g. inpatient|daycare)", validators=[DataRequired(), Length(max=120)])
    annual_limit_inr = DecimalField("Annual Limit (₹)", places=2, validators=[DataRequired(), NumberRange(min=Decimal("1.00"))])
    deductible_inr = DecimalField("Deductible (₹)", places=2, validators=[DataRequired(), NumberRange(min=Decimal("0.00"))])
    copay_percent = DecimalField("Co-pay (%)", places=2, validators=[DataRequired(), NumberRange(min=Decimal("0.00"), max=Decimal("100.00"))])
    submit = SubmitField("Save Plan")


class UserRoleForm(FlaskForm):
    role = SelectField(
        "Role",
        choices=[
            ("policyholder", "Policyholder"),
            ("hospital", "Hospital Desk"),
            ("claims_officer", "Claims Officer"),
            ("admin", "Administrator")
        ],
        validators=[DataRequired()]
    )
    hospital_id = SelectField("Hospital Assignment (for Hospital Desk role only)", coerce=int, validators=[Optional()])
    submit = SubmitField("Update Role")


class UserCreateForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    display_name = StringField("Full Display Name", validators=[DataRequired(), Length(min=2, max=120)])
    password = PasswordField("Initial Password", validators=[DataRequired(), Length(min=6, max=100)])
    role = SelectField(
        "System Role",
        choices=[
            ("policyholder", "Policyholder"),
            ("hospital", "Hospital Desk"),
            ("claims_officer", "Claims Officer"),
            ("admin", "Administrator")
        ],
        validators=[DataRequired()]
    )
    hospital_id = SelectField("Hospital Assignment (Hospital Desk only)", coerce=int, validators=[Optional()])
    submit = SubmitField("Create User Account")


class PolicyPurchaseForm(FlaskForm):
    """
    Form for policyholders to purchase a health insurance policy.
    Validates plan selection, primary insured details, covered family members, nominee, and terms.
    """
    plan_id = SelectField("Selected Insurance Plan", coerce=int, validators=[DataRequired(message="Please select an insurance plan.")])
    start_date = DateField("Policy Start Date", format="%Y-%m-%d", default=date.today, validators=[DataRequired(message="Please specify policy start date.")])
    primary_member_name = StringField("Primary Insured Full Name", validators=[DataRequired(message="Primary member name is required."), Length(min=2, max=120)])
    nominee_name = StringField("Nominee Name", validators=[DataRequired(message="Nominee full name is required."), Length(min=2, max=120)])
    nominee_relationship = SelectField(
        "Nominee Relationship",
        choices=[
            ("spouse", "Spouse"),
            ("child", "Child"),
            ("parent", "Parent"),
            ("sibling", "Sibling"),
            ("other", "Other")
        ],
        default="spouse",
        validators=[DataRequired(message="Please select nominee relationship.")]
    )
    
    # Dependent Coverage Add-ons
    include_spouse = BooleanField("Add Spouse to Policy (+₹2,500/yr)")
    spouse_name = StringField("Spouse Full Name", validators=[Optional(), Length(max=120)])
    
    include_child1 = BooleanField("Add Child 1 to Policy (+₹1,500/yr)")
    child1_name = StringField("Child 1 Full Name", validators=[Optional(), Length(max=120)])
    
    include_child2 = BooleanField("Add Child 2 to Policy (+₹1,500/yr)")
    child2_name = StringField("Child 2 Full Name", validators=[Optional(), Length(max=120)])
    
    include_parent = BooleanField("Add Senior Parent to Policy (+₹3,500/yr)")
    parent_name = StringField("Parent Full Name", validators=[Optional(), Length(max=120)])

    # Payment & Declarations
    payment_method = SelectField(
        "Payment Method",
        choices=[
            ("simulated_upi", "Instant UPI / NetBanking (Simulated Instant Confirmation)"),
            ("offline_neft", "Direct NEFT / Corporate Invoice (Awaiting Confirmation)")
        ],
        default="simulated_upi",
        validators=[DataRequired(message="Please choose a payment method.")]
    )
    agree_terms = BooleanField(
        "I confirm all health details are accurate and agree to policy coverage terms & conditions.",
        validators=[DataRequired(message="You must review and accept the policy terms and health declaration.")]
    )
    submit = SubmitField("Confirm & Buy Policy")

    def validate_start_date(self, field):
        if field.data and field.data < date.today():
            raise ValidationError("Policy start date cannot be in the past.")

    def validate_spouse_name(self, field):
        if self.include_spouse.data and not (field.data and field.data.strip()):
            raise ValidationError("Please provide full name for your spouse.")

    def validate_child1_name(self, field):
        if self.include_child1.data and not (field.data and field.data.strip()):
            raise ValidationError("Please provide full name for Child 1.")

    def validate_child2_name(self, field):
        if self.include_child2.data and not (field.data and field.data.strip()):
            raise ValidationError("Please provide full name for Child 2.")

    def validate_parent_name(self, field):
        if self.include_parent.data and not (field.data and field.data.strip()):
            raise ValidationError("Please provide full name for your parent.")

