"""Generate synthetic candidate CV corpus for offline demo and evaluation.

Usage:
    cd /root/main/hobby
    . .venv/bin/activate
    python scripts/generate_corpus.py --output data/corpus --count 40
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

FIRST_NAMES = ["Alice", "Bob", "Carol", "David", "Eva", "Frank", "Grace", "Henry", "Irene", "Jack"]
LAST_NAMES = [
    "Smith",
    "Johnson",
    "Brown",
    "Taylor",
    "Anderson",
    "White",
    "Harris",
    "Martin",
    "Thompson",
    "Garcia",
]
SKILLS_POOL = [
    "Python",
    "FastAPI",
    "Django",
    "Flask",
    "SQLAlchemy",
    "PostgreSQL",
    "Docker",
    "Kubernetes",
    "Terraform",
    "AWS",
    "GCP",
    "React",
    "TypeScript",
    "Tailwind CSS",
    "Node.js",
    "GraphQL",
    "Redis",
    "Celery",
    "Kafka",
    "Elasticsearch",
    "Pytest",
    "CI/CD",
    "GitHub Actions",
    "GitLab CI",
    "Prometheus",
    "Grafana",
    "LLMs",
]
ROLES = [
    "Backend Engineer",
    "Frontend Developer",
    "DevOps Engineer",
    "Full-Stack Developer",
    "Data Engineer",
]
EDUCATION = ["B.Sc. Computer Science", "M.Sc. Software Engineering", "B.Sc. Information Technology"]


def _generate_cv(index: int) -> dict:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    name = f"{first} {last}"
    email = f"candidate{index:03d}@example.com"
    role = random.choice(ROLES)
    years = random.randint(2, 12)
    skill_count = random.randint(4, 8)
    skills = random.sample(SKILLS_POOL, skill_count)
    paragraphs = [
        f"{name} is a {role} with {years} years of experience.",
        f"Core competencies include {', '.join(skills[:4])} and {skills[4] if len(skills) > 4 else 'problem solving'}.",
        f"Education: {random.choice(EDUCATION)}.",
        "Selected experience:\n- Built scalable APIs and microservices.\n- Improved CI/CD pipelines and deployment reliability.\n- Collaborated with cross-functional teams in agile environments.",
    ]
    return {
        "index": index,
        "name": name,
        "email": email,
        "role": role,
        "years": years,
        "skills": skills,
        "cv_text": "\n\n".join(paragraphs),
        "source": "synthetic",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic candidate corpus")
    parser.add_argument("--output", type=Path, default=Path("data/corpus"), help="Output directory")
    parser.add_argument("--count", type=int, default=40, help="Number of profiles")
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    random.seed(42)
    profiles = [_generate_cv(i) for i in range(args.count)]

    corpus_file = out_dir / "candidates.jsonl"
    with corpus_file.open("w", encoding="utf-8") as f:
        for profile in profiles:
            f.write(json.dumps(profile, ensure_ascii=False) + "\n")

    print(f"Generated {len(profiles)} synthetic candidate profiles in {corpus_file}")


if __name__ == "__main__":
    main()
