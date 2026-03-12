# ============================================
# main.py - ResumeMind Backend Server
# ============================================
# Run this with: python main.py
# Server starts at: http://localhost:8000
# API docs at: http://localhost:8000/docs
# ============================================

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import shutil
import os
import json
import uuid
from datetime import datetime

from parser import parse_resume
from company_intel import get_company_intelligence
from ai_engine import generate_quiz, evaluate_answers, get_gap_analysis

# ============================================
# App Setup
# ============================================
app = FastAPI(
    title="ResumeMind API",
    description="AI-powered career readiness assessment",
    version="1.0.0"
)

# Allow React frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temp folder for uploaded resumes
os.makedirs("temp_resumes", exist_ok=True)

# Simple JSON database for storing results
RESULTS_FILE = "results_db.json"


def load_results():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_results(data):
    with open(RESULTS_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ============================================
# Request/Response Models
# ============================================
class QuizRequest(BaseModel):
    session_id: str
    company: str
    role: str


class AnswerItem(BaseModel):
    question_id: int
    skill: str
    difficulty: str
    question: str
    answer: str
    why_answer: str
    expected_keywords: Optional[List[str]] = []


class EvaluateRequest(BaseModel):
    session_id: str
    company: str
    role: str
    answers: List[AnswerItem]


# ============================================
# API Routes
# ============================================

@app.get("/")
def root():
    return {
        "message": "ResumeMind API is running!",
        "version": "1.0.0",
        "endpoints": [
            "POST /upload-resume",
            "POST /generate-quiz",
            "POST /evaluate",
            "GET /results/{session_id}",
            "GET /progress/{email}"
        ]
    }


@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    company: str = "",
    role: str = ""
):
    """
    Step 1: Upload and parse resume PDF
    Returns extracted skills and session ID
    """

    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted"
        )

    # Save file temporarily
    session_id = str(uuid.uuid4())[:8]
    file_path = f"temp_resumes/{session_id}.pdf"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Parse the resume
    resume_data = parse_resume(file_path)

    if not resume_data["success"]:
        os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail=resume_data["error"]
        )

    # Get company intelligence if provided
    company_intel = {}
    if company and role:
        company_intel = get_company_intelligence(company, role)

    # Get quick gap analysis
    gap_analysis = {}
    if company_intel.get("role_specific_stack"):
        gap_analysis = get_gap_analysis(
            resume_skills=resume_data["skills"]["all"],
            company_stack=company_intel["role_specific_stack"],
            role=role
        )

    # Store session data
    results_db = load_results()
    results_db[session_id] = {
        "created_at": datetime.now().isoformat(),
        "resume_data": resume_data,
        "company": company,
        "role": role,
        "company_intel": company_intel,
        "gap_analysis": gap_analysis,
        "quiz_attempts": []
    }
    save_results(results_db)

    # Clean up temp file
    os.remove(file_path)

    return {
        "success": True,
        "session_id": session_id,
        "skills_found": resume_data["skills"]["all"],
        "skill_count": resume_data["skill_count"],
        "red_flags": resume_data["red_flags"],
        "company_stack": company_intel.get("role_specific_stack", []),
        "gap_analysis": gap_analysis,
        "summary": resume_data["summary"]
    }


@app.post("/generate-quiz")
async def generate_quiz_endpoint(request: QuizRequest):
    """
    Step 2: Generate custom quiz questions
    Based on company's tech stack
    """

    # Load session
    results_db = load_results()
    session = results_db.get(request.session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please upload resume first."
        )

    # Get company intel
    company_intel = get_company_intelligence(
        request.company,
        request.role
    )

    company_stack = company_intel.get(
        "role_specific_stack",
        company_intel.get("stack", [])
    )

    resume_skills = session["resume_data"]["skills"]["all"]

    # Generate quiz using AI
    quiz_data = generate_quiz(
        company=request.company,
        role=request.role,
        company_stack=company_stack,
        resume_skills=resume_skills
    )

    # Save quiz to session
    results_db[request.session_id]["current_quiz"] = quiz_data
    results_db[request.session_id]["company_stack"] = company_stack
    save_results(results_db)

    return {
        "success": True,
        "session_id": request.session_id,
        "company": request.company,
        "role": request.role,
        "company_stack": company_stack,
        "questions": quiz_data["questions"],
        "total_questions": len(quiz_data["questions"])
    }


@app.post("/evaluate")
async def evaluate_endpoint(request: EvaluateRequest):
    """
    Step 3: Evaluate all answers
    Returns score, verdict, and learning roadmap
    """

    # Load session
    results_db = load_results()
    session = results_db.get(request.session_id)

    company_stack = []
    if session:
        company_stack = session.get("company_stack", [])

    # Convert answers to dict format
    answers_list = [
        {
            "skill": a.skill,
            "difficulty": a.difficulty,
            "question": a.question,
            "answer": a.answer,
            "why_answer": a.why_answer,
            "expected_keywords": a.expected_keywords
        }
        for a in request.answers
    ]

    # Evaluate using AI
    evaluation = evaluate_answers(
        company=request.company,
        role=request.role,
        answers=answers_list,
        company_stack=company_stack
    )

    # Save attempt to history
    if session:
        attempt = {
            "attempt_number": len(
                session.get("quiz_attempts", [])
            ) + 1,
            "timestamp": datetime.now().isoformat(),
            "score": evaluation["overall_score"],
            "eligible": evaluation["eligible"],
            "company": request.company,
            "role": request.role
        }
        results_db[request.session_id]["quiz_attempts"].append(attempt)
        results_db[request.session_id]["latest_result"] = evaluation
        save_results(results_db)

    return {
        "success": True,
        "session_id": request.session_id,
        "company": request.company,
        "role": request.role,
        "result": evaluation
    }


@app.get("/results/{session_id}")
def get_results(session_id: str):
    """
    Get full results for a session including
    attempt history and progress
    """
    results_db = load_results()
    session = results_db.get(session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    attempts = session.get("quiz_attempts", [])
    progress = None

    if len(attempts) >= 2:
        first_score = attempts[0]["score"]
        latest_score = attempts[-1]["score"]
        progress = {
            "improved": latest_score > first_score,
            "points_gained": latest_score - first_score,
            "attempts_count": len(attempts),
            "scores_history": [a["score"] for a in attempts]
        }

    return {
        "session_id": session_id,
        "skills_found": session["resume_data"]["skills"]["all"],
        "company": session.get("company"),
        "role": session.get("role"),
        "latest_result": session.get("latest_result"),
        "attempts": attempts,
        "progress": progress
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "ResumeMind is running"}


# ============================================
# Run Server
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("  ResumeMind Backend Starting...")
    print("=" * 50)
    print("  API: http://localhost:8000")
    print("  Docs: http://localhost:8000/docs")
    print("=" * 50)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
