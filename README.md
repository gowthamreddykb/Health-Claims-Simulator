# Health Insurance Claims Processing Simulator

## 1. Project Purpose and Scope
The **Health Insurance Claims Processing Simulator** is a full-stack educational web application designed for insurance workflow training and classroom simulation. It provides a multi-role operational environment for **Policyholders**, **Hospital Desks**, **Claims Officers**, and **Administrators** to track health insurance claims from inception to final simulated settlement.

> **DISCLAIMER:** This application is an educational simulation. All data, hospitals, policies, members, claims, and financial determinations are synthetic. No real patient data is stored, no real health insurance policies are issued, and no actual financial transactions or bank payouts take place.

---

## 2. Project Folder Structure
```text
health_insurance_claims/
│
├── app.py                      # Flask application factory, routes, error handlers, CLI commands
├── config.py                   # Environment configuration & MySQL connection setup
├── extensions.py               # Shared SQLAlchemy, LoginManager, and CSRF extensions
├── models.py                   # 9 SQLAlchemy ORM models with foreign keys & indexes
├── forms.py                    # Server-side validated WTForms with CSRF protection
├── services.py                 # Core workflow transitions, calculations & permission checks
├── import_csv.py               # Sequential transaction-based CSV dataset importer
├── requirements.txt            # Python dependencies
├── .env                        # Local environment variables and secrets (not committed)
├── README.md                   # Complete documentation
│
├── templates/
│   ├── base.html               # Canopy top-horizontal navbar, layout shell & footer
│   ├── login.html              # Split-pane login screen with demo accounts switcher
│   ├── dashboard.html          # Role-adaptive dashboard with 4 metric cards & distribution charts
│   ├── my_policies.html        # Policy overview, coverage details & covered members list
│   ├── hospitals.html          # Network hospital directory with city & network filters
│   ├── claim_list.html         # Canopy Claims Queue with multi-parameter search & filters
│   ├── claim_detail.html       # Claims workspace, assessment panel & audit history timeline
│   ├── claim_form.html         # Multi-step claim submission form with client & server validation
│   ├── review_queue.html       # Dedicated Claims Officer review and assignment queue
│   ├── admin_reference_data.html # Reference data tabs for hospitals, plans & user roles
│   ├── reports.html            # Aggregated analytics, status breakdown & financial totals
│   ├── 403.html                # Access Denied error screen
│   ├── 404.html                # Page Not Found error screen
│   └── 500.html                # Server Error error screen
│
├── static/
│   ├── css/
│   │   └── style.css           # Canopy mint-green and deep forest design system styles
│   │
│   └── js/
│       └── main.js             # Client enhancements, password toggle & live payout estimator
│
└── tests/
    ├── conftest.py             # In-memory test database & multi-role fixtures
    ├── test_auth.py            # Authentication, session & password security tests
    ├── test_claims.py          # Claim creation, validation & duplicate detection tests
    ├── test_permissions.py     # Row-level authorization & role guard tests
    └── test_settlements.py     # Payout formula, remaining cover & settlement tests
```

---

## 3. Technologies Used
- **Backend:** Python 3.10+, Flask 3.0, Flask-SQLAlchemy, SQLAlchemy ORM 2.0, PyMySQL, Flask-Login, Flask-WTF, WTForms, Werkzeug security.
- **Database:** MySQL 8.0+ (with SQLite in-memory fallback for unit testing).
- **Frontend:** HTML5, CSS3, JavaScript (ES6), Bootstrap 5.3, Bootstrap Icons, Google Fonts (Plus Jakarta Sans).
- **Testing:** pytest, pytest-mock.

---

## 4. Installation & Setup Instructions

### Prerequisites
- Python 3.10 or higher
- MySQL Server 8.0+ installed and running
- Git (optional)

### Step 1: Create the MySQL Database
Log in to MySQL (e.g. MySQL Command Line Client):
```sql
CREATE DATABASE health_insurance_claims CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Step 2: Configure Environment Variables (`.env`)
In the `health_insurance_claims/` directory, open or edit `.env`:
```ini
FLASK_SECRET_KEY=generate-a-strong-random-key-here
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=health_insurance_claims
```
*Security Note: Never commit `.env` containing sensitive credentials to a public git repository.*

### Step 3: Install Python Dependencies
Open Command Prompt (Windows) or Terminal (macOS/Linux) and navigate to the project directory:
```bash
python -m venv venv
```
Activate the virtual environment:
- **Windows Command Prompt:**
  ```cmd
  venv\Scripts\activate
  ```
- **Linux/macOS:**
  ```bash
  source venv/bin/activate
  ```
Install the requirements:
```bash
pip install -r requirements.txt
```

### Step 4: Initialize the Database Schema
Generate all 9 tables in MySQL using SQLAlchemy ORM:
```bash
flask --app app.py init-db
```

### Step 5: Import the Seed CSV Datasets
Import all supplied synthetic entities in strict foreign-key order:
```bash
flask --app app.py import-csv
```

### Step 6: Secure Demo Accounts Password Setup
By default, the seed importer creates demo user accounts with the password `Password123!`.
To securely change any user's password locally:
```bash
flask --app app.py set-password
```
Follow the hidden interactive terminal prompt to set a new password.

---

## 5. Demo Accounts

| Role | Username | Password | Purpose |
|---|---|---|---|
| **Policyholder** | `aasha` | `Password123!` | View policy POL-0101, covered members, submit reimbursement claims |
| **Hospital Desk** | `city_hospital` | `Password123!` | Network hospital desk for CityCare Hospital, submit cashless claims |
| **Claims Officer** | `officer_meera` | `Password123!` | Review queue, assign submitted claims, approve/reject/request info |
| **Administrator** | `admin_demo` | `Password123!` | Financial reports, manage reference data, record simulated settlements |

---

## 6. Running the Application
```bash
flask --app app.py run --port 5000 --debug
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 7. Claim Processing Workflow & State Machine

```
[Draft]  ──(Submit)──>  [Submitted]  ──(Officer Assigns)──>  [In Review]
                              ▲                                  │
                              │                                  ├──(Request Info)──> [More Info]
                              └───(Submitter Responds)───────────┤                         │
                                                                 ├──(Reject)────────> [Rejected] (Terminal)
                                                                 │
                                                                 └──(Approve)───────> [Approved]
                                                                                           │
                                                                         (Admin Settles)───▼
                                                                                       [Paid] (Terminal)
```

### Transition Permissions
1. **`draft` -> `submitted`**: Submitter only. Validates admission date is not in the future.
2. **`submitted` -> `in_review`**: Claims Officer upon self-assignment.
3. **`in_review` -> `more_info`**: Assigned Claims Officer with written note.
4. **`more_info` -> `submitted`**: Submitter responds with requested clarification.
5. **`in_review` -> `approved`**: Assigned Claims Officer with eligible amount and written reason.
6. **`in_review` -> `rejected`**: Assigned Claims Officer with written rejection reason.
7. **`approved` -> `paid`**: Administrator upon recording simulated settlement.

---

## 8. Fictional Payout Calculation Formula
For any approved claim:
$$\text{payout} = \operatorname{round}\Big((\text{eligible\_amount} - \min(\text{eligible\_amount}, \text{deductible})) \times (1 - \frac{\text{copay\_percent}}{100}), 2\Big)$$

- **Remaining Cover:** Policy annual limit minus sum of prior simulated paid payouts (`status == 'paid'`).
- **Payee Type:** `hospital` for cashless claims; `policyholder` for reimbursement claims.

---

## 9. Running Automated Tests
Run the complete test suite:
```bash
pytest
```
Run with detailed verbosity:
```bash
pytest -v
```

---

## 10. Troubleshooting
- **MySQL Access Denied:** Check `DB_USER` and `DB_PASSWORD` in `.env`. Ensure your MySQL user has `CREATE`, `SELECT`, `INSERT`, `UPDATE`, `DELETE` grants.
- **Table already exists:** Use `flask --app app.py init-db` which utilizes `db.create_all()` (safe, non-destructive).
- **Import Duplicate Detected:** `import_csv.py` detects if seed data is already present and safely skips to prevent duplication.
