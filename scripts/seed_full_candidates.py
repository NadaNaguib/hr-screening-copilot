"""Seed complete, rich, realistic CVs, documents, and chunk embeddings for all candidates."""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from copilot.infrastructure.config.settings import get_settings
from copilot.infrastructure.db.models import (
    CandidateORM,
    ChunkORM,
    DocumentORM,
    JobORM,
    ReviewTaskORM,
)
from copilot.infrastructure.providers.embedding_adapter import GeminiEmbeddingAdapter

CANDIDATES_DATA = [
    {
        "full_name": "Alice Johnson",
        "email": "alice.johnson@example.com",
        "phone": "+1-415-555-0142",
        "job_title": "Senior Python Backend Engineer",
        "years_of_experience": 8.0,
        "overall_score": 94.0,
        "status": "screened",
        "skills": [
            "Python",
            "FastAPI",
            "PostgreSQL",
            "System Design",
            "Microservices",
            "AWS",
            "Docker",
            "Redis",
        ],
        "education": [
            {
                "degree": "B.S. in Computer Science",
                "institution": "Stanford University",
                "year": "2012-2016",
                "honors": "Summa Cum Laude",
            }
        ],
        "work_experience": [
            {
                "company": "Stripe",
                "role": "Senior Backend Software Engineer",
                "years": "2020-Present",
                "description": "Designed high-throughput payment settlement microservices in Python & FastAPI processing 50k requests/sec. Optimized PostgreSQL database queries reducing p99 latency by 45%.",
            },
            {
                "company": "FinTech Cloud Solutions",
                "role": "Backend Engineer",
                "years": "2016-2020",
                "description": "Built scalable RESTful APIs with Python, Django, and PostgreSQL. Architected asynchronous event-driven queues with Celery and Redis.",
            },
        ],
        "cv_text": """ALICE JOHNSON
Email: alice.johnson@example.com | Phone: +1-415-555-0142 | Location: San Francisco, CA | GitHub: github.com/alicejohnson

PROFESSIONAL SUMMARY
Distinguished Senior Python Backend Engineer with 8 years of professional experience specializing in scalable microservices, FastAPI architecture, distributed system design, and PostgreSQL database performance tuning. Proven track record of architecting mission-critical financial backend pipelines handling over 50,000 requests per second. Active open-source contributor to modern Python async frameworks.

CORE TECHNICAL SKILLS
• Programming Languages: Python (Expert, 8 yrs), SQL, Go (Intermediate), Bash
• Frameworks & Libraries: FastAPI, AsyncIO, Pydantic, SQLAlchemy, Django, Celery
• Databases & Caching: PostgreSQL, Redis, Elasticsearch, DynamoDB
• Cloud & Infrastructure: AWS (ECS, RDS, S3, Lambda), Docker, Kubernetes, Terraform, CI/CD
• Architecture: Distributed Systems, System Design, Microservices, Event-Driven Architecture, REST, gRPC

PROFESSIONAL WORK EXPERIENCE

Senior Backend Software Engineer | Stripe | 2020 – Present
• Architected and deployed scalable payment transaction pipelines using Python and FastAPI, increasing processing throughput to 50,000 req/sec with 99.999% availability.
• Redesigned PostgreSQL schema, indexing strategies, and connection pooling with asyncpg, cutting p99 database response times by 45%.
• Spearheaded migration from monolithic services to distributed containerized microservices on AWS and Docker.
• Contributed performance patches to open-source FastAPI and starlette ecosystem on GitHub.
• Mentored 6 junior and mid-level engineers in distributed system design, clean architecture, and Python best practices.

Backend Software Engineer | FinTech Cloud Solutions | 2016 – 2020
• Developed core financial ledger and billing APIs using Python, Django, and PostgreSQL.
• Designed asynchronous distributed task execution queues using Redis, Celery, and RabbitMQ.
• Implemented automated CI/CD deployment pipelines using Docker, reducing release cycle time from 2 weeks to 1 hour.
• Collaborated with security teams to enforce zero-trust PII redaction and SOC2 compliance across all endpoints.

EDUCATION
• B.S. in Computer Science | Stanford University (2012 – 2016)
  Honors: Summa Cum Laude, Dean's List, GPA 3.94/4.0

PROJECTS & OPEN SOURCE
• Async-Fast-Gateway: Open-source high-throughput API gateway built in Python & FastAPI with 1,200+ stars on GitHub.
• Scalable Database Partitioning Toolkit: PostgreSQL utility for automated horizontal partitioning of time-series transaction tables.

CERTIFICATIONS
• AWS Certified Solutions Architect – Professional (2022)
• Certified Kubernetes Application Developer (CKAD) (2021)
""",
    },
    {
        "full_name": "Bob Smith",
        "email": "bob.smith@example.com",
        "phone": "+1-206-555-0198",
        "job_title": "Frontend React Developer",
        "years_of_experience": 5.0,
        "overall_score": 88.0,
        "status": "screened",
        "skills": [
            "React",
            "TypeScript",
            "Tailwind CSS",
            "Next.js",
            "Redux Toolkit",
            "UI/UX",
            "Webpack",
            "Jest",
        ],
        "education": [
            {
                "degree": "B.S. in Cognitive Science & Human-Computer Interaction",
                "institution": "UC San Diego",
                "year": "2015-2019",
            }
        ],
        "work_experience": [
            {
                "company": "Shopify",
                "role": "Frontend Specialist",
                "years": "2021-Present",
                "description": "Built responsive merchant analytics dashboards in React 18, TypeScript, and Tailwind CSS. Implemented design system components with WCAG AAA accessibility.",
            },
            {
                "company": "DesignTech Interactive",
                "role": "Frontend Developer",
                "years": "2019-2021",
                "description": "Created interactive e-commerce single page applications with React, Next.js, Redux, and modern CSS modules.",
            },
        ],
        "cv_text": """BOB SMITH
Email: bob.smith@example.com | Phone: +1-206-555-0198 | Location: Seattle, WA | Portfolio: bobsmith.dev

PROFESSIONAL SUMMARY
Creative and detail-oriented Frontend React Developer with 5 years of experience crafting enterprise-grade user interfaces with React, TypeScript, Next.js, and Tailwind CSS. Dedicated to superior UX design, responsive layouts, web accessibility standards (WCAG AAA), and ultra-fast web vitals.

CORE TECHNICAL SKILLS
• Frontend: React (17/18), TypeScript, JavaScript (ES6+), Next.js, Redux Toolkit, Zustand, HTML5, CSS3/SCSS
• Styling & Design: Tailwind CSS, CSS Modules, Radix UI, Figma, Design Systems, Responsive Design
• Build & Testing: Webpack, Vite, Jest, React Testing Library, Cypress, Storybook
• Backend Familiarity: Node.js, Express, REST APIs, GraphQL, basic Python

PROFESSIONAL WORK EXPERIENCE

Frontend Specialist | Shopify | 2021 – Present
• Led frontend architecture for merchant analytics web applications using React, TypeScript, and Tailwind CSS, serving 800,000+ global merchants daily.
• Built enterprise-wide design system UI component library with 100% TypeScript coverage, 95% unit test coverage, and full WCAG accessibility.
• Optimized Core Web Vitals (LCP, FID, CLS), improving page load times by 38% and merchant task completion speed.
• Collaborated closely with product designers in Figma to transform high-fidelity mockups into pixel-perfect modular React components.

Frontend Developer | DesignTech Interactive | 2019 – 2021
• Built interactive client-facing SaaS web applications utilizing React, Redux, and Tailwind CSS.
• Integrated GraphQL and RESTful APIs, reducing client-side payload sizes by 30%.
• Implemented end-to-end integration tests using Cypress, catching critical regressions before production releases.

EDUCATION
• B.S. in Cognitive Science (Human-Computer Interaction) | UC San Diego (2015 – 2019)
  Honors: Provost's Honors, Senior Design Project Excellence Award

PROJECTS & OPEN SOURCE
• Tailwind-React-Components: Open-source accessible UI component library with 800+ GitHub stars.
• React State Visualizer: Interactive Chrome DevTools extension for inspecting reactive state trees.
""",
    },
    {
        "full_name": "Carol White",
        "email": "carol.white@example.com",
        "phone": "+1-512-555-0167",
        "job_title": "DevOps Engineer",
        "years_of_experience": 7.0,
        "overall_score": 91.0,
        "status": "screened",
        "skills": [
            "Docker",
            "Kubernetes",
            "Terraform",
            "AWS",
            "CI/CD",
            "Helm",
            "Prometheus",
            "Grafana",
            "Linux",
        ],
        "education": [
            {
                "degree": "B.S. in Computer Engineering",
                "institution": "University of Washington",
                "year": "2013-2017",
            }
        ],
        "work_experience": [
            {
                "company": "CloudNative Systems",
                "role": "Senior DevOps & Infrastructure Engineer",
                "years": "2020-Present",
                "description": "Managed multi-region production Kubernetes (EKS) clusters. Automated cloud infrastructure with Terraform and built GitOps CI/CD pipelines with GitHub Actions and ArgoCD.",
            },
            {
                "company": "DataScale Platform",
                "role": "DevOps Engineer",
                "years": "2017-2020",
                "description": "Automated Docker container builds and deployments. Managed cloud infrastructure across AWS and GCP, instrumenting observability with Prometheus and Grafana.",
            },
        ],
        "cv_text": """CAROL WHITE
Email: carol.white@example.com | Phone: +1-512-555-0167 | Location: Austin, TX | GitHub: github.com/carolwhite-devops

PROFESSIONAL SUMMARY
Accomplished DevOps and Platform Engineer with 7 years of specialized expertise in cloud-native infrastructure, Kubernetes cluster orchestration, Infrastructure as Code (Terraform), Docker containerization, and GitOps CI/CD automation. Proven ability to achieve 99.99% infrastructure uptime across enterprise AWS multi-region environments.

CORE TECHNICAL SKILLS
• Containerization & Orchestration: Docker, Kubernetes (EKS, GKE, K8s), Helm, Istio Service Mesh, ArgoCD
• Infrastructure as Code: Terraform, Terragrunt, AWS CloudFormation, Ansible
• Cloud Providers: Amazon Web Services (AWS - EKS, RDS, S3, IAM, VPC), Google Cloud Platform (GCP)
• CI/CD & Automation: GitHub Actions, GitLab CI, Jenkins, Bash, Python scripting
• Observability: Prometheus, Grafana, Datadog, ELK Stack, OpenTelemetry

PROFESSIONAL WORK EXPERIENCE

Senior DevOps & Infrastructure Engineer | CloudNative Systems | 2020 – Present
• Architected and maintained 12 production Kubernetes (AWS EKS) clusters running over 600 microservices with 99.99% uptime.
• Automated 100% of multi-region cloud infrastructure using modular Terraform, cutting environment provisioning time from 4 days to 15 minutes.
• Implemented GitOps continuous delivery workflows using ArgoCD and GitHub Actions, enabling zero-downtime canary deployments.
• Designed centralized metrics and alerting systems with Prometheus and Grafana dashboards, reducing Mean Time to Detection (MTTD) by 60%.
• Implemented rigorous AWS security controls, IAM role least-privilege policies, and container image vulnerability scanning via Trivy.

DevOps Engineer | DataScale Platform | 2017 – 2020
• Containerized legacy backend monolithic applications into optimized Docker images, shrinking image sizes by 70%.
• Built automated CI/CD build and test pipelines using GitLab CI for 40+ engineering repositories.
• Managed hybrid cloud resources across AWS and Google Cloud Platform (GCP).
• Administered Linux server fleets (Ubuntu/CentOS), automated patch management and backups.

EDUCATION
• B.S. in Computer Engineering | University of Washington (2013 – 2017)
  Magna Cum Laude, President of ACM Cloud Computing Chapter

CERTIFICATIONS
• AWS Certified Solutions Architect – Professional
• Certified Kubernetes Administrator (CKA)
• HashiCorp Certified: Terraform Associate
""",
    },
    {
        "full_name": "David Brown",
        "email": "david.brown@example.com",
        "phone": "+1-312-555-0183",
        "job_title": "Senior Full-Stack Engineer",
        "years_of_experience": 6.0,
        "overall_score": 87.0,
        "status": "screened",
        "skills": [
            "Python",
            "React",
            "TypeScript",
            "FastAPI",
            "PostgreSQL",
            "GraphQL",
            "Leadership",
            "SaaS",
        ],
        "education": [
            {
                "degree": "B.S. in Computer Science",
                "institution": "University of Illinois Urbana-Champaign",
                "year": "2014-2018",
            }
        ],
        "work_experience": [
            {
                "company": "SaaSify Tech",
                "role": "Lead Full-Stack Developer",
                "years": "2021-Present",
                "description": "Led team of 4 engineers building end-to-end features with Python, FastAPI, and React. Architected GraphQL APIs and PostgreSQL schemas.",
            },
            {
                "company": "Enterprise Software Lab",
                "role": "Full-Stack Engineer",
                "years": "2018-2021",
                "description": "Developed full-stack web applications with Python (Django/FastAPI), React, and PostgreSQL. Mentored junior developers.",
            },
        ],
        "cv_text": """DAVID BROWN
Email: david.brown@example.com | Phone: +1-312-555-0183 | Location: Chicago, IL | LinkedIn: linkedin.com/in/davidbrown-dev

PROFESSIONAL SUMMARY
Versatile Full-Stack Engineer and Tech Lead with 6 years of experience driving SaaS product development. Master of both backend (Python, FastAPI, PostgreSQL) and modern frontend (React, TypeScript), with proven experience leading small engineering teams from discovery to production delivery.

CORE TECHNICAL SKILLS
• Backend: Python, FastAPI, Django, PostgreSQL, GraphQL, REST APIs, Redis
• Frontend: React, TypeScript, Redux, Next.js, Tailwind CSS, HTML5, CSS3
• Architecture & Leadership: Team Leadership, Agile/Scrum, System Design, Code Reviews, Technical Architecture
• Tools & Cloud: Docker, Git, AWS (EC2, S3), CI/CD pipelines

PROFESSIONAL WORK EXPERIENCE

Lead Full-Stack Developer | SaaSify Tech | 2021 – Present
• Led a cross-functional team of 4 full-stack developers delivering high-volume collaborative SaaS workspace features for 200,000+ active users.
• Architected end-to-end data flow: designed PostgreSQL relational schemas, built FastAPI and GraphQL backend microservices, and developed dynamic React frontend interfaces.
• Implemented real-time collaboration features using WebSockets and Redis pub/sub.
• Mentored team members, conducted weekly code reviews, and championed unit/integration testing with pytest and Jest.

Full-Stack Engineer | Enterprise Software Lab | 2018 – 2021
• Developed customer-facing web applications using Python (Django & FastAPI) and React with TypeScript.
• Optimized complex PostgreSQL queries and indexing, cutting reporting dashboard loading times by 50%.
• Integrated third-party payment gateways and OAuth2 authentication workflows.

EDUCATION
• B.S. in Computer Science | University of Illinois Urbana-Champaign (2014 – 2018)
""",
    },
    {
        "full_name": "Eva Green",
        "email": "eva.green@example.com",
        "phone": "+1-415-555-0176",
        "job_title": "Senior Python Backend Engineer",
        "years_of_experience": 2.0,
        "overall_score": 74.0,
        "status": "uploaded",
        "skills": [
            "Python",
            "Django",
            "FastAPI",
            "SQL",
            "PostgreSQL",
            "REST APIs",
            "Git",
            "Learning",
        ],
        "education": [
            {
                "degree": "B.S. in Computer Science",
                "institution": "UC Berkeley",
                "year": "2018-2022",
            }
        ],
        "work_experience": [
            {
                "company": "Berkeley Tech Labs",
                "role": "Junior Backend Developer",
                "years": "2022-Present",
                "description": "Developed RESTful APIs with Python and Django. Wrote unit tests, database migrations, and queries with PostgreSQL.",
            }
        ],
        "cv_text": """EVA GREEN
Email: eva.green@example.com | Phone: +1-415-555-0176 | Location: San Francisco, CA

PROFESSIONAL SUMMARY
Motivated Junior Backend Developer with 2 years of professional software development experience in Python and Django. Strong academic computer science foundation from UC Berkeley with practical experience building REST APIs, PostgreSQL databases, and automated testing. Eager to master FastAPI, distributed microservices, and cloud architectures.

CORE TECHNICAL SKILLS
• Programming: Python (Proficient), SQL, Bash, basic JavaScript
• Frameworks: Django, Django REST Framework, beginner FastAPI
• Databases: PostgreSQL, SQLite
• Version Control & Tools: Git, GitHub, Postman, PyTest, Linux

PROFESSIONAL WORK EXPERIENCE

Junior Backend Developer | Berkeley Tech Labs | 2022 – Present
• Developed and documented RESTful API endpoints for university research database applications using Python and Django.
• Designed PostgreSQL tables, wrote relational queries, and implemented schema migrations.
• Authored comprehensive unit and integration test suites using pytest, achieving 88% code coverage.
• Assisted senior backend engineers in containerizing applications with Docker.

EDUCATION
• B.S. in Computer Science | University of California, Berkeley (2018 – 2022)
  Relevant Coursework: Data Structures, Algorithms, Database Systems, Computer Architecture
""",
    },
    {
        "full_name": "Youssef Eid",
        "email": "youssef.eid@example.com",
        "phone": "+20-100-555-0199",
        "job_title": "Senior Python Backend Engineer",
        "years_of_experience": 7.0,
        "overall_score": 92.0,
        "status": "screened",
        "skills": [
            "Python",
            "Machine Learning",
            "AI",
            "PyTorch",
            "FastAPI",
            "Docker",
            "Data Pipelines",
            "PostgreSQL",
            "Vector Search",
        ],
        "education": [
            {
                "degree": "B.S. in Computer Science & Artificial Intelligence",
                "institution": "Cairo University",
                "year": "2013-2017",
                "honors": "First Class Honors",
            }
        ],
        "work_experience": [
            {
                "company": "DeepAI Solutions",
                "role": "Senior AI & Backend Engineer",
                "years": "2020-Present",
                "description": "Architected AI-powered document extraction pipelines using PyTorch, HuggingFace Transformers, and FastAPI. Built high-scale vector search pipelines with pgvector.",
            },
            {
                "company": "SmartTech MENA",
                "role": "Python Machine Learning Engineer",
                "years": "2017-2020",
                "description": "Trained and deployed deep learning models in production with Python, Docker, and PostgreSQL.",
            },
        ],
        "cv_text": """YOUSSEF EID
Email: youssef.eid@example.com | Phone: +20-100-555-0199 | Location: Cairo, Egypt | GitHub: github.com/youssefeid

PROFESSIONAL SUMMARY
Senior AI and Python Backend Engineer with 7 years of deep experience building production Machine Learning (ML), Natural Language Processing (NLP), and vector search systems. Expert in combining PyTorch deep learning models with high-speed FastAPI microservices and PostgreSQL/pgvector pipelines.

CORE TECHNICAL SKILLS
• AI & Machine Learning: PyTorch, TensorFlow, HuggingFace Transformers, Scikit-Learn, LangChain, RAG Systems
• Backend & Systems: Python (Expert), FastAPI, AsyncIO, Docker, PostgreSQL, pgvector, Redis, gRPC
• Data Engineering: Apache Spark, Pandas, NumPy, Data Ingestion Pipelines

PROFESSIONAL WORK EXPERIENCE

Senior AI & Backend Engineer | DeepAI Solutions | 2020 – Present
• Designed and shipped an automated document intelligence platform utilizing Python, PyTorch transformers, and FastAPI serving 1M+ daily document predictions.
• Built vector search indexing engine with pgvector and hybrid retrieval, boosting search accuracy by 35%.
• Containerized ML inference services with Docker and optimized GPU memory utilization, cutting inference latency by 50%.
• Mentored junior machine learning engineers and reviewed production ML deployment pipelines.

Python Machine Learning Engineer | SmartTech MENA | 2017 – 2020
• Developed predictive analytics and recommendation engines in Python and Scikit-Learn.
• Deployed RESTful API inference endpoints using FastAPI and PostgreSQL backend databases.

EDUCATION
• B.S. in Computer Science & Artificial Intelligence | Cairo University (2013 – 2017)
  First Class Honors, Graduation Project: Neural Semantic Search Engine (Ranked #1)
""",
    },
    {
        "full_name": "Elena Rostova",
        "email": "elena.rostova@example.com",
        "phone": "+1-617-555-0133",
        "job_title": "Senior Python Backend Engineer",
        "years_of_experience": 5.0,
        "overall_score": 89.0,
        "status": "screened",
        "skills": [
            "Python",
            "C++",
            "Distributed Systems",
            "PostgreSQL",
            "FastAPI",
            "High Concurrency",
            "System Design",
        ],
        "education": [
            {
                "degree": "B.Sc. in Computer Science & Engineering",
                "institution": "Tech University",
                "year": "2015-2019",
                "honors": "Magna Cum Laude",
            }
        ],
        "work_experience": [
            {
                "company": "HighFrequency Distributed Systems",
                "role": "Backend Software Engineer",
                "years": "2019-Present",
                "description": "Engineered low-latency distributed transaction systems in C++ and Python. Specialized in concurrent algorithms and database performance.",
            }
        ],
        "cv_text": """ELENA ROSTOVA
Email: elena.rostova@example.com | Phone: +1-617-555-0133 | Location: Boston, MA

PROFESSIONAL SUMMARY
Senior Software Engineer with 5 years of experience building high-concurrency distributed systems and backend services using C++ and Python. Deep expertise in distributed data structures, concurrency control, system design, and database optimization.

CORE TECHNICAL SKILLS
• Languages: Python, C++, SQL, Bash
• Distributed Systems: Concurrency, High Throughput, Fault Tolerance, Socket Programming
• Databases: PostgreSQL, Redis, Cassandra

EDUCATION
• B.Sc. in Computer Science & Engineering | Tech University (2015 – 2019)
  Honors: Magna Cum Laude, Dean's Honors List
""",
    },
    {
        "full_name": "Samira El-Sayed",
        "email": "samira.elsayed@example.com",
        "phone": "+20-102-555-0188",
        "job_title": "Senior Python Backend Engineer",
        "years_of_experience": 9.0,
        "overall_score": 96.0,
        "status": "screened",
        "skills": [
            "Go",
            "Python",
            "Microservices",
            "Event-Driven Architecture",
            "Kafka",
            "PostgreSQL",
            "System Design",
            "Leadership",
        ],
        "education": [
            {
                "degree": "B.Sc. in Computer Engineering",
                "institution": "Cairo University",
                "year": "2011-2015",
            }
        ],
        "work_experience": [
            {
                "company": "Global Distributed Cloud",
                "role": "Lead Backend Architect",
                "years": "2019-Present",
                "description": "Led team of 8 architects designing event-driven microservices across Go, Python, and Kafka. Highest seniority in talent pool with 9 years of experience.",
            }
        ],
        "cv_text": """SAMIRA EL-SAYED
Email: samira.elsayed@example.com | Phone: +20-102-555-0188 | Location: Cairo, Egypt

PROFESSIONAL SUMMARY
Distinguished Lead Backend Architect with 9 years of professional experience directing enterprise microservices architecture, event-driven streaming with Apache Kafka, and distributed systems across Go and Python. Extensive leadership experience managing teams of 8+ engineers.

CORE TECHNICAL SKILLS
• Architecture & Leadership: Lead Architect, Team Management (8 engineers), System Design, Event-Driven Architecture
• Languages: Python (9 yrs), Go (6 yrs), SQL
• Messaging & Data: Apache Kafka, PostgreSQL, Redis, gRPC

EDUCATION
• B.Sc. in Computer Engineering | Cairo University (2011 – 2015)
""",
    },
]


def _chunk_cv(text_content: str, filename: str) -> list[dict[str, Any]]:
    """Split CV text into logical sections with page numbers."""
    sections = [s.strip() for s in text_content.split("\n\n") if s.strip()]
    chunks = []
    current_chunk = []
    current_len = 0
    page = 1

    for s in sections:
        current_chunk.append(s)
        current_len += len(s)
        if current_len >= 350:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(
                {
                    "text": chunk_text,
                    "page": page,
                    "filename": filename,
                }
            )
            current_chunk = []
            current_len = 0
            if len(chunks) % 2 == 0:
                page += 1

    if current_chunk:
        chunks.append(
            {
                "text": "\n\n".join(current_chunk),
                "page": page,
                "filename": filename,
            }
        )
    return chunks


async def run_seed():
    db_url = get_settings().database_url
    engine = create_async_engine(db_url, future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    embedding_adapter = GeminiEmbeddingAdapter()

    async with session_factory() as session:
        # 1. Clean up duplicate uploaded candidates with name 'Youssef_Eid_CV.pdf'
        stmt_dup = select(CandidateORM).where(CandidateORM.full_name.ilike("%Youssef%"))
        res_dup = await session.execute(stmt_dup)
        youssef_list = res_dup.scalars().all()
        if len(youssef_list) > 1:
            keep = youssef_list[0]
            keep.full_name = "Youssef Eid"
            for other in youssef_list[1:]:
                # find docs with this candidate_id
                docs_res = await session.execute(select(DocumentORM))
                for doc_row in docs_res.scalars().all():
                    meta = doc_row.metadata_ or {}
                    if str(meta.get("candidate_id")) == str(other.id):
                        await session.execute(
                            delete(ChunkORM).where(ChunkORM.document_id == doc_row.id)
                        )
                        await session.delete(doc_row)
                await session.execute(
                    delete(ReviewTaskORM).where(ReviewTaskORM.candidate_id == other.id)
                )
                await session.delete(other)
            await session.flush()

        # 2. Map jobs
        jobs_res = await session.execute(select(JobORM))
        jobs = {j.title: j for j in jobs_res.scalars().all()}
        default_job = list(jobs.values())[0] if jobs else None

        # 3. Seed or update each candidate
        for cdata in CANDIDATES_DATA:
            full_name = cdata["full_name"]
            target_job = jobs.get(cdata["job_title"], default_job)
            job_id = target_job.id if target_job else None

            # Check existing candidate
            c_res = await session.execute(
                select(CandidateORM).where(CandidateORM.full_name == full_name)
            )
            candidate = c_res.scalar_one_or_none()
            if not candidate:
                candidate = CandidateORM(
                    id=uuid.uuid4(),
                    full_name=full_name,
                    email=cdata["email"],
                    phone=cdata["phone"],
                    years_of_experience=cdata["years_of_experience"],
                    skills=cdata["skills"],
                    education=cdata["education"],
                    work_experience=cdata["work_experience"],
                    raw_text=cdata["cv_text"],
                    cv_sha256=hashlib.sha256(cdata["cv_text"].encode()).hexdigest(),
                    status=cdata["status"],
                    overall_score=cdata["overall_score"],
                    priority="HIGH" if cdata["overall_score"] >= 90 else "MEDIUM",
                    job_id=job_id,
                )
                session.add(candidate)
                await session.flush()
            else:
                candidate.email = cdata["email"]
                candidate.phone = cdata["phone"]
                candidate.years_of_experience = cdata["years_of_experience"]
                candidate.skills = cdata["skills"]
                candidate.education = cdata["education"]
                candidate.work_experience = cdata["work_experience"]
                candidate.raw_text = cdata["cv_text"]
                candidate.overall_score = cdata["overall_score"]
                candidate.status = cdata["status"]
                if job_id:
                    candidate.job_id = job_id
                await session.flush()

            # Ensure review task
            rt_res = await session.execute(
                select(ReviewTaskORM).where(ReviewTaskORM.candidate_id == candidate.id)
            )
            if not rt_res.scalar_one_or_none() and job_id:
                session.add(
                    ReviewTaskORM(
                        id=uuid.uuid4(),
                        candidate_id=candidate.id,
                        job_id=job_id,
                        status="PENDING_TRIAGE",
                        priority=candidate.priority,
                    )
                )

            # Ensure Document record
            filename = f"{full_name.replace(' ', '_')}_CV.pdf"
            all_docs = (await session.execute(select(DocumentORM))).scalars().all()
            doc = None
            for d in all_docs:
                meta = d.metadata_ or {}
                if str(meta.get("candidate_id")) == str(candidate.id) or d.filename == filename:
                    doc = d
                    break

            if not doc:
                doc = DocumentORM(
                    id=uuid.uuid4(),
                    job_id=job_id,
                    filename=filename,
                    mime_type="application/pdf",
                    sha256=hashlib.sha256(cdata["cv_text"].encode()).hexdigest(),
                    raw_text=cdata["cv_text"],
                    metadata_={"candidate_id": str(candidate.id), "full_name": full_name},
                )
                session.add(doc)
                await session.flush()
            else:
                doc.raw_text = cdata["cv_text"]
                doc.filename = filename
                doc.job_id = job_id
                doc.metadata_ = {"candidate_id": str(candidate.id), "full_name": full_name}
                await session.flush()

            # Generate chunks and embeddings
            chunk_items = _chunk_cv(cdata["cv_text"], filename)
            # Remove old chunks for this doc
            await session.execute(delete(ChunkORM).where(ChunkORM.document_id == doc.id))
            await session.flush()

            texts_to_embed = [ch["text"] for ch in chunk_items]
            embeddings = await embedding_adapter.embed(texts_to_embed)

            for idx, ch in enumerate(chunk_items):
                emb = embeddings[idx] if idx < len(embeddings) else None
                chunk_orm = ChunkORM(
                    id=uuid.uuid4(),
                    document_id=doc.id,
                    job_id=job_id,
                    text=ch["text"],
                    page_number=ch["page"],
                    embedding=emb,
                    metadata_={
                        "filename": filename,
                        "candidate_id": str(candidate.id),
                        "full_name": full_name,
                        "page_number": ch["page"],
                        "chunk_index": idx,
                    },
                )
                session.add(chunk_orm)
            await session.flush()
            print(f"Seeded {full_name}: {len(chunk_items)} chunks indexed.")

        await session.commit()
        print("All candidates, documents, and chunk embeddings seeded successfully!")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_seed())
