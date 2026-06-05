"""
Student Portal - Flask Application
Main entry point: routes, database setup, and file handling.
MySQL edition — uses mysql-connector-python.

Install dependency:
    pip install mysql-connector-python

Set the following environment variables (or edit the MY_SQL_CONFIG dict below):
    DB_HOST     (default: localhost)
    DB_PORT     (default: 3306)
    DB_USER     (default: root)
    DB_PASSWORD (default: "")
    DB_NAME     (default: student_portal)
"""

import os
import mysql.connector
from mysql.connector import errorcode
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request,
    redirect, url_for, jsonify, flash
)
from werkzeug.utils import secure_filename

from dotenv import load_dotenv
load_dotenv()  # ← make sure this line exists and is BEFORE the MYSQL_CONFIG dict

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = "studentportal_secret_2024"

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "images", "uploads")
ALLOWED_EXTS  = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024   # 5 MB limit

# ---------------------------------------------------------------------------
# MySQL connection config  — override via environment variables
# ---------------------------------------------------------------------------
MYSQL_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "student_portal"),
}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    """
    Open and return a MySQL connection.
    dictionary=True gives dict-like rows (equivalent to sqlite3.Row).
    """
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    return conn


def init_db():
    """
    Create the database (if it does not exist) and the students table.
    Called once at startup.
    """
    # Connect without selecting a database first so we can CREATE it
    cfg_no_db = {k: v for k, v in MYSQL_CONFIG.items() if k != "database"}
    conn = mysql.connector.connect(**cfg_no_db)
    cursor = conn.cursor(dictionary=True)

    db_name = MYSQL_CONFIG["database"]
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cursor.execute(f"USE `{db_name}`")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id               INT            NOT NULL AUTO_INCREMENT,
            first_name       VARCHAR(100)   NOT NULL,
            last_name        VARCHAR(100)   NOT NULL,
            email            VARCHAR(255)   NOT NULL UNIQUE,
            phone            VARCHAR(30)    NOT NULL,
            date_of_birth    DATE           NOT NULL,
            gender           VARCHAR(20)    NOT NULL,
            address          TEXT           NOT NULL,
            country          VARCHAR(100)   NOT NULL,
            programme        VARCHAR(150)   NOT NULL,
            level            VARCHAR(30)    NOT NULL,
            year_of_entry    YEAR           NOT NULL,
            gpa              DECIMAL(4, 2)  NOT NULL,
            admission_status VARCHAR(30)    NOT NULL DEFAULT 'Pending',
            photo            VARCHAR(300)   NOT NULL DEFAULT 'default.png',
            created_at       TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB
    """)

    conn.commit()
    cursor.close()
    conn.close()


def allowed_file(filename):
    """Check that the uploaded file has an allowed extension."""
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTS


# ---------------------------------------------------------------------------
# Data for dynamic select boxes (returned as JSON)
# ---------------------------------------------------------------------------

PROGRAMMES = [
    "Computer Science", "Electrical Engineering", "Mechanical Engineering",
    "Civil Engineering", "Business Administration", "Accounting",
    "Medicine & Surgery", "Nursing", "Law", "Architecture",
    "Agricultural Science", "Economics", "Mathematics", "Physics",
    "Chemistry", "Psychology", "Sociology", "Education",
]

COUNTRIES = [
    "Ghana", "Nigeria", "Kenya", "South Africa", "Ethiopia",
    "Tanzania", "Uganda", "Cameroon", "Senegal", "Côte d'Ivoire",
    "United States", "United Kingdom", "Canada", "Germany", "France",
    "China", "India", "Brazil", "Australia", "Japan",
]

LEVELS = ["100", "200", "300", "400", "Postgraduate"]

ENTRY_YEARS = list(range(2020, 2027))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Landing page."""
    return render_template("index.html")


@app.route("/form")
def form():
    """Portal form page."""
    return render_template("form.html")


@app.route("/students")
def students():
    """Students index – lists every student from the database."""
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, first_name, last_name, email, programme, level, admission_status "
        "FROM students ORDER BY created_at DESC"
    )
    all_students = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("students.html", students=all_students)


@app.route("/student/<int:student_id>")
def student_detail(student_id):
    """Details page for a single student."""
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()
    cursor.close()
    conn.close()

    if student is None:
        flash("Student not found.", "error")
        return redirect(url_for("students"))
    return render_template("detail.html", student=student)


# ---------------------------------------------------------------------------
# Form submission
# ---------------------------------------------------------------------------

@app.route("/submit", methods=["POST"])
def submit():
    """
    Handle portal form submission:
    - Validate all fields
    - Save photo to disk
    - Insert student record into DB
    - Redirect to students index on success
    """
    # --- collect text fields ---
    first_name    = request.form.get("first_name", "").strip()
    last_name     = request.form.get("last_name", "").strip()
    email         = request.form.get("email", "").strip()
    phone         = request.form.get("phone", "").strip()
    dob           = request.form.get("date_of_birth", "").strip()
    gender        = request.form.get("gender", "").strip()
    address       = request.form.get("address", "").strip()
    country       = request.form.get("country", "").strip()
    programme     = request.form.get("programme", "").strip()
    level         = request.form.get("level", "").strip()
    year_of_entry = request.form.get("year_of_entry", "").strip()
    gpa           = request.form.get("gpa", "").strip()

    # --- basic server-side validation ---
    required = [first_name, last_name, email, phone, dob, gender,
                address, country, programme, level, year_of_entry, gpa]
    if not all(required):
        flash("All fields are required. Please fill in the form completely.", "error")
        return redirect(url_for("form"))

    # --- handle photo upload ---
    photo_file = request.files.get("photo")
    if not photo_file or photo_file.filename == "":
        flash("Please upload a profile photo.", "error")
        return redirect(url_for("form"))

    if not allowed_file(photo_file.filename):
        flash("Invalid file type. Please upload a PNG, JPG, or GIF image.", "error")
        return redirect(url_for("form"))

    filename   = secure_filename(photo_file.filename)
    email_slug = email.replace("@", "_at_").replace(".", "_")
    filename   = f"{email_slug}_{filename}"
    save_path  = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    photo_file.save(save_path)

    # --- insert into database ---
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            INSERT INTO students
              (first_name, last_name, email, phone, date_of_birth,
               gender, address, country, programme, level,
               year_of_entry, gpa, photo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (first_name, last_name, email, phone, dob,
              gender, address, country, programme, level,
              int(year_of_entry), float(gpa), filename))
        conn.commit()
        cursor.close()
        conn.close()

    except mysql.connector.IntegrityError as e:
        if e.errno == errorcode.ER_DUP_ENTRY:
            flash("A student with that email address already exists.", "error")
        else:
            flash(f"Database integrity error: {e}", "error")
        return redirect(url_for("form"))

    except Exception as e:
        flash(f"An error occurred while saving: {e}", "error")
        return redirect(url_for("form"))

    return redirect(url_for("students"))


# ---------------------------------------------------------------------------
# Async status update (called from detail page via fetch)
# ---------------------------------------------------------------------------

@app.route("/update_status/<int:student_id>", methods=["POST"])
def update_status(student_id):
    """
    Asynchronously update a student's admission status.
    Expects JSON body: { "status": "Admitted" }
    Returns JSON:      { "success": true }
    """
    data       = request.get_json(silent=True) or {}
    new_status = data.get("status", "").strip()

    valid_statuses = ["Pending", "Admitted", "Rejected", "Deferred"]
    if new_status not in valid_statuses:
        return jsonify({"success": False, "message": "Invalid status value."}), 400

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "UPDATE students SET admission_status = %s WHERE id = %s",
        (new_status, student_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"success": True, "status": new_status})


# ---------------------------------------------------------------------------
# API endpoints for dynamic select population
# ---------------------------------------------------------------------------

@app.route("/api/programmes")
def api_programmes():
    return jsonify(sorted(PROGRAMMES))


@app.route("/api/countries")
def api_countries():
    return jsonify(COUNTRIES)


@app.route("/api/levels")
def api_levels():
    return jsonify(LEVELS)


@app.route("/api/entry_years")
def api_entry_years():
    return jsonify(ENTRY_YEARS)


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    init_db()
    app.run(debug=True, port=5000)
