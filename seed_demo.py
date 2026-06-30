"""
seed_demo.py
------------
Run this AFTER `python app.py` has been started once (so the DB exists),
or just run this script directly — it will initialize the DB itself too.

It creates:
  - 1 demo recruiter account
  - 1 demo Job Description (Python Developer)
  - Uploads the 3 sample resumes from sample_resumes/ and runs them
    through the AI scoring + ranking + question-generation pipeline

This gives you an instant, fully-populated demo for hackathon judges —
no manual clicking required before you start presenting.

Usage:
    python seed_demo.py
"""

import os
import shutil
from werkzeug.security import generate_password_hash

from app import app, init_db
from models import db, User, Job, Resume
from ai_engine import process_resume, rank_resumes

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_resumes")

DEMO_JD = """\
We are hiring a Python Developer to join our backend engineering team.

Responsibilities:
- Design and develop REST APIs using Python and Django/Flask.
- Work with relational databases (PostgreSQL/MySQL) to build efficient data models.
- Deploy and manage services on AWS using Docker and Kubernetes.
- Collaborate with cross-functional teams in an Agile/Scrum environment.
- Write clean, tested, maintainable code (pytest, CI/CD).

Requirements:
- 2+ years experience with Python, Django or Flask.
- Strong knowledge of SQL and REST API design.
- Familiarity with AWS, Docker.
- Good communication and problem-solving skills.
"""


def seed():
    with app.app_context():
        init_db()  # ensures tables + default admin exist

        # 1. Create (or reuse) a demo recruiter
        recruiter = User.query.filter_by(email="recruiter@example.com").first()
        if not recruiter:
            recruiter = User(
                name="Demo Recruiter",
                email="recruiter@example.com",
                password_hash=generate_password_hash("recruiter123"),
                role="recruiter",
            )
            db.session.add(recruiter)
            db.session.commit()
            print("Created demo recruiter -> recruiter@example.com / recruiter123")
        else:
            print("Demo recruiter already exists -> recruiter@example.com / recruiter123")

        # 2. Create (or reuse) a demo job
        job = Job.query.filter_by(title="Python Developer (Demo)").first()
        if not job:
            job = Job(
                title="Python Developer (Demo)",
                description=DEMO_JD,
                required_skills="python, django, flask, sql, aws, docker",
                recruiter_id=recruiter.id,
            )
            db.session.add(job)
            db.session.commit()
            print(f"Created demo job -> '{job.title}' (id={job.id})")
        else:
            print(f"Demo job already exists -> '{job.title}' (id={job.id})")

        if Resume.query.filter_by(job_id=job.id).count() > 0:
            print("Resumes already seeded for this job. Skipping upload step.")
            print("\nDemo is ready. Login as recruiter and open the job to view results.")
            return

        # 3. Copy + process each sample resume through the real AI pipeline
        job_upload_dir = os.path.join(app.config["UPLOAD_FOLDER"], str(job.id))
        os.makedirs(job_upload_dir, exist_ok=True)

        sample_files = [f for f in os.listdir(SAMPLE_DIR) if f.endswith((".txt", ".pdf", ".docx"))]
        if not sample_files:
            print("No sample resumes found in sample_resumes/. Skipping.")
            return

        for filename in sample_files:
            src = os.path.join(SAMPLE_DIR, filename)
            dst = os.path.join(job_upload_dir, filename)
            shutil.copy(src, dst)

            ai_result = process_resume(dst, job.description, fallback_name=filename)
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
            print(f"Processed: {filename} -> score will be computed after ranking")

        db.session.commit()

        # 4. Rank all resumes for this job
        all_resumes = Resume.query.filter_by(job_id=job.id).all()
        pairs = [(r, r.score) for r in all_resumes]
        rank_resumes(pairs)
        db.session.commit()

        print("\n--- Demo seeded successfully! ---")
        for r in sorted(all_resumes, key=lambda x: x.rank):
            print(f"  #{r.rank}  {r.candidate_name:<20} score={r.score}%")

        print("\nNow run:  python app.py")
        print("Login as Admin   -> admin@example.com / admin123")
        print("Login as Recruiter -> recruiter@example.com / recruiter123")
        print(f"Open the job '{job.title}' to see ranked candidates + AI interview questions.")


if __name__ == "__main__":
    seed()
