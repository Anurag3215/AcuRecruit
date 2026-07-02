"""
AcuRecruit — AI-powered Resume Screening & Recruiter Platform
app.py: Flask application entrypoint (Admin + Recruiter modules)
"""
import os
from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from models import db, User, Job, Resume
from ai_engine import process_resume, rank_resumes

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-change-me"  # change for production
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB total upload cap

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def admin_required(f):
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def recruiter_required(f):
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "recruiter":
            abort(403)
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard" if current_user.role == "admin" else "recruiter_dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            if not user.is_active_flag:
                flash("Your account has been disabled by the Admin. Contact support.", "danger")
                return redirect(url_for("login"))
            login_user(user)
            return redirect(url_for("index"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# ADMIN MODULE
# Feature 1: Add / Remove recruiters
# Feature 2: Enable / Disable recruiter accounts
# Feature 3: Global dashboard — view all jobs & resumes across all recruiters
# ---------------------------------------------------------------------------

@app.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    recruiters = User.query.filter_by(role="recruiter").all()
    total_jobs = Job.query.count()
    total_resumes = Resume.query.count()
    return render_template(
        "admin_dashboard.html",
        recruiters=recruiters,
        total_jobs=total_jobs,
        total_resumes=total_resumes,
    )


@app.route("/admin/recruiters/add", methods=["POST"])
@login_required
@admin_required
def add_recruiter():
    name = request.form["name"].strip()
    email = request.form["email"].strip().lower()
    password = request.form["password"]

    if User.query.filter_by(email=email).first():
        flash("A user with that email already exists.", "danger")
        return redirect(url_for("admin_dashboard"))

    recruiter = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        role="recruiter",
    )
    db.session.add(recruiter)
    db.session.commit()
    flash(f"Recruiter '{name}' added successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/recruiters/<int:user_id>/remove", methods=["POST"])
@login_required
@admin_required
def remove_recruiter(user_id):
    recruiter = User.query.get_or_404(user_id)
    if recruiter.role != "recruiter":
        abort(400)
    db.session.delete(recruiter)
    db.session.commit()
    flash("Recruiter removed.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/recruiters/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_recruiter(user_id):
    recruiter = User.query.get_or_404(user_id)
    if recruiter.role != "recruiter":
        abort(400)
    recruiter.is_active_flag = not recruiter.is_active_flag
    db.session.commit()
    flash(f"Recruiter {'enabled' if recruiter.is_active_flag else 'disabled'}.", "success")
    return redirect(url_for("admin_dashboard"))


# ---------------------------------------------------------------------------
# RECRUITER MODULE
# Feature 1: Create job description
# Feature 2: Bulk upload resumes -> AI scoring, ranking
# Feature 3: View shortlist + auto-generated interview questions
# Feature 4: Shortlist / Reject candidates
# ---------------------------------------------------------------------------

@app.route("/recruiter/dashboard")
@login_required
@recruiter_required
def recruiter_dashboard():
    jobs = Job.query.filter_by(recruiter_id=current_user.id).order_by(Job.created_at.desc()).all()
    return render_template("recruiter_dashboard.html", jobs=jobs)


@app.route("/recruiter/jobs/create", methods=["GET", "POST"])
@login_required
@recruiter_required
def create_job():
    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        required_skills = request.form.get("required_skills", "").strip()

        job = Job(
            title=title,
            description=description,
            required_skills=required_skills,
            recruiter_id=current_user.id,
        )
        db.session.add(job)
        db.session.commit()
        flash("Job description created. Now upload resumes for it.", "success")
        return redirect(url_for("job_detail", job_id=job.id))
    return render_template("create_job.html")


@app.route("/recruiter/jobs/<int:job_id>")
@login_required
@recruiter_required
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    if job.recruiter_id != current_user.id:
        abort(403)
    resumes = Resume.query.filter_by(job_id=job.id).order_by(Resume.rank.asc().nullslast()).all()
    return render_template("job_detail.html", job=job, resumes=resumes)


@app.route("/recruiter/jobs/<int:job_id>/upload", methods=["POST"])
@login_required
@recruiter_required
def upload_resumes(job_id):
    job = Job.query.get_or_404(job_id)
    if job.recruiter_id != current_user.id:
        abort(403)

    files = request.files.getlist("resumes")
    if not files or files[0].filename == "":
        flash("Please select at least one resume file.", "danger")
        return redirect(url_for("job_detail", job_id=job.id))

    job_upload_dir = os.path.join(app.config["UPLOAD_FOLDER"], str(job.id))
    os.makedirs(job_upload_dir, exist_ok=True)

    new_resumes = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(job_upload_dir, filename)
            file.save(filepath)

            # --- AGENTIC AI PIPELINE RUNS HERE ---
            ai_result = process_resume(filepath, job.description, fallback_name=filename)

            resume = Resume(
                job_id=job.id,
                filename=filename,
                candidate_name=ai_result["candidate_name"],
                raw_text=ai_result["raw_text"],
                matched_keywords=ai_result["matched_keywords"],
                score=ai_result["score"],
                interview_questions=ai_result["interview_questions"],
                status="pending",
            )
            db.session.add(resume)
            new_resumes.append(resume)
        else:
            flash(f"Skipped unsupported file: {file.filename}", "warning")

    db.session.commit()

    # Re-rank ALL resumes for this job (existing + new) after this batch
    all_resumes = Resume.query.filter_by(job_id=job.id).all()
    pairs = [(r, r.score) for r in all_resumes]
    rank_resumes(pairs)
    db.session.commit()

    flash(f"Uploaded & screened {len(new_resumes)} resume(s) using the AI agent.", "success")
    return redirect(url_for("job_detail", job_id=job.id))


@app.route("/recruiter/resumes/<int:resume_id>/status/<string:new_status>", methods=["POST"])
@login_required
@recruiter_required
def update_resume_status(resume_id, new_status):
    resume = Resume.query.get_or_404(resume_id)
    if resume.job.recruiter_id != current_user.id:
        abort(403)
    if new_status not in ("shortlisted", "rejected", "pending"):
        abort(400)
    resume.status = new_status
    db.session.commit()
    flash("Candidate status updated.", "success")
    return redirect(url_for("job_detail", job_id=resume.job_id))


@app.route("/recruiter/resumes/<int:resume_id>")
@login_required
@recruiter_required
def resume_detail(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    if resume.job.recruiter_id != current_user.id:
        abort(403)
    return render_template("resume_detail.html", resume=resume)


# ---------------------------------------------------------------------------
# DB INIT / SEED (creates default admin on first run)
# ---------------------------------------------------------------------------

def init_db():
    os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(role="admin").first():
            admin = User(
                name="Default Admin",
                email="admin@example.com",
                password_hash=generate_password_hash("admin123"),
                role="admin",
            )
            db.session.add(admin)
            db.session.commit()
            print("Default admin created -> email: admin@example.com | password: admin123")



if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
