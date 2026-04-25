"""
db_setup.py — Database Initialization & Mock Data
===================================================
Creates a local SQLite database (company.db) with 5 interrelated tables:
  1. Departments  — Company departments
  2. Employees    — Staff members (FK → Departments)
  3. Projects     — Company projects (FK → Departments, Employees)
  4. Tasks        — Individual tasks within projects (FK → Projects, Employees)
  5. Salary_History — Salary change log (FK → Employees)

Run this script once to create and populate the database:
    python db_setup.py
"""

import sqlite3
import os

DB_NAME = "company.db"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_NAME)


def create_tables(cursor: sqlite3.Cursor) -> None:
    """Create all tables with proper relationships and constraints."""

    # Enable foreign key support
    cursor.execute("PRAGMA foreign_keys = ON;")

    # ── 1. Departments ──────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Departments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL UNIQUE,
            location    TEXT    NOT NULL,
            budget      REAL    NOT NULL DEFAULT 0,
            created_date TEXT   NOT NULL DEFAULT (date('now'))
        );
    """)

    # ── 2. Employees ────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Employees (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name      TEXT    NOT NULL,
            last_name       TEXT    NOT NULL,
            email           TEXT    NOT NULL UNIQUE,
            phone           TEXT,
            position        TEXT    NOT NULL,
            hire_date       TEXT    NOT NULL,
            salary          REAL    NOT NULL,
            department_id   INTEGER NOT NULL,
            is_active       INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (department_id) REFERENCES Departments(id)
        );
    """)

    # ── 3. Projects ─────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Projects (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT    NOT NULL,
            description         TEXT,
            start_date          TEXT    NOT NULL,
            end_date            TEXT,
            budget              REAL    NOT NULL DEFAULT 0,
            status              TEXT    NOT NULL DEFAULT 'Planning'
                                CHECK(status IN ('Planning','In Progress','Completed','On Hold','Cancelled')),
            department_id       INTEGER NOT NULL,
            lead_employee_id    INTEGER,
            FOREIGN KEY (department_id)    REFERENCES Departments(id),
            FOREIGN KEY (lead_employee_id) REFERENCES Employees(id)
        );
    """)

    # ── 4. Tasks ────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Tasks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT    NOT NULL,
            description     TEXT,
            project_id      INTEGER NOT NULL,
            assigned_to     INTEGER,
            status          TEXT    NOT NULL DEFAULT 'To Do'
                            CHECK(status IN ('To Do','In Progress','Done','Blocked')),
            priority        TEXT    NOT NULL DEFAULT 'Medium'
                            CHECK(priority IN ('Low','Medium','High','Critical')),
            due_date        TEXT,
            created_date    TEXT    NOT NULL DEFAULT (date('now')),
            FOREIGN KEY (project_id)  REFERENCES Projects(id),
            FOREIGN KEY (assigned_to) REFERENCES Employees(id)
        );
    """)

    # ── 5. Salary_History ───────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Salary_History (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id     INTEGER NOT NULL,
            old_salary      REAL    NOT NULL,
            new_salary      REAL    NOT NULL,
            change_date     TEXT    NOT NULL,
            reason          TEXT,
            FOREIGN KEY (employee_id) REFERENCES Employees(id)
        );
    """)


def populate_data(cursor: sqlite3.Cursor) -> None:
    """Insert realistic mock data into all tables."""

    # ── Departments (5 rows) ────────────────────────────────────────
    departments = [
        ("Engineering",    "Building A, Floor 3",  500000.00, "2020-01-15"),
        ("Marketing",      "Building B, Floor 1",  300000.00, "2020-02-01"),
        ("Human Resources","Building A, Floor 1",  200000.00, "2020-01-15"),
        ("Finance",        "Building C, Floor 2",  250000.00, "2020-03-10"),
        ("Product",        "Building A, Floor 4",  400000.00, "2021-06-01"),
    ]
    cursor.executemany(
        "INSERT INTO Departments (name, location, budget, created_date) VALUES (?, ?, ?, ?);",
        departments,
    )

    # ── Employees (15 rows) ─────────────────────────────────────────
    employees = [
        ("Ahmed",   "Khan",     "ahmed.khan@company.com",      "+92-300-1234567", "Senior Software Engineer",  "2020-03-15", 120000, 1, 1),
        ("Sara",    "Ali",      "sara.ali@company.com",        "+92-301-2345678", "Software Engineer",         "2021-07-01", 90000,  1, 1),
        ("Usman",   "Raza",     "usman.raza@company.com",      "+92-302-3456789", "DevOps Engineer",           "2021-09-10", 95000,  1, 1),
        ("Fatima",  "Noor",     "fatima.noor@company.com",     "+92-303-4567890", "Marketing Manager",         "2020-05-20", 110000, 2, 1),
        ("Hassan",  "Sheikh",   "hassan.sheikh@company.com",   "+92-304-5678901", "Content Strategist",        "2022-01-10", 70000,  2, 1),
        ("Ayesha",  "Malik",    "ayesha.malik@company.com",    "+92-305-6789012", "HR Director",               "2020-02-01", 130000, 3, 1),
        ("Bilal",   "Ahmed",    "bilal.ahmed@company.com",     "+92-306-7890123", "HR Specialist",             "2022-04-15", 65000,  3, 1),
        ("Zain",    "Ul Haq",   "zain.ulhaq@company.com",     "+92-307-8901234", "Financial Analyst",         "2021-03-01", 85000,  4, 1),
        ("Maryam",  "Iqbal",    "maryam.iqbal@company.com",   "+92-308-9012345", "Senior Accountant",         "2020-06-15", 100000, 4, 1),
        ("Omar",    "Farooq",   "omar.farooq@company.com",    "+92-309-0123456", "Product Manager",           "2021-08-01", 115000, 5, 1),
        ("Hira",    "Tanveer",  "hira.tanveer@company.com",   "+92-310-1234567", "UX Designer",               "2022-02-01", 88000,  5, 1),
        ("Ali",     "Haider",   "ali.haider@company.com",     "+92-311-2345678", "Junior Developer",          "2023-01-10", 60000,  1, 1),
        ("Nadia",   "Butt",     "nadia.butt@company.com",     "+92-312-3456789", "Social Media Manager",      "2023-03-15", 62000,  2, 1),
        ("Tariq",   "Mehmood",  "tariq.mehmood@company.com",  "+92-313-4567890", "Data Analyst",              "2022-11-01", 78000,  1, 0),
        ("Sana",    "Javed",    "sana.javed@company.com",     "+92-314-5678901", "Product Analyst",           "2023-06-01", 72000,  5, 1),
    ]
    cursor.executemany(
        """INSERT INTO Employees
           (first_name, last_name, email, phone, position, hire_date, salary, department_id, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);""",
        employees,
    )

    # ── Projects (10 rows) ──────────────────────────────────────────
    projects = [
        ("Website Redesign",       "Complete overhaul of the corporate website",           "2024-01-15", "2024-06-30", 150000, "Completed",   1, 1),
        ("Mobile App v2",          "Second version of the customer-facing mobile app",     "2024-03-01", "2024-12-31", 280000, "In Progress", 1, 1),
        ("Brand Refresh",          "Update brand guidelines, logo, and marketing assets",  "2024-02-01", "2024-05-31", 80000,  "Completed",   2, 4),
        ("Employee Portal",        "Internal HR self-service portal for employees",        "2024-04-01", "2024-10-31", 120000, "In Progress", 3, 6),
        ("Financial Dashboard",    "Real-time financial reporting dashboard",              "2024-05-01", "2024-09-30", 95000,  "Planning",    4, 8),
        ("AI Chatbot",             "Customer support chatbot powered by LLM",              "2024-06-01", None,         200000, "In Progress", 1, 2),
        ("Social Media Campaign",  "Q3 social media growth campaign",                     "2024-07-01", "2024-09-30", 45000,  "On Hold",     2, 5),
        ("Data Pipeline",          "Automated ETL pipeline for analytics",                 "2024-03-15", "2024-08-31", 110000, "Completed",   1, 3),
        ("Compliance Audit System","Automated compliance tracking and reporting",          "2024-08-01", None,         160000, "Planning",    4, 9),
        ("UX Research Platform",   "Internal tool for collecting user research data",      "2024-04-15", "2024-11-30", 90000,  "In Progress", 5, 11),
    ]
    cursor.executemany(
        """INSERT INTO Projects
           (name, description, start_date, end_date, budget, status, department_id, lead_employee_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
        projects,
    )

    # ── Tasks (15 rows) ─────────────────────────────────────────────
    tasks = [
        ("Design homepage mockup",      "Create wireframes and high-fidelity mockups",     1,  11, "Done",        "High",     "2024-02-01", "2024-01-15"),
        ("Implement responsive layout",  "Frontend responsive CSS for all screen sizes",   1,  2,  "Done",        "High",     "2024-03-15", "2024-01-20"),
        ("Set up CI/CD pipeline",        "Configure GitHub Actions for auto-deployment",    2,  3,  "In Progress", "Critical", "2024-05-01", "2024-03-10"),
        ("API authentication module",    "Implement OAuth2 for mobile app",                2,  1,  "In Progress", "High",     "2024-06-01", "2024-03-15"),
        ("Design new logo options",      "Create 3 logo concepts for review",              3,  4,  "Done",        "Medium",   "2024-03-01", "2024-02-05"),
        ("Update brand guidelines PDF",  "Document new brand colors, fonts, and usage",    3,  5,  "Done",        "Low",      "2024-04-30", "2024-02-10"),
        ("Build leave request form",     "Self-service form for leave applications",       4,  7,  "In Progress", "Medium",   "2024-06-15", "2024-04-05"),
        ("Payslip download feature",     "Employees can download monthly payslips",        4,  6,  "To Do",       "High",     "2024-08-01", "2024-04-10"),
        ("Dashboard wireframes",         "Design mockups for the financial dashboard",     5,  8,  "To Do",       "Medium",   "2024-06-01", "2024-05-05"),
        ("Train chatbot on FAQ data",    "Fine-tune model on customer support FAQs",       6,  2,  "In Progress", "Critical", "2024-08-01", "2024-06-10"),
        ("Integrate chatbot with CRM",   "Connect chatbot responses to CRM tickets",       6,  1,  "To Do",       "High",     "2024-09-01", "2024-06-15"),
        ("Create social media calendar", "Plan posts for Q3 across all platforms",         7,  13, "Blocked",     "Medium",   "2024-07-15", "2024-07-01"),
        ("Build ETL for sales data",     "Extract and transform daily sales records",      8,  3,  "Done",        "High",     "2024-05-01", "2024-03-20"),
        ("User interview scheduling",    "Set up interviews with 20 target users",         10, 11, "In Progress", "Medium",   "2024-06-01", "2024-04-20"),
        ("Compliance report template",   "Design quarterly compliance report layout",      9,  9,  "To Do",       "Low",      "2024-09-01", "2024-08-05"),
    ]
    cursor.executemany(
        """INSERT INTO Tasks
           (title, description, project_id, assigned_to, status, priority, due_date, created_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
        tasks,
    )

    # ── Salary_History (12 rows) ────────────────────────────────────
    salary_history = [
        (1,  100000, 110000, "2021-03-15", "Annual performance review"),
        (1,  110000, 120000, "2022-03-15", "Promotion to Senior Engineer"),
        (2,  75000,  85000,  "2022-07-01", "Annual raise"),
        (2,  85000,  90000,  "2023-07-01", "Merit increase"),
        (4,  90000,  100000, "2021-05-20", "Annual raise"),
        (4,  100000, 110000, "2022-05-20", "Promotion to Manager"),
        (6,  110000, 120000, "2021-02-01", "Annual raise"),
        (6,  120000, 130000, "2022-02-01", "Promotion to Director"),
        (8,  70000,  78000,  "2022-03-01", "Annual raise"),
        (8,  78000,  85000,  "2023-03-01", "Exceptional performance bonus"),
        (10, 100000, 115000, "2022-08-01", "Promotion to Product Manager"),
        (3,  80000,  95000,  "2022-09-10", "Market adjustment + promotion"),
    ]
    cursor.executemany(
        """INSERT INTO Salary_History
           (employee_id, old_salary, new_salary, change_date, reason)
           VALUES (?, ?, ?, ?, ?);""",
        salary_history,
    )


def main():
    """Initialize the database and populate with mock data."""
    # Remove existing database to start fresh
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"🗑️  Removed existing {DB_NAME}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        create_tables(cursor)
        populate_data(cursor)
        conn.commit()
        print(f"✅ Database '{DB_NAME}' created successfully at:\n   {DB_PATH}")
        print(f"\n📊 Tables created:")

        # Print summary
        tables = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        ).fetchall()
        for (table_name,) in tables:
            count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            print(f"   • {table_name}: {count} rows")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
