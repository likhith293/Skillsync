# ============================================
# company_intel.py - Company Intelligence
# ============================================
# Fetches real tech stack data for companies
# using GitHub API and job posting APIs
# ============================================

import requests
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "jsearch.p.rapidapi.com")

# Fallback data if APIs fail
# Based on known company tech stacks
COMPANY_STACKS = {
    "flipkart": {
        "stack": ["React", "TypeScript", "Node.js", "Java", "Kafka",
                  "Redis", "MySQL", "Docker", "Kubernetes"],
        "frontend": ["React", "TypeScript", "GraphQL", "Jest"],
        "backend": ["Java", "Node.js", "Spring Boot", "Kafka"],
        "source": "fallback"
    },
    "swiggy": {
        "stack": ["React", "React Native", "Go", "Python", "Redis",
                  "PostgreSQL", "Kafka", "Docker"],
        "frontend": ["React", "TypeScript", "Redux", "React Native"],
        "backend": ["Go", "Python", "Django", "Redis", "Kafka"],
        "source": "fallback"
    },
    "zepto": {
        "stack": ["React", "Next.js", "TypeScript", "Node.js",
                  "PostgreSQL", "Redis", "AWS"],
        "frontend": ["React", "Next.js", "TypeScript", "Tailwind CSS"],
        "backend": ["Node.js", "PostgreSQL", "Redis", "AWS Lambda"],
        "source": "fallback"
    },
    "razorpay": {
        "stack": ["React", "Go", "Python", "MySQL", "Redis",
                  "Kafka", "AWS", "Docker"],
        "frontend": ["React", "TypeScript", "GraphQL"],
        "backend": ["Go", "Python", "MySQL", "Redis", "Kafka"],
        "source": "fallback"
    },
    "cred": {
        "stack": ["React Native", "Kotlin", "Swift", "Python",
                  "PostgreSQL", "Redis", "AWS"],
        "frontend": ["React Native", "TypeScript", "Redux"],
        "backend": ["Python", "PostgreSQL", "Redis", "AWS"],
        "source": "fallback"
    },
    "meesho": {
        "stack": ["React", "Python", "Java", "MySQL",
                  "Redis", "Kafka", "GCP"],
        "frontend": ["React", "TypeScript", "Redux"],
        "backend": ["Python", "Java", "MySQL", "GCP"],
        "source": "fallback"
    },
    "phonepe": {
        "stack": ["React", "Java", "Spring Boot", "MySQL",
                  "Redis", "Kafka", "AWS"],
        "frontend": ["React", "TypeScript", "Redux"],
        "backend": ["Java", "Spring Boot", "MySQL", "Redis"],
        "source": "fallback"
    },
    "paytm": {
        "stack": ["React", "Java", "Python", "MySQL",
                  "Redis", "Kafka", "AWS"],
        "frontend": ["React", "JavaScript", "Redux"],
        "backend": ["Java", "Python", "MySQL", "Redis"],
        "source": "fallback"
    },
    "zomato": {
        "stack": ["React", "React Native", "Python", "Go",
                  "PostgreSQL", "Redis", "Kafka", "AWS"],
        "frontend": ["React", "TypeScript", "React Native"],
        "backend": ["Python", "Go", "PostgreSQL", "Redis"],
        "source": "fallback"
    },
    "google": {
        "stack": ["Angular", "TypeScript", "Go", "Python", "Java",
                  "C++", "Kubernetes", "BigQuery", "GCP"],
        "frontend": ["Angular", "TypeScript", "Lit", "Web Components"],
        "backend": ["Go", "Python", "Java", "C++", "Kubernetes"],
        "source": "fallback"
    },
    "microsoft": {
        "stack": ["React", "TypeScript", "C#", ".NET", "Azure",
                  "SQL Server", "Docker", "Kubernetes"],
        "frontend": ["React", "TypeScript", "Azure DevOps"],
        "backend": ["C#", ".NET", "Azure", "SQL Server"],
        "source": "fallback"
    },
    "amazon": {
        "stack": ["React", "Java", "Python", "AWS", "DynamoDB",
                  "Lambda", "S3", "Kafka", "Docker"],
        "frontend": ["React", "TypeScript", "AWS Amplify"],
        "backend": ["Java", "Python", "AWS", "DynamoDB", "Lambda"],
        "source": "fallback"
    },
    "infosys": {
        "stack": ["React", "Angular", "Java", "Python", ".NET",
                  "SQL", "AWS", "Azure", "Docker"],
        "frontend": ["React", "Angular", "JavaScript", "TypeScript"],
        "backend": ["Java", "Python", ".NET", "SQL", "AWS"],
        "source": "fallback"
    },
    "tcs": {
        "stack": ["React", "Angular", "Java", "Python",
                  "SQL", "AWS", "Azure", "Spring Boot"],
        "frontend": ["React", "Angular", "JavaScript"],
        "backend": ["Java", "Python", "SQL", "Spring Boot"],
        "source": "fallback"
    },
    "wipro": {
        "stack": ["React", "Java", "Python", ".NET",
                  "SQL", "AWS", "Azure"],
        "frontend": ["React", "JavaScript", "Angular"],
        "backend": ["Java", "Python", ".NET", "SQL"],
        "source": "fallback"
    },
    "ola": {
        "stack": ["React Native", "Node.js", "Python", "Go",
                  "MySQL", "Redis", "Kafka", "AWS"],
        "frontend": ["React", "React Native", "TypeScript"],
        "backend": ["Node.js", "Python", "Go", "MySQL", "Redis"],
        "source": "fallback"
    },
}


def get_github_stack(company_name: str) -> list:
    """
    Detect company tech stack from their GitHub org
    """
    if not GITHUB_TOKEN:
        return []

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        # Search for company's GitHub org
        search_url = (
            f"https://api.github.com/search/repositories"
            f"?q=org:{company_name.lower()}&sort=stars&per_page=10"
        )
        response = requests.get(search_url, headers=headers, timeout=5)

        if response.status_code != 200:
            return []

        repos = response.json().get("items", [])
        languages = {}

        # Count languages across repos
        for repo in repos[:5]:
            lang = repo.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

        # Sort by frequency
        sorted_langs = sorted(
            languages.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [lang for lang, _ in sorted_langs[:8]]

    except Exception as e:
        print(f"GitHub API error: {e}")
        return []


def get_job_requirements(company: str, role: str) -> list:
    """
    Fetch required skills from live job postings
    """
    if not RAPIDAPI_KEY:
        return []

    try:
        url = "https://jsearch.p.rapidapi.com/search"
        querystring = {
            "query": f"{role} at {company} India",
            "num_pages": "1",
            "page": "1"
        }
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": RAPIDAPI_HOST
        }

        response = requests.get(
            url,
            headers=headers,
            params=querystring,
            timeout=5
        )

        if response.status_code != 200:
            return []

        jobs = response.json().get("data", [])
        skills = []

        for job in jobs[:3]:
            highlights = job.get("job_highlights", {})
            qualifications = highlights.get("Qualifications", [])
            for q in qualifications:
                skills.append(q)

        return skills[:10]

    except Exception as e:
        print(f"RapidAPI error: {e}")
        return []


def get_company_intelligence(company: str, role: str) -> dict:
    """
    Main function - gets full company tech profile
    Tries live APIs first, falls back to database
    """
    company_key = company.lower().replace(" ", "")
    result = {
        "company": company,
        "role": role,
        "stack": [],
        "role_specific_stack": [],
        "live_job_skills": [],
        "source": "unknown"
    }

    # Try GitHub API for live stack detection
    github_langs = get_github_stack(company)

    # Try RapidAPI for live job requirements
    job_skills = get_job_requirements(company, role)

    # Use fallback database
    fallback = COMPANY_STACKS.get(company_key, {})

    if github_langs:
        result["stack"] = github_langs
        result["source"] = "github"
    elif fallback:
        result["stack"] = fallback.get("stack", [])
        result["source"] = "database"
    else:
        result["stack"] = ["JavaScript", "Python", "SQL", "Git", "REST APIs"]
        result["source"] = "generic"

    # Get role-specific stack
    if fallback:
        role_lower = role.lower()
        if "frontend" in role_lower:
            result["role_specific_stack"] = fallback.get("frontend", [])
        elif "backend" in role_lower:
            result["role_specific_stack"] = fallback.get("backend", [])
        else:
            result["role_specific_stack"] = fallback.get("stack", [])[:6]

    # Add live job skills if available
    result["live_job_skills"] = job_skills

    return result
