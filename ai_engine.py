"""
ai_engine.py
------------
A lightweight, fully-free "agentic" pipeline that:
  1. Extracts text from uploaded resumes (PDF / DOCX / TXT)
  2. Extracts keywords/skills from both the Job Description (JD) and the resume
  3. Compares them using TF-IDF + Cosine Similarity (scikit-learn) -> a 0-100 score
  4. Ranks all resumes uploaded for a job
  5. Auto-generates 10 HR interview questions per shortlisted candidate,
     based on the skills/keywords actually found in their resume + the JD.

No paid APIs (OpenAI, etc.) are used anywhere — everything runs locally,
which keeps the project at zero cost as required.
"""

import os
import re
import string
import random
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    import PyPDF2  # preferred (listed in requirements.txt)
except ImportError:
    import pypdf as PyPDF2  # fallback: modern fork has a compatible PdfReader API

import docx

# ---------------------------------------------------------------------------
# 1. TEXT EXTRACTION
# ---------------------------------------------------------------------------

def extract_text(filepath: str) -> str:
    """Extracts raw text from a resume file (.pdf, .docx, .txt)."""
    ext = filepath.rsplit(".", 1)[-1].lower()
    text = ""
    try:
        if ext == "pdf":
            with open(filepath, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += (page.extract_text() or "") + "\n"
        elif ext == "docx":
            d = docx.Document(filepath)
            text = "\n".join(p.text for p in d.paragraphs)
        elif ext == "txt":
            with open(filepath, "r", errors="ignore") as f:
                text = f.read()
    except Exception as e:
        text = ""
    return text.strip()


def guess_candidate_name(text: str, fallback: str) -> str:
    """Very simple heuristic: first non-empty line that looks like a name."""
    for line in text.split("\n")[:5]:
        line = line.strip()
        if 2 <= len(line.split()) <= 4 and not any(ch.isdigit() for ch in line) and "@" not in line:
            return line.title()
    return fallback


# ---------------------------------------------------------------------------
# 2. SKILL / KEYWORD EXTRACTION
# ---------------------------------------------------------------------------

# A small free curated tech/HR skill dictionary. Extend freely.
SKILL_BANK = [
    "python", "java", "c++", "c#", "javascript", "typescript", "react", "angular",
    "vue", "node.js", "django", "flask", "fastapi", "sql", "mysql", "postgresql",
    "mongodb", "aws", "azure", "gcp", "docker", "kubernetes", "git", "github",
    "machine learning", "deep learning", "nlp", "data analysis", "data science",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "excel", "power bi",
    "tableau", "communication", "leadership", "project management", "agile", "scrum",
    "html", "css", "rest api", "graphql", "linux", "ci/cd", "testing", "selenium",
    "spring boot", "android", "ios", "swift", "kotlin", "php", "laravel", "redis",
    "elasticsearch", "hadoop", "spark", "etl", "tableau", "salesforce", "sap",
    "customer service", "recruitment", "negotiation", "marketing", "seo", "content writing",
]

STOPWORDS = set("""a an the and or of to in for on with at by is are was were be been
being this that these those as it its from into over under out up down so but if then
than will would can could should we you they he she i our your their""".split())


def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9+#. ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_keywords(text: str, top_n: int = 25) -> list:
    """Combines a curated-skill match with frequency-based keyword extraction."""
    cleaned = clean_text(text)

    # a) curated skill matches (exact phrase match against SKILL_BANK)
    found_skills = {skill for skill in SKILL_BANK if skill in cleaned}

    # b) frequency-based extra keywords (nouns-ish, longer than 3 chars, not stopwords)
    tokens = [w for w in cleaned.split() if len(w) > 3 and w not in STOPWORDS]
    freq = Counter(tokens)
    frequent_words = [w for w, _ in freq.most_common(top_n) if w not in found_skills]

    keywords = list(found_skills) + frequent_words
    return keywords[:top_n]


# ---------------------------------------------------------------------------
# 3. JD <-> RESUME SCORING  (TF-IDF + Cosine Similarity)
# ---------------------------------------------------------------------------

def score_resume_against_jd(jd_text: str, resume_text: str) -> dict:
    """
    Returns a dict: {score: 0-100 float, matched_keywords: [...]}
    Uses TF-IDF vectorization + cosine similarity — a classic, free, explainable
    NLP technique (no external API / no GPU needed).
    """
    jd_clean = clean_text(jd_text)
    resume_clean = clean_text(resume_text)

    if not jd_clean or not resume_clean:
        return {"score": 0.0, "matched_keywords": []}

    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        tfidf_matrix = vectorizer.fit_transform([jd_clean, resume_clean])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    except ValueError:
        similarity = 0.0

    score = round(float(similarity) * 100, 2)

    jd_keywords = set(extract_keywords(jd_text, top_n=40))
    resume_keywords = set(extract_keywords(resume_text, top_n=60))
    matched = sorted(jd_keywords & resume_keywords)

    # Small boost: more overlapping curated/explicit keywords -> nudge score up,
    # capped at 100, to reward exact skill matches beyond pure vector similarity.
    if jd_keywords:
        overlap_ratio = len(matched) / max(len(jd_keywords), 1)
        score = min(100.0, round(score * 0.7 + overlap_ratio * 100 * 0.3, 2))

    return {"score": score, "matched_keywords": matched}


def rank_resumes(resume_score_pairs: list) -> list:
    """resume_score_pairs: list of (resume_obj, score). Returns sorted with rank assigned."""
    sorted_pairs = sorted(resume_score_pairs, key=lambda x: x[1], reverse=True)
    for i, (resume, _) in enumerate(sorted_pairs, start=1):
        resume.rank = i
    return sorted_pairs


# ---------------------------------------------------------------------------
# 4. AUTOMATIC INTERVIEW QUESTION GENERATION (rule/template based — free)
# ---------------------------------------------------------------------------

QUESTION_TEMPLATES = [
    "Can you walk me through a project where you used {skill}?",
    "How would you rate your proficiency in {skill}, and how did you gain that experience?",
    "Describe a challenging problem you solved using {skill}.",
    "What best practices do you follow when working with {skill}?",
    "Tell me about a time {skill} didn't work as expected — how did you debug it?",
    "How do you stay updated with new developments in {skill}?",
    "How would you explain {skill} to someone with no technical background?",
    "What tools or libraries do you typically pair with {skill}?",
    "Give an example of how {skill} contributed to a measurable business outcome.",
    "What are the limitations of {skill}, and how do you work around them?",
]

GENERIC_QUESTIONS = [
    "Walk me through your resume and your overall career journey so far.",
    "Why are you interested in this particular role and our organization?",
    "Describe a time you had to work under a tight deadline. How did you manage it?",
    "Tell me about a conflict you had with a teammate and how you resolved it.",
    "Where do you see yourself professionally in the next 3-5 years?",
]


def generate_interview_questions(matched_keywords: list, jd_text: str, num_questions: int = 10) -> list:
    """
    Generates up to `num_questions` interview questions tailored to the
    candidate's matched skills (from resume <-> JD overlap) plus a couple
    of generic behavioural questions, mimicking what an HR agent would ask.
    """
    questions = []
    skills = matched_keywords[:] if matched_keywords else extract_keywords(jd_text, top_n=10)
    random.shuffle(skills)

    skill_question_count = max(0, num_questions - 2)  # leave room for 2 generic Qs
    used_templates = set()

    i = 0
    while len(questions) < skill_question_count and skills:
        skill = skills[i % len(skills)]
        template = random.choice(QUESTION_TEMPLATES)
        key = (skill, template)
        if key not in used_templates:
            questions.append(template.format(skill=skill))
            used_templates.add(key)
        i += 1
        if i > 100:  # safety break
            break

    # Fill remaining with generic behavioural questions
    remaining = num_questions - len(questions)
    questions.extend(GENERIC_QUESTIONS[:remaining])

    return questions[:num_questions]


# ---------------------------------------------------------------------------
# 5. ORCHESTRATOR — the "agent" that runs the full pipeline for one resume
# ---------------------------------------------------------------------------

def process_resume(filepath: str, jd_text: str, fallback_name: str) -> dict:
    """Runs the full agentic pipeline for a single uploaded resume file."""
    text = extract_text(filepath)
    candidate_name = guess_candidate_name(text, fallback_name)
    result = score_resume_against_jd(jd_text, text)
    questions = generate_interview_questions(result["matched_keywords"], jd_text)

    return {
        "candidate_name": candidate_name,
        "raw_text": text,
        "score": result["score"],
        "matched_keywords": ", ".join(result["matched_keywords"]),
        "interview_questions": "\n".join(questions),
    }
