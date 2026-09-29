from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    session,
)
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "bouesti_secret_key_for_flash_messages"

UPLOAD_FOLDER_STUDENTS = "uploads/student_projects"
UPLOAD_FOLDER_LECTURERS = "uploads/lecturer_projects"


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def allowed_file(filename):
    if filename is None:
        return False
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "pdf"


# --- AUTHENTICATION DECORATORS ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "role" not in session or session["role"] != role:
                flash("You do not have permission to access this area.", "error")
                return redirect(url_for("index"))
            return f(*args, **kwargs)

        return decorated_function  # <--- This line was returning 'decorator' before

    return decorator


# --- ROUTES ---
@app.route("/")
def index():
    conn = get_db_connection()
    projects = conn.execute(
        "SELECT * FROM projects ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    conn.close()
    return render_template("index.html", projects=projects)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        conn = get_db_connection()

        # Check if the username or matric number already exists
        existing_user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing_user:
            flash("Username or Matric Number already exists.", "error")
            conn.close()
            return redirect(request.url)

        # Hash the password and insert the new user
        hashed_password = generate_password_hash(password)
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, hashed_password, role),
        )
        conn.commit()
        conn.close()

        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['username']}!", "success")

            if user["role"] == "ADMIN":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/admin")
@login_required
@role_required("ADMIN")
def admin_dashboard():
    conn = get_db_connection()
    projects = conn.execute(
        "SELECT * FROM projects ORDER BY created_at DESC"
    ).fetchall()
    users = conn.execute("SELECT id, username, role FROM users").fetchall()
    conn.close()
    return render_template("admin_dashboard.html", projects=projects, users=users)


@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@login_required
@role_required("ADMIN")
def delete_user(user_id):
    # Prevent the admin from accidentally deleting their own account
    if user_id == session.get("user_id"):
        flash("You cannot delete your own administrator account.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    flash("User account successfully removed.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete_project/<int:project_id>", methods=["POST"])
@login_required
@role_required("ADMIN")
def delete_project(project_id):
    conn = get_db_connection()
    project = conn.execute(
        "SELECT file_path FROM projects WHERE id = ?", (project_id,)
    ).fetchone()

    if project:
        # Delete the actual PDF file from the server
        if os.path.exists(project["file_path"]):
            try:
                os.remove(project["file_path"])
            except Exception:
                pass

        # Delete the record from the database
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        flash("Project and associated file deleted successfully.", "success")
    else:
        flash("Project not found.", "error")

    conn.close()
    return redirect(url_for("admin_dashboard"))


@app.route("/student/upload", methods=["GET", "POST"])
@login_required
@role_required("STUDENT")
def student_upload():
    if request.method == "POST":
        title = request.form["title"]
        author_name = request.form["author_name"]
        matric_number = request.form["matric_number"]
        department = request.form["department"]
        supervisor = request.form["supervisor"]
        academic_session = request.form["academic_session"]
        keywords = request.form["keywords"]
        abstract = request.form["abstract"]

        file = request.files.get("pdf_file")

        if file is None or file.filename == "":
            flash("No file selected", "error")
            return redirect(request.url)

        if file and allowed_file(str(file.filename)):
            filename = secure_filename(str(file.filename))
            unique_filename = f"student_{matric_number}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER_STUDENTS, unique_filename)
            file.save(file_path)

            conn = get_db_connection()
            conn.execute(
                """
                INSERT INTO projects (title, author_name, author_type, matric_number, department, supervisor, academic_session, abstract, keywords, file_path, original_filename)
                VALUES (?, ?, 'STUDENT', ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    title,
                    author_name,
                    matric_number,
                    department,
                    supervisor,
                    academic_session,
                    abstract,
                    keywords,
                    file_path,
                    filename,
                ),
            )
            conn.commit()
            conn.close()

            flash("Student project uploaded successfully!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid file type. Only PDF is allowed.", "error")

    return render_template("student_upload.html")


@app.route("/lecturer/upload", methods=["GET", "POST"])
@login_required
@role_required("LECTURER")
def lecturer_upload():
    if request.method == "POST":
        title = request.form["title"]
        author_name = request.form["author_name"]
        department = request.form["department"]
        academic_session = request.form["academic_session"]
        keywords = request.form["keywords"]
        abstract = request.form["abstract"]

        file = request.files.get("pdf_file")

        if file is None or file.filename == "":
            flash("No file selected", "error")
            return redirect(request.url)

        if file and allowed_file(str(file.filename)):
            filename = secure_filename(str(file.filename))
            unique_filename = f"lecturer_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER_LECTURERS, unique_filename)
            file.save(file_path)

            conn = get_db_connection()
            conn.execute(
                """
                INSERT INTO projects (title, author_name, author_type, department, academic_session, abstract, keywords, file_path, original_filename)
                VALUES (?, ?, 'LECTURER', ?, ?, ?, ?, ?, ?)
            """,
                (
                    title,
                    author_name,
                    department,
                    academic_session,
                    abstract,
                    keywords,
                    file_path,
                    filename,
                ),
            )
            conn.commit()
            conn.close()

            flash("Lecturer research uploaded successfully!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid file type. Only PDF is allowed.", "error")

    return render_template("lecturer_upload.html")


@app.route("/search")
def search():
    query = request.args.get("q", "")
    projects = []

    if query:
        conn = get_db_connection()
        search_term = f"%{query}%"
        projects = conn.execute(
            """
            SELECT * FROM projects 
            WHERE title LIKE ? 
               OR author_name LIKE ? 
               OR keywords LIKE ? 
               OR abstract LIKE ? 
               OR department LIKE ?
            ORDER BY created_at DESC
        """,
            (search_term, search_term, search_term, search_term, search_term),
        ).fetchall()
        conn.close()

    return render_template("search.html", projects=projects, query=query)


@app.route("/project/<int:project_id>")
def project_details(project_id):
    conn = get_db_connection()
    project = conn.execute(
        "SELECT * FROM projects WHERE id = ?", (project_id,)
    ).fetchone()
    conn.close()

    if project is None:
        flash("Project not found.", "error")
        return redirect(url_for("index"))

    return render_template("project_details.html", project=project)


@app.route("/project/<int:project_id>/download")
@login_required
def download_project(project_id):
    conn = get_db_connection()
    project = conn.execute(
        "SELECT * FROM projects WHERE id = ?", (project_id,)
    ).fetchone()
    conn.close()

    if project is None or not os.path.exists(project["file_path"]):
        flash("File not found.", "error")
        return redirect(url_for("index"))

    return send_file(
        project["file_path"],
        as_attachment=True,
        download_name=project["original_filename"],
    )


if __name__ == "__main__":
    app.run(debug=True)
