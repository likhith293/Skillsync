# ============================================
# parser.py - Resume PDF Parser
# ============================================
# This file extracts text and skills from
# the uploaded resume PDF
# ============================================

import pdfplumber
import re

# Master list of skills we look for
SKILL_KEYWORDS = {
    "frontend": [
        "html", "css", "javascript", "typescript", "react", "next.js", "vue",
        "angular", "tailwind", "bootstrap", "sass", "webpack", "vite",
        "redux", "graphql", "jest", "cypress", "figma"
    ],
    "backend": [
        "python", "node.js", "java", "c++", "c#", "go", "rust", "php",
        "fastapi", "django", "flask", "express", "spring", "laravel",
        "rest api", "microservices", "docker", "kubernetes", "redis",
        "postgresql", "mysql", "mongodb", "firebase"
    ],
    "data": [
        "sql", "pandas", "numpy", "tensorflow", "pytorch", "scikit-learn",
        "power bi", "tableau", "excel", "r", "matlab", "hadoop", "spark",
        "machine learning", "deep learning", "nlp", "computer vision"
    ],
    "devops": [
        "git", "github", "gitlab", "ci/cd", "jenkins", "aws", "azure",
        "gcp", "linux", "bash", "terraform", "ansible"
    ]
}


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract raw text from a PDF resume
    """
    full_text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""
    return full_text


def extract_skills(text: str) -> dict:
    """
    Find all skills mentioned in resume text
    Returns dict of found skills by category
    """
    text_lower = text.lower()
    found_skills = {
        "frontend": [],
        "backend": [],
        "data": [],
        "devops": [],
        "all": []
    }

    for category, skills in SKILL_KEYWORDS.items():
        for skill in skills:
            if skill.lower() in text_lower:
                found_skills[category].append(skill)
                if skill not in found_skills["all"]:
                    found_skills["all"].append(skill)

    return found_skills


def extract_experience(text: str) -> dict:
    """
    Extract education and work experience info
    """
    experience = {
        "education": [],
        "companies": [],
        "years_experience": 0,
        "projects_count": 0
    }

    # Look for degree mentions
    degrees = ["b.e", "b.tech", "m.tech", "mca", "bca", "b.sc", "m.sc",
               "bachelor", "master", "phd", "diploma"]
    for degree in degrees:
        if degree in text.lower():
            experience["education"].append(degree.upper())

    # Count project mentions
    project_count = len(re.findall(
        r'\bproject\b', text.lower()
    ))
    experience["projects_count"] = min(project_count, 20)

    # Look for internship/work
    work_keywords = ["internship", "intern", "developer", "engineer",
                     "analyst", "worked at", "experience at"]
    companies_found = []
    for keyword in work_keywords:
        if keyword in text.lower():
            companies_found.append(keyword)
    experience["companies"] = companies_found[:5]

    # Estimate experience level
    if len(experience["companies"]) == 0:
        experience["years_experience"] = 0
    elif len(experience["companies"]) <= 2:
        experience["years_experience"] = 1
    else:
        experience["years_experience"] = 2

    return experience


def parse_resume(file_path: str) -> dict:
    """
    Main function - parses entire resume
    Returns structured data ready for AI analysis
    """
    # Step 1: Extract raw text
    raw_text = extract_text_from_pdf(file_path)

    if not raw_text:
        return {
            "success": False,
            "error": "Could not read PDF. Make sure it is a valid PDF file.",
            "raw_text": "",
            "skills": {},
            "experience": {}
        }

    # Step 2: Extract skills
    skills = extract_skills(raw_text)

    # Step 3: Extract experience
    experience = extract_experience(raw_text)

    # Step 4: Detect red flags
    red_flags = []

    # Too many skills claimed with no projects
    if len(skills["all"]) > 15 and experience["projects_count"] < 2:
        red_flags.append(
            "Many skills listed but very few projects found. "
            "This may reduce credibility."
        )

    # Skills listed but no practical evidence
    advanced_skills = ["kubernetes", "tensorflow", "pytorch", "aws"]
    for skill in advanced_skills:
        if skill in skills["all"] and experience["projects_count"] < 3:
            red_flags.append(
                f"'{skill}' listed but limited project evidence found."
            )

    return {
        "success": True,
        "raw_text": raw_text[:3000],  # First 3000 chars for AI
        "skills": skills,
        "experience": experience,
        "red_flags": red_flags,
        "skill_count": len(skills["all"]),
        "summary": f"Found {len(skills['all'])} skills across "
                   f"{experience['projects_count']} projects"
    }
