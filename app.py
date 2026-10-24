import sys
import os
import getpass
import csv
import io
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import wraps
from werkzeug.local import LocalProxy
from werkzeug.utils import secure_filename
from flask import (
    Flask, render_template, redirect, url_for, flash, request,
    abort, jsonify, session, g, send_from_directory, Response
)
from sqlalchemy import or_, and_, func

# Ensure directory is on sys.path for direct "python app.py" execution
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

if __package__:
    from .config import Config
    from .extensions import db
    from .models import (
        User, AnonymousUser, Hospital, Plan, Policy, Member, Claim,
        ClaimDocument, ClaimHistory, Settlement, Notification
    )
    from .forms import (
        LoginForm, ClaimForm, DocumentChecklistForm, DocumentUploadForm,
        ReviewDecisionForm, MoreInfoResponseForm, SettlementForm,
        WithdrawClaimForm, HospitalForm, PlanForm, UserRoleForm, UserCreateForm,
        PolicyPurchaseForm
    )
    from .services import (
        calculate_remaining_cover, calculate_claim_payout,
        detect_potential_duplicates, can_user_view_claim, can_user_edit_claim,
        assign_claim_to_officer, process_review_decision, record_simulated_settlement,
        withdraw_claim, save_uploaded_document, create_notification,
        get_dashboard_metrics, add_claim_history, round_inr,
        calculate_policy_premium, validate_and_purchase_policy
    )
else:
    from config import Config
    from extensions import db
    from models import (
        User, AnonymousUser, Hospital, Plan, Policy, Member, Claim,
        ClaimDocument, ClaimHistory, Settlement, Notification
    )
    from forms import (
        LoginForm, ClaimForm, DocumentChecklistForm, DocumentUploadForm,
        ReviewDecisionForm, MoreInfoResponseForm, SettlementForm,
        WithdrawClaimForm, HospitalForm, PlanForm, UserRoleForm, UserCreateForm,
        PolicyPurchaseForm
    )
    from services import (
        calculate_remaining_cover, calculate_claim_payout,
        detect_potential_duplicates, can_user_view_claim, can_user_edit_claim,
        assign_claim_to_officer, process_review_decision, record_simulated_settlement,
        withdraw_claim, save_uploaded_document, create_notification,
        get_dashboard_metrics, add_claim_history, round_inr,
        calculate_policy_premium, validate_and_purchase_policy
    )

# In-memory login attempt tracker for rate limiting
_login_attempts = {}

def get_current_user():
    """Retrieve currently authenticated user from Flask request context or return AnonymousUser."""
    return getattr(g, "current_user", None) or AnonymousUser()

current_user = LocalProxy(get_current_user)

def login_user(user, remember=False):
    """Store user session into Flask signed cookie session."""
    session["user_id"] = user.user_id
    if remember:
        session.permanent = True
    g.current_user = user

def logout_user():
    """Clear user session."""
    session.pop("user_id", None)
    g.current_user = AnonymousUser()

def login_required(f):
    """Protect route requiring active user authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "info")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    
    # Ensure upload directory exists
    os.makedirs(app.config.get("UPLOAD_FOLDER", os.path.join(_current_dir, "uploads")), exist_ok=True)

    @app.before_request
    def load_logged_in_user():
        user_id = session.get("user_id")
        if user_id is None:
            g.current_user = AnonymousUser()
        else:
            g.current_user = db.session.get(User, user_id) or AnonymousUser()

    @app.context_processor
    def inject_current_user():
        unread_notifs = 0
        if current_user.is_authenticated:
            unread_notifs = Notification.query.filter_by(user_id=current_user.user_id, is_read=False).count()
        return dict(
            current_user=get_current_user(),
            unread_notifications_count=unread_notifs,
            csrf_token=lambda: ""
        )

    # --- Role Decorators ---
    def require_role(*roles):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not current_user.is_authenticated or current_user.role not in roles:
                    abort(403)
                return f(*args, **kwargs)
            return decorated_function
        return decorator

    # --- Error Handlers ---
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("500.html"), 500

    # --- Context Processors ---
    @app.context_processor
    def inject_globals():
        return {
            "current_year": datetime.utcnow().year,
            "format_inr": lambda val: f"₹{Decimal(str(val or 0)):,.2f}" if val is not None else "₹0.00"
        }

    # --- Authentication Routes ---
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
            
        form = LoginForm()
        ip_addr = request.remote_addr or "127.0.0.1"

        if form.validate_on_submit():
            username = form.username.data.strip()
            now = datetime.utcnow()

            # Check rate limiting (max 5 failed attempts within 15 minutes)
            attempts_info = _login_attempts.get(ip_addr, {"count": 0, "lockout_until": None})
            if attempts_info["lockout_until"] and now < attempts_info["lockout_until"]:
                mins_left = int((attempts_info["lockout_until"] - now).total_seconds() / 60) + 1
                flash(f"Too many failed login attempts. Please try again in {mins_left} minute(s).", "danger")
                return render_template("login.html", form=form)

            user = User.query.filter_by(username=username).first()
            if user and user.check_password(form.password.data):
                # Reset rate limiter on success
                _login_attempts.pop(ip_addr, None)
                login_user(user, remember=form.remember_me.data)
                flash(f"Welcome back, {user.display_name}!", "success")
                next_page = request.args.get("next")
                if next_page and next_page.startswith("/"):
                    return redirect(next_page)
                return redirect(url_for("dashboard"))
            else:
                # Increment failed attempts
                attempts_info["count"] += 1
                if attempts_info["count"] >= 5:
                    attempts_info["lockout_until"] = now + timedelta(minutes=15)
                    flash("Too many failed attempts. Account login throttled for 15 minutes.", "danger")
                else:
                    flash("Invalid username or password. Please verify your credentials.", "danger")
                _login_attempts[ip_addr] = attempts_info
                
        return render_template("login.html", form=form)

    @app.route("/logout", methods=["GET", "POST"])
    @login_required
    def logout():
        logout_user()
        flash("You have been securely logged out.", "info")
        return redirect(url_for("login"))

    @app.route("/switch-role/<role>")
    @login_required
    def switch_role(role):
        # In non-development / production environments, role switching is strictly forbidden
        if not (app.debug or app.testing or os.getenv("FLASK_ENV") != "production"):
            abort(403)

        role_map = {
            "policyholder": "aasha",
            "hospital": "city_hospital",
            "hospital_desk": "city_hospital",
            "claims_officer": "officer_meera",
            "admin": "admin_demo"
        }
        target_username = role_map.get(role)
        if target_username:
            target_user = User.query.filter_by(username=target_username).first()
            if target_user:
                login_user(target_user)
                flash(f"Switched role to {target_user.display_name} ({target_user.role.replace('_', ' ').title()}).", "success")
        return redirect(url_for("dashboard"))

    # --- In-App Notifications ---
    @app.route("/notifications")
    @login_required
    def notifications():
        user_notifs = Notification.query.filter_by(user_id=current_user.user_id).order_by(Notification.created_at.desc()).limit(50).all()
        return render_template("notifications.html", notifications=user_notifs)

    @app.route("/notifications/<int:notification_id>/read", methods=["POST"])
    @login_required
    def mark_notification_read(notification_id):
        notif = Notification.query.get_or_404(notification_id)
        if notif.user_id != current_user.user_id:
            abort(403)
        notif.is_read = True
        db.session.commit()
        return redirect(request.referrer or url_for("notifications"))

    @app.route("/notifications/mark-all-read", methods=["POST"])
    @login_required
    def mark_all_notifications_read():
        Notification.query.filter_by(user_id=current_user.user_id, is_read=False).update({"is_read": True})
        db.session.commit()
        flash("All notifications marked as read.", "success")
        return redirect(url_for("notifications"))

    # --- Dashboards & Lists ---
    @app.route("/dashboard")
    @login_required
    def dashboard():
        metrics = get_dashboard_metrics(current_user)
        return render_template("dashboard.html", metrics=metrics)

    @app.route("/policies")
    @login_required
    def my_policies():
        status_filter = request.args.get("status", "all")
        search_query = request.args.get("q", "").strip()

        if current_user.is_policyholder:
            query = Policy.query.filter_by(holder_user_id=current_user.user_id)
        elif current_user.is_admin or current_user.is_claims_officer:
            query = Policy.query
        else:
            abort(403)

        if status_filter in ["active", "expired"]:
            query = query.filter_by(status=status_filter)

        if search_query:
            query = query.join(Plan).filter(
                or_(
                    Policy.policy_id.cast(db.String).ilike(f"%{search_query}%"),
                    Plan.plan_name.ilike(f"%{search_query}%")
                )
            )

        policies = query.order_by(Policy.policy_id.asc()).all()
        return render_template("my_policies.html", policies=policies, status_filter=status_filter, search_query=search_query)

    @app.route("/buy-policy", methods=["GET", "POST"])
    @login_required
    def buy_policy():
        """
        Policy Purchase Workflow:
        1. View Available Plans (from database)
        2. Select a Plan
        3. Enter Required Details (primary member, dependents, start date)
        4. Review Premium & Coverage (calculated via audited business rules)
        5. Confirm Purchase & Persist
        """
        if not current_user.is_policyholder:
            flash("Policy purchase is exclusively available for Policyholders.", "warning")
            abort(403)

        plans = Plan.query.order_by(Plan.annual_limit_inr.asc()).all()
        if not plans:
            flash("No active insurance plans available for purchase at this time.", "danger")
            return redirect(url_for("my_policies"))

        # Pre-calculate base premiums and features for comparison catalog
        plan_catalog = []
        for p in plans:
            p_info = calculate_policy_premium(p, ["self"])
            plan_catalog.append({
                "plan": p,
                "premium": p_info
            })

        form = PolicyPurchaseForm()
        form.plan_id.choices = [
            (p.plan_id, f"{p.plan_name} — ₹{p.annual_limit_inr:,.0f} Sum Insured (Base ₹{calculate_policy_premium(p)['base_premium']:,.0f}/yr)")
            for p in plans
        ]

        # Handle GET requests (initial render & pre-selections)
        if request.method == "GET":
            preselected_plan_id = request.args.get("plan_id", type=int)
            if preselected_plan_id and any(p.plan_id == preselected_plan_id for p in plans):
                form.plan_id.data = preselected_plan_id
            elif plans:
                form.plan_id.data = plans[0].plan_id

            if not form.primary_member_name.data:
                form.primary_member_name.data = current_user.display_name
            if not form.start_date.data:
                form.start_date.data = date.today()

        # Handle POST requests (validation & purchase confirmation)
        elif request.method == "POST":
            if form.validate_on_submit():
                # Collate dependent members
                dependents = []
                if form.include_spouse.data and form.spouse_name.data and form.spouse_name.data.strip():
                    dependents.append({"name": form.spouse_name.data.strip(), "relationship": "spouse"})
                if form.include_child1.data and form.child1_name.data and form.child1_name.data.strip():
                    dependents.append({"name": form.child1_name.data.strip(), "relationship": "child"})
                if form.include_child2.data and form.child2_name.data and form.child2_name.data.strip():
                    dependents.append({"name": form.child2_name.data.strip(), "relationship": "child"})
                if form.include_parent.data and form.parent_name.data and form.parent_name.data.strip():
                    dependents.append({"name": form.parent_name.data.strip(), "relationship": "parent"})

                success, message, new_policy, breakdown = validate_and_purchase_policy(
                    user=current_user,
                    plan_id=form.plan_id.data,
                    start_date=form.start_date.data,
                    primary_member_name=form.primary_member_name.data,
                    dependents=dependents,
                    payment_mode=form.payment_method.data
                )

                if success and new_policy:
                    flash(message, "success")
                    return redirect(url_for("buy_policy_success", policy_id=new_policy.policy_id))
                else:
                    flash(message, "danger")
            else:
                for field_name, err_list in form.errors.items():
                    for err in err_list:
                        flash(f"{getattr(form, field_name).label.text}: {err}", "danger")

        # Compute initial active breakdown for server-side preview rendering
        selected_plan_id = form.plan_id.data or (plans[0].plan_id if plans else 1)
        selected_plan = db.session.get(Plan, selected_plan_id) or plans[0]
        active_rels = ["self"]
        if form.include_spouse.data:
            active_rels.append("spouse")
        if form.include_child1.data:
            active_rels.append("child")
        if form.include_child2.data:
            active_rels.append("child")
        if form.include_parent.data:
            active_rels.append("parent")
        active_breakdown = calculate_policy_premium(selected_plan, active_rels)

        return render_template(
            "buy_policy.html",
            form=form,
            plans=plans,
            plan_catalog=plan_catalog,
            selected_plan=selected_plan,
            active_breakdown=active_breakdown
        )

    @app.route("/buy-policy/success/<int:policy_id>")
    @login_required
    def buy_policy_success(policy_id):
        """Display purchase confirmation and issued policy receipt details."""
        policy = Policy.query.get_or_404(policy_id)
        if not (policy.holder_user_id == current_user.user_id or current_user.is_admin):
            abort(403)

        relationships = [m.relationship_type for m in policy.members]
        breakdown = calculate_policy_premium(policy.plan, relationships)

        return render_template(
            "buy_policy_success.html",
            policy=policy,
            breakdown=breakdown
        )

    @app.route("/api/plan-premium/<int:plan_id>")
    @login_required
    def api_plan_premium(plan_id):
        """API endpoint for live interactive premium recalculation on the frontend."""
        plan = Plan.query.get_or_404(plan_id)
        rels = request.args.getlist("rel")
        if not rels:
            rels = ["self"]
        breakdown = calculate_policy_premium(plan, rels)
        # Format for JSON serialization
        return jsonify({
            "plan_id": breakdown["plan_id"],
            "plan_name": breakdown["plan_name"],
            "annual_limit_inr": float(breakdown["annual_limit_inr"]),
            "deductible_inr": float(breakdown["deductible_inr"]),
            "copay_percent": float(breakdown["copay_percent"]),
            "base_premium": float(breakdown["base_premium"]),
            "dependent_premium": float(breakdown["dependent_premium"]),
            "net_premium": float(breakdown["net_premium"]),
            "gst_rate_percent": float(breakdown["gst_rate_percent"]),
            "gst_amount": float(breakdown["gst_amount"]),
            "total_annual_premium": float(breakdown["total_annual_premium"]),
            "total_members": breakdown["total_members"],
            "dependent_breakdown": [
                {
                    "relationship": d["relationship"],
                    "label": d["label"],
                    "amount": float(d["amount"])
                }
                for d in breakdown["dependent_breakdown"]
            ]
        })

    @app.route("/hospitals")
    @login_required
    def hospitals():
        search_query = request.args.get("name", "").strip()
        city_filter = request.args.get("city", "").strip()
        network_filter = request.args.get("network", "").strip()

        query = Hospital.query
        if search_query:
            query = query.filter(Hospital.name.ilike(f"%{search_query}%"))
        if city_filter:
            query = query.filter_by(city=city_filter)
        if network_filter in ["1", "0"]:
            query = query.filter_by(network_status=bool(int(network_filter)))

        all_cities = [c[0] for c in db.session.query(Hospital.city).distinct().order_by(Hospital.city).all()]
        hospitals_list = query.order_by(Hospital.name.asc()).all()
        return render_template(
            "hospitals.html",
            hospitals=hospitals_list,
            cities=all_cities,
            search_query=search_query,
            selected_city=city_filter,
            selected_network=network_filter
        )

    @app.route("/claims")
    @login_required
    def claim_list():
        search_q = request.args.get("q", "").strip()
        status_f = request.args.get("status", "").strip()
        type_f = request.args.get("type", "").strip()
        hospital_f = request.args.get("hospital", "").strip()

        # Base role authorization scoping
        if current_user.is_policyholder:
            query = Claim.query.join(Policy).filter(Policy.holder_user_id == current_user.user_id)
        elif current_user.is_hospital_desk:
            query = Claim.query.filter(Claim.hospital_id == current_user.hospital_id)
        elif current_user.is_claims_officer or current_user.is_admin:
            query = Claim.query
        else:
            abort(403)

        # Apply user filters
        if status_f:
            query = query.filter(Claim.status == status_f)
        if type_f:
            query = query.filter(Claim.claim_type == type_f)
        if hospital_f:
            try:
                hid = int(hospital_f)
                query = query.filter(Claim.hospital_id == hid)
            except ValueError:
                pass
        if search_q:
            query = query.join(Member).filter(
                or_(
                    Claim.claim_id.cast(db.String).ilike(f"%{search_q}%"),
                    Member.display_name.ilike(f"%{search_q}%")
                )
            )

        claims = query.order_by(Claim.claim_id.desc()).all()
        all_hospitals = Hospital.query.order_by(Hospital.name.asc()).all()

        counts = {
            "total": len(claims),
            "submitted": sum(1 for c in claims if c.status == "submitted"),
            "in_review": sum(1 for c in claims if c.status == "in_review"),
            "approved": sum(1 for c in claims if c.status == "approved"),
            "rejected": sum(1 for c in claims if c.status == "rejected"),
            "more_info": sum(1 for c in claims if c.status == "more_info"),
            "paid": sum(1 for c in claims if c.status == "paid"),
        }

        return render_template(
            "claim_list.html",
            claims=claims,
            counts=counts,
            hospitals=all_hospitals,
            search_q=search_q,
            status_f=status_f,
            type_f=type_f,
            hospital_f=hospital_f
        )

    @app.route("/claims/<int:claim_id>")
    @login_required
    def claim_detail(claim_id):
        claim = Claim.query.get_or_404(claim_id)
        if not can_user_view_claim(current_user, claim):
            abort(403)

        duplicates = detect_potential_duplicates(claim) if (current_user.is_claims_officer or current_user.is_admin) else []
        remaining_cover = calculate_remaining_cover(claim.policy, claim.admission_date)
        
        payout_info = None
        if claim.eligible_amount_inr:
            payout_info = calculate_claim_payout(claim.eligible_amount_inr, claim.policy.plan)

        checklist_form = DocumentChecklistForm()
        doc_dict = {d.document_type: d.checklist_status for d in claim.documents}
        checklist_form.hospital_bill.data = doc_dict.get("hospital_bill", "missing")
        checklist_form.discharge_summary.data = doc_dict.get("discharge_summary", "missing")

        upload_form = DocumentUploadForm()
        decision_form = ReviewDecisionForm()
        more_info_form = MoreInfoResponseForm()
        settlement_form = SettlementForm()
        withdraw_form = WithdrawClaimForm()

        return render_template(
            "claim_detail.html",
            claim=claim,
            duplicates=duplicates,
            remaining_cover=remaining_cover,
            payout_info=payout_info,
            checklist_form=checklist_form,
            upload_form=upload_form,
            decision_form=decision_form,
            more_info_form=more_info_form,
            settlement_form=settlement_form,
            withdraw_form=withdraw_form
        )

    @app.route("/claims/new", methods=["GET", "POST"])
    @login_required
    def new_claim():
        if not (current_user.is_policyholder or current_user.is_hospital_desk):
            abort(403)

        form = ClaimForm()

        # Populate Select choices based on user role
        if current_user.is_policyholder:
            user_policies = Policy.query.filter_by(holder_user_id=current_user.user_id, status="active").all()
            if not user_policies:
                flash("You do not have any active policies to file a claim against.", "warning")
                return redirect(url_for("my_policies"))
            form.policy_id.choices = [(p.policy_id, f"Policy #{p.policy_id} - {p.plan.plan_name}") for p in user_policies]
            
            selected_pol_id = form.policy_id.data or user_policies[0].policy_id
            members = Member.query.filter_by(policy_id=selected_pol_id).all()
            form.member_id.choices = [(m.member_id, f"{m.display_name} ({m.relationship_type})") for m in members]
            
            form.hospital_id.choices = [(h.hospital_id, f"{h.name} - {h.city}") for h in Hospital.query.order_by(Hospital.name).all()]
            form.claim_type.choices = [("reimbursement", "Reimbursement"), ("cashless", "Cashless")]
            
        elif current_user.is_hospital_desk:
            my_hospital = Hospital.query.get(current_user.hospital_id)
            if not my_hospital or not my_hospital.network_status:
                flash("Your hospital is not currently in the approved cashless network.", "danger")
                return redirect(url_for("claim_list"))
                
            form.hospital_id.choices = [(my_hospital.hospital_id, f"{my_hospital.name} (Network Desk)")]
            form.claim_type.choices = [("cashless", "Cashless")]
            
            active_pols = Policy.query.filter_by(status="active").all()
            form.policy_id.choices = [(p.policy_id, f"Policy #{p.policy_id} ({p.holder.display_name}) - {p.plan.plan_name}") for p in active_pols]
            selected_pol_id = form.policy_id.data or (active_pols[0].policy_id if active_pols else None)
            members = Member.query.filter_by(policy_id=selected_pol_id).all() if selected_pol_id else []
            form.member_id.choices = [(m.member_id, f"{m.display_name} ({m.relationship_type})") for m in members]

        # Collate policy coverage limits metadata for client-side and server-side checks
        policy_limits = {}
        candidate_policies = user_policies if current_user.is_policyholder else active_pols
        for p in candidate_policies:
            rem = calculate_remaining_cover(p, date.today())
            max_limit = min(rem, p.plan.annual_limit_inr)
            policy_limits[p.policy_id] = {
                "annual_limit": float(p.plan.annual_limit_inr),
                "remaining_cover": float(rem),
                "max_allowed": float(max_limit),
                "plan_name": p.plan.plan_name,
                "deductible": float(p.plan.deductible_inr),
                "copay": float(p.plan.copay_percent)
            }

        if form.validate_on_submit():
            is_submit_action = bool(form.submit_claim.data)
            target_status = "in_review" if is_submit_action else "draft"
            
            policy = Policy.query.get(form.policy_id.data)
            member = Member.query.get(form.member_id.data)
            hospital = Hospital.query.get(form.hospital_id.data)
            
            if not policy or member.policy_id != policy.policy_id:
                flash("Selected member does not belong to the selected policy.", "danger")
                return render_template("claim_form.html", form=form, is_edit=False, policy_limits=policy_limits)

            if current_user.is_hospital_desk and hospital.hospital_id != current_user.hospital_id:
                flash("Hospital desk users can only create claims for their own hospital.", "danger")
                return render_template("claim_form.html", form=form, is_edit=False, policy_limits=policy_limits)

            if form.claim_type.data == "cashless" and not hospital.network_status:
                flash("Cashless claims can only be filed at network hospitals.", "danger")
                return render_template("claim_form.html", form=form, is_edit=False, policy_limits=policy_limits)

            if is_submit_action and form.admission_date.data > date.today():
                flash("Cannot submit a claim with a future admission date. Save as Draft until admission.", "danger")
                return render_template("claim_form.html", form=form, is_edit=False, policy_limits=policy_limits)

            # Strict Policy Amount Validation: User cannot enter more than the policy coverage amount
            remaining_cover = calculate_remaining_cover(policy, form.admission_date.data)
            max_policy_amount = min(remaining_cover, policy.plan.annual_limit_inr)
            requested_val = round_inr(Decimal(str(form.requested_amount_inr.data)))
            if requested_val > max_policy_amount:
                flash(
                    f"Validation Error: Claim amount (₹{requested_val:,.2f}) cannot exceed the maximum policy coverage limit of ₹{max_policy_amount:,.2f}. Please adjust the requested amount.",
                    "danger"
                )
                return render_template("claim_form.html", form=form, is_edit=False, policy_limits=policy_limits)

            # Automatic Round-Robin Assignment Method across Claims Officers
            assigned_officer = None
            if is_submit_action:
                officers = User.query.filter_by(role="claims_officer").order_by(User.user_id.asc()).all()
                if officers:
                    # Find the most recently assigned claim to determine next officer in the round-robin ring
                    last_assigned = Claim.query.filter(Claim.officer_user_id.isnot(None)).order_by(Claim.claim_id.desc()).first()
                    if last_assigned and last_assigned.officer_user_id:
                        officer_ids = [o.user_id for o in officers]
                        try:
                            last_idx = officer_ids.index(last_assigned.officer_user_id)
                            next_idx = (last_idx + 1) % len(officers)
                        except ValueError:
                            next_idx = 0
                        assigned_officer = officers[next_idx]
                    else:
                        assigned_officer = officers[0]

            try:
                claim = Claim(
                    policy_id=policy.policy_id,
                    member_id=member.member_id,
                    hospital_id=hospital.hospital_id,
                    claim_type=form.claim_type.data,
                    treatment_type=form.treatment_type.data,
                    admission_date=form.admission_date.data,
                    discharge_date=form.discharge_date.data,
                    requested_amount_inr=requested_val,
                    status=target_status,
                    officer_user_id=assigned_officer.user_id if assigned_officer else None,
                    description=form.description.data.strip() if form.description.data else None,
                    submitted_at=datetime.utcnow() if is_submit_action else None
                )
                db.session.add(claim)
                db.session.flush()

                # Add default documents checklist
                doc_bill = ClaimDocument(claim_id=claim.claim_id, document_type="hospital_bill", checklist_status="received" if is_submit_action else "missing")
                doc_summary = ClaimDocument(claim_id=claim.claim_id, document_type="discharge_summary", checklist_status="received" if is_submit_action else "missing")
                db.session.add_all([doc_bill, doc_summary])

                note = (
                    f"Claim submitted by user and automatically assigned to Claims Officer {assigned_officer.display_name} via Round-Robin method."
                    if (is_submit_action and assigned_officer)
                    else "Claim submitted by user for adjudication review."
                    if is_submit_action
                    else "Claim created as draft."
                )
                add_claim_history(
                    claim_id=claim.claim_id,
                    from_status=None if not is_submit_action else "draft",
                    to_status=target_status,
                    actor_user_id=current_user.user_id,
                    note=note
                )
                
                # Notify assigned officer directly if submitted
                if is_submit_action and assigned_officer:
                    create_notification(
                        user_id=assigned_officer.user_id,
                        title="Claim Assigned (Round-Robin)",
                        message=f"Claim CLM-{claim.claim_id:06d} for {member.display_name} (₹{claim.requested_amount_inr:,.2f}) has been automatically assigned to you via Round-Robin method.",
                        category="info",
                        claim_id=claim.claim_id
                    )

                db.session.commit()
                flash(
                    f"Claim CLM-{claim.claim_id:06d} successfully submitted and assigned to Claims Officer {assigned_officer.display_name if assigned_officer else 'the Review Queue'}!"
                    if is_submit_action
                    else f"Claim CLM-{claim.claim_id:06d} saved as Draft.",
                    "success"
                )
                return redirect(url_for("claim_detail", claim_id=claim.claim_id))
            except Exception as e:
                db.session.rollback()
                flash(f"Error creating claim: {str(e)}", "danger")

        return render_template("claim_form.html", form=form, is_edit=False, policy_limits=policy_limits)

    @app.route("/claims/<int:claim_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_claim(claim_id):
        claim = Claim.query.get_or_404(claim_id)
        if not can_user_edit_claim(current_user, claim):
            abort(403)
        if claim.status not in ["draft", "more_info"]:
            flash(f"Claim in '{claim.status}' status cannot be edited.", "warning")
            return redirect(url_for("claim_detail", claim_id=claim_id))

        form = ClaimForm(obj=claim)
        
        # Populate Select choices
        if current_user.is_policyholder:
            user_policies = Policy.query.filter_by(holder_user_id=current_user.user_id, status="active").all()
            form.policy_id.choices = [(p.policy_id, f"Policy #{p.policy_id} - {p.plan.plan_name}") for p in user_policies]
            members = Member.query.filter_by(policy_id=claim.policy_id).all()
            form.member_id.choices = [(m.member_id, f"{m.display_name} ({m.relationship_type})") for m in members]
            form.hospital_id.choices = [(h.hospital_id, f"{h.name} - {h.city}") for h in Hospital.query.order_by(Hospital.name).all()]
            form.claim_type.choices = [("reimbursement", "Reimbursement"), ("cashless", "Cashless")]
        else:
            my_hospital = Hospital.query.get(current_user.hospital_id)
            form.hospital_id.choices = [(my_hospital.hospital_id, f"{my_hospital.name} (Network Desk)")]
            form.claim_type.choices = [("cashless", "Cashless")]
            active_pols = Policy.query.filter_by(status="active").all()
            form.policy_id.choices = [(p.policy_id, f"Policy #{p.policy_id} ({p.holder.display_name}) - {p.plan.plan_name}") for p in active_pols]
            members = Member.query.filter_by(policy_id=claim.policy_id).all()
            form.member_id.choices = [(m.member_id, f"{m.display_name} ({m.relationship_type})") for m in members]

        if form.validate_on_submit():
            is_submit = bool(form.submit_claim.data)
            claim.policy_id = form.policy_id.data
            claim.member_id = form.member_id.data
            claim.hospital_id = form.hospital_id.data
            claim.treatment_type = form.treatment_type.data
            claim.admission_date = form.admission_date.data
            claim.discharge_date = form.discharge_date.data
            claim.requested_amount_inr = round_inr(Decimal(str(form.requested_amount_inr.data)))
            claim.description = form.description.data.strip() if form.description.data else None
            claim.updated_at = datetime.utcnow()
            
            old_status = claim.status
            if is_submit:
                claim.status = "submitted"
                claim.submitted_at = datetime.utcnow()
                add_claim_history(
                    claim_id=claim.claim_id,
                    from_status=old_status,
                    to_status="submitted",
                    actor_user_id=current_user.user_id,
                    note="Draft updated and submitted for review."
                )
            else:
                add_claim_history(
                    claim_id=claim.claim_id,
                    from_status=old_status,
                    to_status=old_status,
                    actor_user_id=current_user.user_id,
                    note="Draft claim details updated."
                )
            db.session.commit()
            flash("Claim updated successfully.", "success")
            return redirect(url_for("claim_detail", claim_id=claim.claim_id))

        return render_template("claim_form.html", form=form, is_edit=True, claim=claim)

    @app.route("/claims/<int:claim_id>/withdraw", methods=["POST"])
    @login_required
    def withdraw_claim_route(claim_id):
        form = WithdrawClaimForm()
        if form.validate_on_submit():
            reason = form.reason.data.strip()
            ok, msg = withdraw_claim(claim_id, current_user, reason)
            flash(msg, "success" if ok else "danger")
        else:
            flash("Please provide a valid withdrawal reason.", "danger")
        return redirect(url_for("claim_detail", claim_id=claim_id))

    @app.route("/claims/<int:claim_id>/upload-document", methods=["POST"])
    @login_required
    def upload_document(claim_id):
        claim = Claim.query.get_or_404(claim_id)
        if not can_user_view_claim(current_user, claim):
            abort(403)
            
        form = DocumentUploadForm()
        if form.validate_on_submit():
            file_storage = form.document_file.data
            doc_type = form.document_type.data
            upload_dir = app.config.get("UPLOAD_FOLDER", os.path.join(_current_dir, "uploads"))
            ok, msg = save_uploaded_document(claim, doc_type, file_storage, current_user, upload_dir)
            flash(msg, "success" if ok else "danger")
        else:
            flash("Invalid document format or size. Only PDF, PNG, JPG files up to 10MB are permitted.", "danger")
        return redirect(url_for("claim_detail", claim_id=claim_id))

    @app.route("/claims/<int:claim_id>/documents/<int:document_id>/download")
    @login_required
    def download_document(claim_id, document_id):
        claim = Claim.query.get_or_404(claim_id)
        if not can_user_view_claim(current_user, claim):
            abort(403)
            
        doc = ClaimDocument.query.filter_by(document_id=document_id, claim_id=claim_id).first_or_404()
        if not doc.storage_key:
            abort(404)
            
        upload_dir = app.config.get("UPLOAD_FOLDER", os.path.join(_current_dir, "uploads"))
        return send_from_directory(
            upload_dir,
            doc.storage_key,
            as_attachment=True,
            download_name=doc.original_filename or f"doc_{claim_id}_{doc.document_type}.pdf"
        )

    @app.route("/claims/<int:claim_id>/assign", methods=["POST"])
    @login_required
    @require_role("claims_officer")
    def assign_claim(claim_id):
        success, message = assign_claim_to_officer(claim_id, current_user)
        category = "success" if success else "danger"
        flash(message, category)
        return redirect(url_for("claim_detail", claim_id=claim_id))

    @app.route("/claims/<int:claim_id>/review", methods=["POST"])
    @login_required
    @require_role("claims_officer")
    def review_decision(claim_id):
        form = ReviewDecisionForm()
        if form.validate_on_submit():
            action = form.action.data
            reason = form.decision_reason.data
            eligible_amt = form.eligible_amount_inr.data
            
            success, msg = process_review_decision(
                claim_id=claim_id,
                officer=current_user,
                action=action,
                decision_reason=reason,
                eligible_amount=eligible_amt
            )
            flash(msg, "success" if success else "danger")
        else:
            flash("Please provide a valid decision reason and eligible amount.", "danger")
        return redirect(url_for("claim_detail", claim_id=claim_id))

    @app.route("/claims/<int:claim_id>/documents", methods=["POST"])
    @login_required
    def update_documents(claim_id):
        claim = Claim.query.get_or_404(claim_id)
        if not can_user_view_claim(current_user, claim):
            abort(403)
            
        form = DocumentChecklistForm()
        if form.validate_on_submit():
            doc_bill = ClaimDocument.query.filter_by(claim_id=claim_id, document_type="hospital_bill").first()
            if not doc_bill:
                doc_bill = ClaimDocument(claim_id=claim_id, document_type="hospital_bill")
                db.session.add(doc_bill)
            if not (doc_bill.checklist_status == "received" and form.hospital_bill.data == "missing"):
                doc_bill.checklist_status = form.hospital_bill.data

            doc_summary = ClaimDocument.query.filter_by(claim_id=claim_id, document_type="discharge_summary").first()
            if not doc_summary:
                doc_summary = ClaimDocument(claim_id=claim_id, document_type="discharge_summary")
                db.session.add(doc_summary)
            if not (doc_summary.checklist_status == "received" and form.discharge_summary.data == "missing"):
                doc_summary.checklist_status = form.discharge_summary.data

            note = form.notes.data.strip() if form.notes.data else "Checklist updated."
            add_claim_history(
                claim_id=claim_id,
                from_status=claim.status,
                to_status=claim.status,
                actor_user_id=current_user.user_id,
                note=f"Documents updated: Hospital Bill={doc_bill.checklist_status}, Discharge Summary={doc_summary.checklist_status}. Note: {note}"
            )
            db.session.commit()
            flash("Document checklist updated successfully.", "success")
        return redirect(url_for("claim_detail", claim_id=claim_id))

    @app.route("/claims/<int:claim_id>/respond", methods=["POST"])
    @login_required
    def respond_more_info(claim_id):
        claim = Claim.query.get_or_404(claim_id)
        if not can_user_edit_claim(current_user, claim) or claim.status != "more_info":
            abort(403)

        form = MoreInfoResponseForm()
        if form.validate_on_submit():
            response = form.response_note.data.strip()
            old_status = claim.status
            claim.status = "submitted"
            claim.updated_at = datetime.utcnow()
            add_claim_history(
                claim_id=claim.claim_id,
                from_status=old_status,
                to_status="submitted",
                actor_user_id=current_user.user_id,
                note=f"Submitter Responded: {response}"
            )
            # Notify assigned officer if present
            if claim.officer_user_id:
                create_notification(
                    user_id=claim.officer_user_id,
                    title="Information Response Received",
                    message=f"Submitter responded to info request for CLM-{claim.claim_id:06d}: {response[:120]}...",
                    category="info",
                    claim_id=claim.claim_id
                )
            db.session.commit()
            flash("Information submitted. Claim returned to Submitted status for review.", "success")
        return redirect(url_for("claim_detail", claim_id=claim_id))

    @app.route("/claims/<int:claim_id>/settle", methods=["POST"])
    @login_required
    @require_role("admin")
    def settle_claim(claim_id):
        success, msg = record_simulated_settlement(claim_id, current_user)
        flash(msg, "success" if success else "danger")
        return redirect(url_for("claim_detail", claim_id=claim_id))

    @app.route("/review-queue")
    @login_required
    @require_role("claims_officer")
    def review_queue():
        filter_type = request.args.get("filter", "assigned")
        search_q = request.args.get("q", "").strip()

        base_q = Claim.query
        if filter_type == "assigned":
            base_q = base_q.filter_by(officer_user_id=current_user.user_id, status="in_review")
        elif filter_type == "unassigned":
            base_q = base_q.filter_by(status="submitted", officer_user_id=None)
        elif filter_type == "more_info":
            base_q = base_q.filter_by(officer_user_id=current_user.user_id, status="more_info")
        elif filter_type == "awaiting_decision":
            base_q = base_q.filter_by(officer_user_id=current_user.user_id, status="in_review")

        if search_q:
            base_q = base_q.join(Member).filter(
                or_(
                    Claim.claim_id.cast(db.String).ilike(f"%{search_q}%"),
                    Member.display_name.ilike(f"%{search_q}%")
                )
            )

        claims = base_q.order_by(Claim.admission_date.desc()).all()
        
        counts = {
            "assigned": Claim.query.filter_by(officer_user_id=current_user.user_id, status="in_review").count(),
            "unassigned": Claim.query.filter_by(status="submitted", officer_user_id=None).count(),
            "more_info": Claim.query.filter_by(officer_user_id=current_user.user_id, status="more_info").count(),
            "awaiting_decision": Claim.query.filter_by(officer_user_id=current_user.user_id, status="in_review").count()
        }

        return render_template(
            "review_queue.html",
            claims=claims,
            counts=counts,
            filter_type=filter_type,
            search_q=search_q
        )

    @app.route("/admin/reference-data", methods=["GET", "POST"])
    @login_required
    @require_role("admin")
    def admin_reference_data():
        active_tab = request.args.get("tab", "hospitals")
        hospital_form = HospitalForm()
        plan_form = PlanForm()
        user_form = UserCreateForm()

        if hospital_form.validate_on_submit() and "save_hospital" in request.form:
            h = Hospital(
                name=hospital_form.name.data.strip(),
                city=hospital_form.city.data.strip(),
                network_status=bool(int(hospital_form.network_status.data))
            )
            db.session.add(h)
            db.session.commit()
            flash(f"Hospital '{h.name}' added successfully.", "success")
            return redirect(url_for("admin_reference_data", tab="hospitals"))

        if "save_plan" in request.form:
            plan_name = request.form.get("plan_name", "").strip()
            treatments = request.form.get("covered_treatment_types", "inpatient|daycare").strip()
            try:
                limit = Decimal(request.form.get("annual_limit_inr", "300000"))
                deductible = Decimal(request.form.get("deductible_inr", "1500"))
                copay = Decimal(request.form.get("copay_percent", "10"))
            except Exception:
                limit = Decimal("300000")
                deductible = Decimal("1500")
                copay = Decimal("10")

            if plan_name:
                p = Plan(
                    plan_name=plan_name,
                    covered_treatment_types=treatments,
                    annual_limit_inr=limit,
                    deductible_inr=deductible,
                    copay_percent=copay
                )
                db.session.add(p)
                db.session.commit()
                flash(f"Insurance Plan '{p.plan_name}' added successfully.", "success")
                return redirect(url_for("admin_reference_data", tab="plans"))

        if "create_user" in request.form:
            new_u = request.form.get("username", "").strip()
            disp_u = request.form.get("display_name", "").strip()
            role_u = request.form.get("role", "policyholder").strip()
            pwd_u = request.form.get("password", "").strip()
            hosp_id_val = request.form.get("hospital_id")
            hosp_id = int(hosp_id_val) if hosp_id_val and hosp_id_val.isdigit() else None

            if new_u and disp_u and pwd_u:
                existing_u = User.query.filter_by(username=new_u).first()
                if existing_u:
                    flash(f"Username '{new_u}' already exists.", "danger")
                else:
                    user_record = User(
                        username=new_u,
                        display_name=disp_u,
                        role=role_u,
                        hospital_id=hosp_id if role_u == "hospital" else None
                    )
                    user_record.set_password(pwd_u)
                    db.session.add(user_record)
                    db.session.commit()
                    flash(f"User account '{new_u}' ({role_u}) created successfully.", "success")
                    return redirect(url_for("admin_reference_data", tab="users"))

        if "edit_hospital_id" in request.form:
            h_id = request.form.get("edit_hospital_id", type=int)
            h = Hospital.query.get(h_id)
            if h:
                h.name = request.form.get("name", h.name).strip()
                h.city = request.form.get("city", h.city).strip()
                h.network_status = (request.form.get("network_status") == "1")
                db.session.commit()
                flash(f"Hospital '{h.name}' updated successfully.", "success")
                return redirect(url_for("admin_reference_data", tab="hospitals"))

        if "edit_plan_id" in request.form:
            p_id = request.form.get("edit_plan_id", type=int)
            p = Plan.query.get(p_id)
            if p:
                p.plan_name = request.form.get("plan_name", p.plan_name).strip()
                p.covered_treatment_types = request.form.get("covered_treatment_types", p.covered_treatment_types).strip()
                try:
                    p.annual_limit_inr = Decimal(request.form.get("annual_limit_inr", str(p.annual_limit_inr)))
                    p.deductible_inr = Decimal(request.form.get("deductible_inr", str(p.deductible_inr)))
                    p.copay_percent = Decimal(request.form.get("copay_percent", str(p.copay_percent)))
                except Exception:
                    pass
                db.session.commit()
                flash(f"Plan '{p.plan_name}' updated successfully.", "success")
                return redirect(url_for("admin_reference_data", tab="plans"))

        if "edit_user_id" in request.form:
            u_id = request.form.get("edit_user_id", type=int)
            u = User.query.get(u_id)
            if u:
                u.display_name = request.form.get("display_name", u.display_name).strip()
                u.role = request.form.get("role", u.role).strip()
                hosp_val = request.form.get("hospital_id")
                u.hospital_id = int(hosp_val) if (hosp_val and hosp_val.isdigit() and u.role == "hospital") else None
                db.session.commit()
                flash(f"User account '@{u.username}' updated successfully.", "success")
                return redirect(url_for("admin_reference_data", tab="users"))

        hospitals_list = Hospital.query.order_by(Hospital.name).all()
        plans_list = Plan.query.order_by(Plan.plan_id).all()
        users_list = User.query.order_by(User.user_id).all()

        return render_template(
            "admin_reference_data.html",
            active_tab=active_tab,
            hospitals=hospitals_list,
            plans=plans_list,
            users=users_list,
            hospital_form=hospital_form,
            plan_form=plan_form,
            user_form=user_form
        )

    @app.route("/reports")
    @login_required
    @require_role("admin", "claims_officer")
    def reports():
        total_claims = Claim.query.count()
        approved_count = Claim.query.filter_by(status="approved").count()
        rejected_count = Claim.query.filter_by(status="rejected").count()
        paid_count = Claim.query.filter_by(status="paid").count()

        req_sum = db.session.query(func.coalesce(func.sum(Claim.requested_amount_inr), 0)).scalar()
        elig_sum = db.session.query(func.coalesce(func.sum(Claim.eligible_amount_inr), 0)).scalar()
        paid_sum = db.session.query(func.coalesce(func.sum(Settlement.amount_inr), 0)).scalar()

        status_groups = db.session.query(Claim.status, func.count(Claim.claim_id)).group_by(Claim.status).all()
        type_groups = db.session.query(Claim.claim_type, func.count(Claim.claim_id)).group_by(Claim.claim_type).all()

        return render_template(
            "reports.html",
            total_claims=total_claims,
            approved_count=approved_count,
            rejected_count=rejected_count,
            paid_count=paid_count,
            total_requested_inr=Decimal(str(req_sum or 0)),
            total_eligible_inr=Decimal(str(elig_sum or 0)),
            total_settled_inr=Decimal(str(paid_sum or 0)),
            status_groups=dict(status_groups),
            type_groups=dict(type_groups)
        )

    @app.route("/reports/export-csv")
    @login_required
    @require_role("admin", "claims_officer")
    def export_reports_csv():
        """Export claims report dataset to CSV with formula injection defense."""
        def sanitize_csv_cell(val):
            s = str(val or "")
            if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
                return f"'{s}"
            return s

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Claim ID", "Policy ID", "Member Name", "Hospital Name",
            "Claim Type", "Treatment Type", "Admission Date", "Discharge Date",
            "Requested Amount (INR)", "Status", "Eligible Amount (INR)", "Assigned Officer"
        ])

        claims = Claim.query.order_by(Claim.claim_id.asc()).all()
        for c in claims:
            writer.writerow([
                sanitize_csv_cell(f"CLM-{c.claim_id:06d}"),
                sanitize_csv_cell(c.policy_id),
                sanitize_csv_cell(c.member.display_name if c.member else ""),
                sanitize_csv_cell(c.hospital.name if c.hospital else ""),
                sanitize_csv_cell(c.claim_type),
                sanitize_csv_cell(c.treatment_type),
                sanitize_csv_cell(c.admission_date.strftime("%Y-%m-%d") if c.admission_date else ""),
                sanitize_csv_cell(c.discharge_date.strftime("%Y-%m-%d") if c.discharge_date else ""),
                sanitize_csv_cell(str(c.requested_amount_inr)),
                sanitize_csv_cell(c.status),
                sanitize_csv_cell(str(c.eligible_amount_inr or "0.00")),
                sanitize_csv_cell(c.officer.display_name if c.officer else "Unassigned")
            ])

        response = Response(output.getvalue(), mimetype="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=Canopy_Claims_Report.csv"
        return response

    # --- CLI Commands ---
    @app.cli.command("init-db")
    def init_db():
        """Initialize MySQL database schema from SQLAlchemy models."""
        db.create_all()
        print("Database schema successfully created from models.")

    @app.cli.command("set-password")
    def set_password_command():
        """Securely set a user's password using Werkzeug."""
        username = input("Enter username to update password: ").strip()
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"User '{username}' not found.")
            return
        pwd = getpass.getpass(f"Enter new password for '{username}': ")
        confirm_pwd = getpass.getpass("Confirm new password: ")
        if pwd != confirm_pwd:
            print("Passwords did not match.")
            return
        user.set_password(pwd)
        db.session.commit()
        print(f"Password for user '{username}' successfully updated.")

    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        try:
            db.create_all()
        except Exception as db_err:
            print(f"[DB] Notice: {db_err}")
            sqlite_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "health_claims.db")
            app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_db_path}"
            db.engine.dispose()
            db.create_all()

        try:
            if Hospital.query.count() == 0:
                print("[DB] Initializing database with seed records...")
                if __package__:
                    from .seed_db import seed_database
                else:
                    from seed_db import seed_database
                seed_database(reset_existing=False)
        except Exception as seed_err:
            print(f"[DB] Auto-seed status: {seed_err}")

    print("\n" + "=" * 65)
    print("  Canopy Health Insurance Claims Processing Simulator")
    print("  Server running at: http://127.0.0.1:5000")
    print("  Demo Logins (Password: Password123!):")
    print("    - Policyholder: aasha")
    print("    - Hospital Desk: city_hospital")
    print("    - Claims Officer: officer_meera")
    print("    - Administrator: admin_demo")
    print("=" * 65 + "\n")

    app.run(host="0.0.0.0", port=5000, debug=True)
