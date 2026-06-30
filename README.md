# AcuRecruit — AI Resume Screening System (Admin + Recruiter), Free & Open-Source

A Flask-based prototype for HR resume screening, named **AcuRecruit**, with
two modules, **Admin** and **Recruiter**, plus a local, **fully free
"agentic" AI pipeline** (no paid APIs, no OpenAI key needed) that scores,
ranks, and generates interview questions
from resumes.

## Tech stack (100% free / open source)
- **Flask** — web framework
- **SQLite + SQLAlchemy** — database (zero setup, file-based)
- **Flask-Login** — authentication/session handling
- **scikit-learn** (TF‑IDF + Cosine Similarity) — resume ⟷ job description matching
- **PyPDF2 / python-docx** — resume text extraction (PDF/DOCX/TXT)
- Rule/template-based question generator — no GPU, no internet call required

## Features

### Admin module
1. Add recruiters (HR) with name/email/password
2. Remove recruiters (cascades — deletes their jobs & resumes)
3. Enable/Disable a recruiter account (soft block, no deletion)
4. Global dashboard — counts of recruiters, jobs, resumes screened

### Recruiter module (the core)
1. Create a Job Description (JD) before uploading resumes
2. **Bulk upload resumes** (multi-file PDF/DOCX/TXT)
3. **Agentic AI pipeline runs automatically on upload**:
   - Extracts resume text
   - Extracts skills/keywords from both JD and resume
   - Computes a **0–100 match score** (TF-IDF + cosine similarity, boosted by
     keyword overlap ratio)
   - **Ranks** all resumes for that job, best first
   - **Auto-generates 10 tailored HR interview questions** per candidate,
     based on the skills found in their resume that match the JD
4. Recruiter can **Shortlist / Reject** each candidate
5. View a candidate detail page: score, matched keywords, resume text preview,
   and the full interview question list

## How the "AI agent" works (ai_engine.py)
This avoids any paid LLM API so the project costs $0 to run:
1. **Extraction** — pulls raw text out of PDF/DOCX/TXT resumes
2. **Keyword extraction** — combines a curated tech/HR skill dictionary with
   frequency-based keyword mining
3. **Scoring** — TF-IDF vectorizes the JD and resume text, then computes
   cosine similarity; this is blended with the keyword-overlap ratio for a
   final, explainable 0–100 score
4. **Ranking** — sorts all resumes per job by score
5. **Question generation** — picks the matched skills and slots them into a
   bank of interview-question templates ("Tell me about a project where you
   used {skill}..."), plus 2 standard behavioural questions, producing 10
   total questions per candidate

> Optional upgrade path (still free): you can later swap in Hugging Face's
> free Inference API or a small local model (e.g. via `transformers` /
> `sentence-transformers`) for embeddings-based matching or LLM-generated
> questions — the `ai_engine.py` module is isolated so this is a drop-in
> replacement without touching the Flask routes.

## Quick Start (hackathon — one command)

**Mac/Linux:**
```bash
./run.sh
```

**Windows:**
```bash
run.bat
```

This single command will: create a virtual environment, install all
dependencies, **seed a demo recruiter + job + 3 sample resumes already
scored and ranked**, then start the server. Open
**http://127.0.0.1:5000**, log in, and you'll have a fully populated demo
ready for judges immediately — no manual clicking needed beforehand.

- Admin login: `admin@example.com` / `admin123`
- Recruiter login (pre-seeded): `recruiter@example.com` / `recruiter123`
  → open the job **"Python Developer (Demo)"** to see 3 ranked candidates
  with AI-generated interview questions already waiting.

## Manual Setup (step by step)

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies (all free, from PyPI)
pip install -r requirements.txt

# 3. (Optional) Seed demo data for instant presentation
python seed_demo.py

# 4. Run the app (auto-creates SQLite DB + default admin on first run)
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

**Default admin login** (created automatically on first run):
- Email: `admin@example.com`
- Password: `admin123`

> Change the `SECRET_KEY` in `app.py` and the default admin password before
> any real/shared deployment.

## ⚠️ Important — test this BEFORE your hackathon slot
This was built and syntax-validated in a sandboxed environment without
internet access, so the `pip install` step could not be fully executed
end-to-end here. The Flask routes, models, and the AI scoring/ranking/
question-generation engine (`ai_engine.py`) were tested in isolation and
work correctly. **Run `./run.sh` (or the manual setup) once on your own
machine ahead of time** to confirm everything installs cleanly in your
environment, and fix any environment-specific issues (Python version,
OS-specific build tools for scikit-learn, etc.) before you're on stage.

## Typical flow to demo the project
**Fastest way:** run `./run.sh` (or `run.bat`) — it seeds everything for you.
Then log in as the demo recruiter and open the pre-loaded job.

**Manual way (to show judges the live AI pipeline in action):**
1. Log in as Admin → add a Recruiter account.
2. Log out → log in as that Recruiter.
3. Create a Job Description (paste a real JD, e.g. "Python Developer").
4. Bulk-upload the 3 files in `sample_resumes/` (or your own PDF/DOCX/TXT).
5. Watch the AI auto-score and rank them live.
6. Click a candidate → see matched keywords + the 10 generated interview
   questions.
7. Shortlist/reject candidates as needed.

## Project structure
```
resume_screening/
├── app.py            # Flask routes (Admin + Recruiter modules, auth)
├── models.py          # SQLAlchemy models: User, Job, Resume
├── ai_engine.py        # The free "agentic AI" pipeline (parsing/scoring/ranking/questions)
├── requirements.txt
├── templates/          # Jinja2 HTML templates
├── static/style.css
└── uploads/             # Uploaded resumes (auto-created, per job_id folder)
```

## Notes / next steps for a production version
- Add file-size/type validation hardening, virus scanning for uploads
- Move SECRET_KEY / DB URI to environment variables
- Add pagination for large resume batches
- Replace TF-IDF with free sentence-embedding models for deeper semantic
  matching if exact-keyword matching isn't precise enough
- Add email notifications to shortlisted candidates (e.g. free SMTP)
