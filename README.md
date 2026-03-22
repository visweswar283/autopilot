# ApplyPilot — Automated Job Application System

An intelligent, fully automated job application platform that discovers job listings across major portals, tailors your resume using AI/ML, and submits applications on your behalf — end-to-end.

> **Multi-tenant by design** — built for a single user today, scales to thousands without re-architecture.

---

## Overview

ApplyPilot automates the entire job hunting lifecycle:
- Scraping & discovering jobs from LinkedIn, Jobright, Workday, Indeed, Greenhouse, Lever, and more
- Automated form filling and application submission with your standard resume
- Application tracking, analytics, and status dashboards
- Intelligent cross-portal deduplication, scoring, and prioritization of job postings

> **Deferred to future phases:** Resume tailoring, cover letter generation (unlocked at higher subscription tiers)

---

## Multi-Tenancy Model

The system is designed in three distinct layers, each with a clear scaling strategy:

```
┌─────────────────────────────────────────────────────────────┐
│  PLATFORM LAYER  (shared across all users)                   │
│  Job scraping · JD deduplication · Portal health monitoring  │
│  Runs on: Airflow cron DAGs                                  │
└─────────────────────────────────────────────────────────────┘
                           │ feeds job pool
┌─────────────────────────────────────────────────────────────┐
│  TENANT LAYER  (per-user, isolated)                          │
│  Scoring · Applying · Status tracking                        │
│  Runs on: Celery worker queue (fair-scheduled per user)      │
└─────────────────────────────────────────────────────────────┘
                           │ enforced by
┌─────────────────────────────────────────────────────────────┐
│  DATA LAYER  (PostgreSQL RLS + namespaced S3)                │
│  Every query scoped to tenant_id at DB level                 │
│  No cross-tenant data leakage possible                       │
└─────────────────────────────────────────────────────────────┘
```

**Key insight:** Job scraping is shared (same LinkedIn jobs exist for everyone). Only the per-user work (scoring, tailoring, applying) runs per-tenant. This makes scraping O(1) regardless of user count.

---

## Architecture at a Glance

```
┌──────────────────────────────────────────────────────────────────────┐
│                        User Interface (Next.js)                       │
│          Dashboard · Resume Manager · Job Feed · Analytics            │
└─────────────────────────┬────────────────────────────────────────────┘
                          │ REST + Polling (WebSocket deferred to Phase 5)
┌─────────────────────────▼────────────────────────────────────────────┐
│                     Go Backend (API + Auth Gateway)                   │
│         Auth · Jobs · Applications · Resume · Tenant Management       │
│                  Rate limiting per user per portal                    │
└──────┬─────────────┬──────────────┬──────────────┬───────────────────┘
       │             │              │              │
┌──────▼──────┐ ┌────▼──────┐ ┌────▼──────┐ ┌────▼──────────────────┐
│ PostgreSQL  │ │  Redis    │ │    S3     │ │  Python ML Service     │
│ + Row Level │ │ Task Queue│ │ Per-tenant│ │  Job Scorer · NLP      │
│  Security   │ │ + Cache   │ │ namespace │ │  (Tailoring: Phase 5+) │
└─────────────┘ └─────┬─────┘ └───────────┘ └────────────────────────┘
                      │ Celery tasks (per-user, fair-queued)
┌─────────────────────▼────────────────────────────────────────────────┐
│                  Celery Worker Pool (Application Workers)             │
│        score_jobs_for_user · apply_to_job · sync_status              │
│   Fair queue: max N concurrent tasks per user (no starvation)        │
└─────────────────────┬────────────────────────────────────────────────┘
                      │ per-user browser sessions + credentials
┌─────────────────────▼────────────────────────────────────────────────┐
│               Browser Automation Workers (Python + Playwright)        │
│  Each worker has 1 browser session = 1 user account (isolated)       │
│  LinkedIn · Workday · Greenhouse · Lever · Jobright · Indeed         │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│             Apache Airflow (Platform-level cron only)                 │
│   scrape_jobs_dag · dedup_dag · portal_health_dag · cleanup_dag      │
│   NOT used for per-user work — Celery handles that                   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│              Kubernetes (EKS) + Docker                                │
│  Go API pods · Celery worker pods · ML service pods · Airflow pods   │
│  Celery workers auto-scale on queue depth (KEDA)                     │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│            Prometheus + Grafana (Observability)                       │
│  Per-tenant metrics · Queue depth · Portal health · Funnel analytics │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Scalability at Each Growth Stage

### Stage 1 — Solo (1 user, current)
- Docker Compose local dev
- Single PostgreSQL + Redis
- Airflow LocalExecutor
- Celery with 2-3 workers

### Stage 2 — Small SaaS (10–100 users)
- Deploy to EKS
- Celery worker pool scales to 10–20 pods
- PostgreSQL with PgBouncer connection pooler
- Per-user rate limiting enforced in Go API
- Redis Streams as Celery broker

### Stage 3 — Growing SaaS (100–10,000 users)
- Celery workers auto-scale via KEDA on queue depth
- PostgreSQL read replica for analytics queries
- S3 for all file storage, no local disk
- Airflow KubernetesExecutor (platform DAGs only)
- Tenant subscription plans + usage metering

### Stage 4 — Large Scale (10,000+ users)
- Horizontal PostgreSQL sharding by `tenant_id` (Citus or migrate to CockroachDB)
- Dedicated worker pools per subscription tier (free vs paid)
- Multi-region deployment
- CDN for frontend (CloudFront)

---

## Core Modules

### 1. Job Discovery & Scraping (Platform-shared)
- Crawlers for LinkedIn, Jobright, Workday, Indeed, Greenhouse, Lever, Dice, Glassdoor
- Jobs scraped **once, stored globally** — all users see the same job pool
- Per-user scoring happens separately after scraping
- **Two-level deduplication:**
  - `fingerprint` — dedup within a portal (same job reposted)
  - `cross_portal_fingerprint` — dedup across portals: `hash(company + title + location + posted_date)` prevents applying to the same role 3 times from different portals
- Airflow cron DAG, not per-user

### 2. AI / ML Engine (Python, stateless)
- **Job Scoring**: Rank jobs by match score against user profile and skills
- Stateless FastAPI service — scales horizontally with no coordination
- **Deferred to Phase 5+**: Resume tailoring, cover letter generation, skill gap analysis (paid tier features)

### 3. Application Automation (Per-user, isolated workers)
- One browser session = one user account (never shared)
- Credentials fetched from AWS Secrets Manager per task, never in env vars
- Per-user per-portal rate limits tracked in Redis
- Smart form filling with standard resume, CAPTCHA fallback to human review queue
- Supports: LinkedIn Easy Apply, Workday, Greenhouse, Lever
- No cover letter submission (deferred to Phase 5+)

### 4. Tenant & Subscription Management
- Subscription plans: Free / Pro / Team
- Per-plan quotas: max applies/day, portals enabled, ML features
- Usage metering stored in PostgreSQL
- Plan enforcement in Go API middleware

### 5. Fair Queue Scheduling (Celery)
- Each user gets their own Celery queue namespace
- Global worker pool with per-user concurrency cap
- No single user can monopolize the worker pool
- Priority boost for paid tiers

### 6. Application Tracking
- Full lifecycle: Discovered → Queued → Applied → Viewed → Interview → Offer → Rejected
- Per-tenant analytics: response rates, portal effectiveness, salary trends
- Email parsing for status updates (Gmail/Outlook integration)

### 7. Observability (Per-tenant metrics)
- Prometheus metrics labeled with `tenant_id` (aggregated, not raw user data)
- Grafana dashboards: platform-wide + per-user drill-down
- Alerts: failed worker pods, queue backlog, portal credential expiry

---

## Tech Stack Summary

| Layer | Technology | Reason |
|-------|-----------|--------|
| Frontend | Next.js (React) | SSR, fast UI, great DX |
| Backend API | Go (Gin/Fiber) | High performance, low latency, easy horizontal scale |
| ML/AI Service | Python (FastAPI) | Rich ML ecosystem, stateless |
| Automation Workers | Python (Playwright) | Best-in-class browser automation |
| Platform Orchestration | Apache Airflow | Cron-based platform jobs only |
| Per-user Task Queue | Celery + Redis | Fair scheduling, dynamic per-user tasks |
| Primary Database | PostgreSQL + RLS | Tenant isolation at DB level, ACID |
| Connection Pool | PgBouncer | Needed at 100+ concurrent users |
| Cache / Broker | Redis | Task queue + fast cache |
| Object Storage | AWS S3 | Tenant-namespaced, cheap, durable |
| Container Registry | AWS ECR | Native EKS integration |
| Container Runtime | Docker | Standard image format |
| Orchestration | Kubernetes (EKS) | Auto-scale worker pool via KEDA |
| Worker Autoscaler | KEDA | Scale Celery workers on queue depth |
| Monitoring | Prometheus + Grafana | Per-tenant dashboards |
| ML Models | HuggingFace (sentence-transformers, spaCy) | Job scoring only; LLM APIs deferred to Phase 7 |

---

## Supported Job Portals (Planned)

- [x] LinkedIn (Easy Apply + Standard)
- [x] Workday ATS
- [x] Greenhouse ATS
- [x] Lever ATS
- [x] Jobright
- [ ] Indeed
- [ ] Dice
- [ ] Glassdoor
- [ ] ZipRecruiter
- [ ] Monster
- [ ] Handshake (campus)

---

## Key Design Principles

1. **Scraping is shared, applying is isolated** — O(1) scraping cost regardless of user count
2. **Tenant isolation at every layer** — RLS in DB, namespaced S3, per-user Celery queues, isolated browser sessions
3. **Fair scheduling** — Celery concurrency caps prevent any user from starving others
4. **Credentials never in code or env** — always fetched from AWS Secrets Manager per task
5. **Human-in-the-loop** — configurable auto-apply thresholds; ambiguous jobs go to review queue
6. **Cost minimization** — shared job pool, spot instances, no expensive managed services
7. **Stateless services** — Go API + ML service have no local state; safe to scale to N replicas

---

## Roadmap

### Phase 1 — Foundation (Single User)
- Go API skeleton (auth, user, jobs CRUD)
- PostgreSQL schema with RLS from day 1
- Next.js dashboard shell
- Docker Compose local dev environment

### Phase 2 — Scraping
- LinkedIn and Workday scrapers
- Airflow DAG for platform scraping
- Job deduplication and global job pool

### Phase 3 — ML Engine (Scoring Only)
- Resume parser + job scoring (sentence-transformers)
- Celery tasks for per-user scoring
- No tailoring yet

### Phase 4 — Automation
- LinkedIn Easy Apply bot (standard resume, no cover letter)
- Workday form filler
- Per-user browser session management
- Application status tracking

### Phase 5 — Multi-Tenant
- Subscription plans + usage metering
- Per-user Celery fair queues
- KEDA autoscaler for worker pods
- Tenant analytics dashboard

### Phase 6 — Production & Scale
- Kubernetes deployment
- PgBouncer connection pooling
- Email status sync
- Prometheus per-tenant metrics

### Phase 7 — Intelligence (Paid Tier Features)
- Resume tailoring per job description (LLM-based)
- Cover letter generation
- Response rate learning (per user, anonymized aggregate)
- Skill gap analysis
- Salary intelligence
- Interview prep assistant

---

## Getting Started (Local Dev)

```bash
# Prerequisites: Docker, Docker Compose, Go 1.22+, Python 3.11+, Node.js 20+

git clone https://github.com/yourhandle/applypilot
cd applypilot

# Start all services locally
docker compose up -d

# Run DB migrations (RLS policies included)
make migrate-up

# Run Go API
cd backend && go run main.go

# Run ML service
cd ml-service && pip install -r requirements.txt && uvicorn main:app --reload

# Run Celery workers
cd workers && celery -A tasks worker --concurrency=4

# Run frontend
cd frontend && npm install && npm run dev
```

---

## Deferred Features Backlog

Everything below was intentionally removed from the current build scope to keep the MVP lean. These are not abandoned — they are queued for future phases. Pick them up when the time is right.

---

### UI / Real-time

| Feature | Why Deferred | When to Add |
|---------|-------------|-------------|
| WebSocket / SSE for live status updates | Polling is sufficient for MVP; WebSocket adds infra complexity | Phase 5 — when users complain about stale status |
| Email notifications (applied, interview invite, offer) | Requires email provider setup (SES / SendGrid) | Phase 5 |
| Browser push notifications | Requires PWA setup | Phase 6+ |

---

### Application Content

| Feature | Why Deferred | When to Add |
|---------|-------------|-------------|
| Cover letter generation (LLM-based) | Adds cost per application, no tailoring either way in MVP | Phase 7 — paid tier |
| Resume tailoring per job description | LLM cost at scale; needs caching layer first | Phase 7 — paid tier |
| ML cost caching layer (`hash(resume_id + job_fingerprint)`) | Only needed once tailoring is live | Same time as tailoring |
| A/B testing resume versions | Needs response rate data first (need months of data) | Phase 7 |

---

### Intelligence & Analytics

| Feature | Why Deferred | When to Add |
|---------|-------------|-------------|
| Skill gap analysis (`resume vs target_role`) | Requires LLM; deferred with tailoring | Phase 7 |
| Response rate learning (improve scoring from outcomes) | Needs 3–6 months of application data to be useful | Phase 7 |
| Salary intelligence (market salary per role + location) | Needs data aggregation pipeline | Phase 7 |
| Interview prep assistant | Out of MVP scope entirely | Phase 8 |
| Company research auto-summary | Out of MVP scope | Phase 8 |

---

### Infrastructure / Auth

| Feature | Why Deferred | When to Add |
|---------|-------------|-------------|
| OAuth for portal authentication (instead of password) | Portals don't widely support OAuth for automation | When portals offer it |
| GDPR: user data export + right-to-delete endpoint | Required before EU launch | Before any EU marketing |
| Multi-region deployment | Single region is fine until latency complaints | Phase 6+ |
| CDN (CloudFront) for frontend | Not worth the cost at small scale | Phase 6 |

---

### Portal Coverage

| Portal | Why Deferred | Notes |
|--------|-------------|-------|
| Indeed | ToS is strict on automation | Investigate API options |
| Dice | Lower priority for target roles | Phase 4 |
| Glassdoor | Apply redirects to external ATS anyway | Low value-add |
| ZipRecruiter | Mid-priority | Phase 4 |
| Monster | Low priority | Phase 5 |
| Handshake | Campus-focused, niche | Phase 6 |

---

## License

Private — all rights reserved.
