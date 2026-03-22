# ApplyPilot — Developer Guide

Complete technical reference for contributors and maintainers.

---

## Table of Contents

1. [Repository Structure](#repository-structure)
2. [Multi-Tenancy Architecture Decisions](#multi-tenancy-architecture-decisions)
3. [Local Development Setup](#local-development-setup)
4. [Go Backend](#go-backend)
5. [Python ML Service](#python-ml-service)
6. [Celery Task Workers](#celery-task-workers)
7. [Python Automation Workers](#python-automation-workers)
8. [Apache Airflow (Platform Layer Only)](#apache-airflow-platform-layer-only)
9. [Frontend (Next.js)](#frontend-nextjs)
10. [Database Schema](#database-schema)
11. [Docker & Docker Compose](#docker--docker-compose)
12. [Kubernetes (EKS) + KEDA](#kubernetes-eks--keda)
13. [AWS Services](#aws-services)
14. [Prometheus & Grafana](#prometheus--grafana)
15. [ML/AI Subsystem](#mlai-subsystem)
16. [Portal Adapters](#portal-adapters)
17. [Configuration & Secrets](#configuration--secrets)
18. [CI/CD Pipeline](#cicd-pipeline)
19. [Testing Strategy](#testing-strategy)
20. [Coding Standards](#coding-standards)

---

## Repository Structure

```
applypilot/
├── backend/                    # Go API service
│   ├── cmd/api/main.go
│   ├── internal/
│   │   ├── auth/               # JWT auth + tenant middleware
│   │   ├── handlers/           # HTTP handlers
│   │   ├── models/             # DB models (GORM)
│   │   ├── repository/         # DB query layer (always scoped to tenant_id)
│   │   ├── service/            # Business logic
│   │   ├── middleware/         # Rate limiting (per user per portal), logging, CORS
│   │   └── tenant/             # Subscription plan enforcement, usage metering
│   ├── pkg/
│   │   ├── config/
│   │   ├── database/           # PostgreSQL (RLS) + Redis connections + PgBouncer
│   │   ├── s3/
│   │   └── metrics/            # Prometheus metrics with tenant labels
│   ├── migrations/             # SQL migrations (includes RLS policies)
│   ├── Dockerfile
│   └── go.mod
│
├── ml-service/                 # Python FastAPI — ML/AI engine (stateless)
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── score.py
│   │   │   ├── tailor.py
│   │   │   ├── coverletter.py
│   │   │   └── skills.py
│   │   ├── models/
│   │   └── schemas/
│   ├── requirements.txt
│   └── Dockerfile
│
├── workers/                    # Python — Celery tasks + browser automation
│   ├── tasks/
│   │   ├── celery_app.py       # Celery app config (Redis broker, fair routing)
│   │   ├── score_jobs.py       # Task: score jobs for a specific user
│   │   ├── tailor_resume.py    # Task: tailor resume for a specific job + user
│   │   ├── apply_job.py        # Task: apply to a specific job as a specific user
│   │   └── sync_status.py      # Task: sync application status for a user
│   ├── adapters/
│   │   ├── base.py             # Abstract adapter interface
│   │   ├── linkedin.py
│   │   ├── workday.py
│   │   ├── greenhouse.py
│   │   ├── lever.py
│   │   └── jobright.py
│   ├── scrapers/               # Platform-level scrapers (not per-user)
│   │   ├── linkedin_scraper.py
│   │   ├── workday_scraper.py
│   │   ├── jobright_scraper.py
│   │   └── indeed_scraper.py
│   ├── browser/
│   │   ├── session_manager.py  # Per-user browser session pool
│   │   └── fingerprint.py
│   ├── secrets.py              # AWS Secrets Manager helpers (fetch per-task)
│   ├── rate_limiter.py         # Per-user per-portal rate limiter (Redis-backed)
│   ├── requirements.txt
│   └── Dockerfile
│
├── airflow/                    # Airflow — PLATFORM cron jobs only
│   ├── dags/
│   │   ├── scrape_jobs_dag.py  # Scrape all portals → global job pool
│   │   ├── dedup_jobs_dag.py   # Deduplicate scraped jobs
│   │   ├── portal_health_dag.py
│   │   └── cleanup_dag.py
│   ├── plugins/
│   └── Dockerfile
│
├── frontend/                   # Next.js dashboard
│   ├── src/
│   │   ├── app/
│   │   │   ├── dashboard/
│   │   │   ├── jobs/
│   │   │   ├── applications/
│   │   │   ├── resume/
│   │   │   ├── settings/
│   │   │   └── billing/        # Subscription management
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
│
├── infra/
│   ├── k8s/
│   │   ├── backend/
│   │   ├── ml-service/
│   │   ├── workers/
│   │   │   ├── deployment.yaml
│   │   │   └── keda-scaledobject.yaml   # Auto-scale on Redis queue depth
│   │   ├── airflow/
│   │   └── monitoring/
│   └── helm/
│
├── monitoring/
│   ├── prometheus/prometheus.yml
│   └── grafana/dashboards/
│       ├── platform_overview.json
│       ├── per_tenant_funnel.json
│       ├── worker_queue_depth.json
│       └── portal_health.json
│
├── docker-compose.yml
├── .env.example
├── Makefile
├── README.md
└── dev.md
```

---

## Multi-Tenancy Architecture Decisions

This section explains the critical decisions that make the system scale from 1 to 10,000+ users.

### Decision 1: Airflow for platform jobs only, Celery for per-user jobs

**Problem:** Using Airflow for per-user tasks (score jobs, apply to jobs) breaks at scale.
- Airflow's scheduler has a fixed capacity; scheduling thousands of per-user DAG runs overwhelms it.
- Airflow DAGs are defined statically — dynamic per-user scheduling is awkward.

**Solution:**
- **Airflow** handles only platform-level cron jobs: scraping portals, deduplication, cleanup.
- **Celery** handles all per-user work: scoring, tailoring, applying. Tasks are dispatched dynamically by the Go API.

```
Airflow: scrape_jobs (every 2h) → writes to global jobs table
Go API: receives "apply" request → enqueues Celery task for that user
Celery: picks up task, fetches user credentials from Secrets Manager, executes
```

### Decision 2: Scraping is shared, per-user work is isolated

**Problem:** If 1000 users all search for "Software Engineer" on LinkedIn, you'd be making 1000x the requests.

**Solution:** Job scraping runs once at the platform level and writes to a shared `jobs` table. Each user then has their own `user_job_scores` table that stores their personalized score for each job. This means:
- Scraping cost = O(1) regardless of user count
- Scoring cost = O(users) — but lightweight and parallelizable

### Decision 3: PostgreSQL Row Level Security (RLS) for tenant isolation

Every query is automatically scoped to the current tenant — no chance of leaking data.

```sql
-- Enable RLS on every tenant-scoped table
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;

-- Policy: users can only see their own rows
CREATE POLICY tenant_isolation ON applications
    USING (user_id = current_setting('app.current_user_id')::uuid);

-- Go API sets this before every query:
SET app.current_user_id = '<user-uuid>';
```

No matter what SQL the application generates, it will only return rows for the current user.

### Decision 4: Browser sessions are strictly per-user, never shared

**Problem:** If two users share a browser session, portal bans hit both.

**Solution:** Each `apply_job` Celery task:
1. Fetches the user's credentials from AWS Secrets Manager (not env vars)
2. Launches or resumes a browser session keyed to `user_id:portal`
3. Sessions are stored in Redis with TTL, namespaced by user

```python
# workers/tasks/apply_job.py
async def apply_job(user_id: str, job_id: str, ...):
    creds = await secrets.get_credentials(user_id, portal="linkedin")
    session = await session_manager.get_or_create(user_id, portal="linkedin")
    adapter = LinkedInAdapter(session, creds)
    result = await adapter.apply(job, profile, resume_path)
```

### Decision 5: Per-user per-portal rate limiting in Redis

LinkedIn allows ~40 Easy Applies/day per account. This is tracked per user.

```
Redis key: rate_limit:{user_id}:{portal}:{date}
Value: current apply count
Expire: end of day
```

The Go API checks this before enqueuing a task. Workers also check before applying.

### Decision 6: Fair Celery queue routing

Without fair scheduling, one user who queues 500 jobs will block all other users.

```python
# celery_app.py — each user gets their own virtual queue
# Worker pool picks round-robin across all user queues
CELERY_ROUTES = {
    'tasks.apply_job': {'queue': 'apply:{user_id}'},
    'tasks.score_jobs': {'queue': 'score:{user_id}'},
}
# Per-user concurrency cap: max 2 concurrent apply tasks per user
CELERY_WORKER_MAX_TASKS_PER_USER = 2
```

### Decision 7: KEDA for auto-scaling Celery workers

Workers scale based on actual queue depth in Redis — no manual intervention.

```yaml
# infra/k8s/workers/keda-scaledobject.yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: celery-worker-scaler
spec:
  scaleTargetRef:
    name: celery-workers
  minReplicaCount: 2
  maxReplicaCount: 50
  triggers:
    - type: redis
      metadata:
        address: redis:6379
        listName: celery        # total queue depth
        listLength: "10"        # scale up if >10 tasks per worker
```

---

## Local Development Setup

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Go | 1.22+ | `brew install go` |
| Python | 3.11+ | `brew install python@3.11` |
| Node.js | 20+ | `brew install node` |
| Docker Desktop | latest | docker.com |
| kubectl | 1.29+ | `brew install kubectl` |
| helm | 3.x | `brew install helm` |
| awscli | 2.x | `brew install awscli` |

### First-time setup

```bash
cp .env.example .env
# Fill in API keys and portal credentials

docker compose up -d postgres redis airflow prometheus grafana

make migrate-up     # Runs SQL migrations including RLS policies

# Terminal 1: Go API
cd backend && air

# Terminal 2: ML service
cd ml-service && uvicorn app.main:app --reload --port 8001

# Terminal 3: Celery workers
cd workers && celery -A tasks.celery_app worker --concurrency=4 --loglevel=info

# Terminal 4: Frontend
cd frontend && npm install && npm run dev
```

### Makefile targets

```makefile
make dev            # Start docker compose services
make stop           # Stop services
make migrate-up     # Run pending DB migrations
make migrate-down   # Rollback last migration
make test           # Run all tests
make lint           # golangci-lint + ruff
make build          # Build all Docker images
make push           # Push to ECR
make deploy         # kubectl apply
make worker-shell   # Open shell in a worker container
```

---

## Go Backend

### Framework: Gin + GORM + golang-migrate

### Key Dependencies
- `gin-gonic/gin` — HTTP router
- `go-gorm/gorm` + `gorm/driver/postgres` — ORM
- `golang-migrate/migrate` — SQL migrations
- `go-redis/redis/v9` — Redis client
- `aws/aws-sdk-go-v2` — S3 + Secrets Manager
- `prometheus/client_golang` — metrics
- `golang-jwt/jwt` — JWT auth
- `jackc/pgx` — PostgreSQL driver (faster than lib/pq)

### API Endpoints

```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh

GET    /api/v1/jobs                       # tenant-scoped job feed with personal scores
GET    /api/v1/jobs/:id
PATCH  /api/v1/jobs/:id/status            # approve / skip / blacklist

GET    /api/v1/applications
GET    /api/v1/applications/:id
POST   /api/v1/applications/:id/retry

GET    /api/v1/resume
POST   /api/v1/resume                     # upload → store in S3 under tenant namespace
GET    /api/v1/resume/:id/download
# POST /api/v1/resume/tailor             # DEFERRED — Phase 7 (paid tier)

GET    /api/v1/profile
PUT    /api/v1/profile

GET    /api/v1/stats                      # tenant dashboard metrics
GET    /api/v1/billing                    # subscription plan + usage

GET    /metrics                           # Prometheus scrape endpoint
```

### Tenant Middleware (Go)

Every authenticated request sets the PostgreSQL session variable for RLS:

```go
// internal/middleware/tenant.go
func TenantMiddleware(db *gorm.DB) gin.HandlerFunc {
    return func(c *gin.Context) {
        userID := c.GetString("user_id")  // set by JWT middleware
        db.Exec("SET app.current_user_id = ?", userID)
        c.Next()
    }
}
```

### Per-User Per-Portal Rate Limiter (Go)

```go
// internal/middleware/rate_limit.go
func PortalRateLimit(rdb *redis.Client) gin.HandlerFunc {
    return func(c *gin.Context) {
        userID := c.GetString("user_id")
        portal := c.Param("portal")
        key := fmt.Sprintf("rate_limit:%s:%s:%s", userID, portal, today())
        count, _ := rdb.Incr(ctx, key).Result()
        rdb.ExpireAt(ctx, key, endOfDay())
        limit := planLimit(c.GetString("plan"), portal)
        if count > int64(limit) {
            c.AbortWithStatusJSON(429, gin.H{"error": "daily apply limit reached"})
            return
        }
        c.Next()
    }
}
```

### Environment Variables (backend)

```env
PORT=8080
DATABASE_URL=postgres://user:pass@localhost:5432/jobassistant
REDIS_URL=redis://localhost:6379
ML_SERVICE_URL=http://localhost:8001
AWS_REGION=us-east-1
S3_BUCKET=applypilot-docs
JWT_SECRET=changeme
PGBOUNCER_URL=postgres://user:pass@pgbouncer:5432/jobassistant  # prod only
```

---

## Python ML Service

### Framework: FastAPI + Uvicorn (stateless — scale to N replicas freely)

### Models Used (Phase 1–4 scope)

| Task | Model | Library |
|------|-------|---------|
| Job-resume similarity scoring | `all-MiniLM-L6-v2` | sentence-transformers |
| Resume keyword extraction | `en_core_web_sm` | spaCy |
| JD skill extraction | `jjzha/jobbert-base-cased` | transformers |
| ~~Resume bullet rewriting~~ | ~~GPT-4o / Claude 3.5~~ | DEFERRED Phase 7 |
| ~~Cover letter generation~~ | ~~GPT-4o / Claude 3.5~~ | DEFERRED Phase 7 |

### Key Endpoints (active)

```
POST /score          # { resume_text, jd_text } → { score, matched_skills, missing_skills }
POST /extract-skills # { text } → { skills: [...] }

# DEFERRED — Phase 7 (paid tier):
# POST /tailor       # { resume_text, jd_text } → { tailored_resume, changes_made }
# POST /cover-letter # { resume_text, jd_text, company, role } → { cover_letter }
# POST /gap-analysis # { resume_text, target_role } → { gaps, recommendations }
```

The ML service is intentionally stateless. It receives all context in the request body. No user sessions, no DB access. This lets it scale independently of everything else.

---

## Celery Task Workers

### Framework: Celery 5.x + Redis broker

Celery handles all **per-user asynchronous work**. The Go API enqueues tasks; workers execute them.

### Task Definitions

```python
# workers/tasks/score_jobs.py
@app.task(bind=True, queue='score:{user_id}', max_retries=3)
def score_jobs_for_user(self, user_id: str, job_ids: list[str]):
    """Score a batch of new jobs against a user's profile."""
    profile = db.get_profile(user_id)
    resume = db.get_default_resume(user_id)
    for job_id in job_ids:
        job = db.get_job(job_id)
        score = ml_client.score(resume.text, job.description)
        db.upsert_user_job_score(user_id, job_id, score)

# workers/tasks/apply_job.py
@app.task(bind=True, queue='apply:{user_id}', max_retries=2)
def apply_to_job(self, user_id: str, job_id: str, resume_id: str):
    """Apply to a single job on behalf of a user (standard resume, no cover letter)."""
    # Always fetch credentials fresh from Secrets Manager — never from env
    creds = secrets.get(user_id, job.portal)
    rate_limiter.check_or_raise(user_id, job.portal)

    resume_path = s3.download_resume(resume_id)   # standard resume, no tailoring

    session = session_manager.get_or_create(user_id, job.portal)
    adapter = AdapterFactory.get(job.portal, session, creds)
    result = adapter.apply(job, profile, resume_path)   # no cover_letter_path

    db.create_application(user_id, job_id, result)
    rate_limiter.increment(user_id, job.portal)
    # DEFERRED: tailored_resume, cover_letter — Phase 7
```

### Fair Queue Routing

```python
# workers/tasks/celery_app.py
app = Celery('applypilot', broker='redis://localhost:6379/0')

app.conf.task_routes = {
    'tasks.apply_to_job':        {'queue': lambda args, **_: f"apply:{args[0]}"},
    'tasks.score_jobs_for_user': {'queue': lambda args, **_: f"score:{args[0]}"},
    # 'tasks.tailor_resume'      DEFERRED — Phase 7
}

# Workers listen on all queues but are limited per-user
# Start with: celery worker -Q apply:* -c 10
```

---

## Python Automation Workers

### Framework: Playwright (async)

### Adapter Interface

Every portal adapter implements:

```python
class BaseAdapter:
    async def login(self, credentials: Credentials) -> bool
    async def apply(self, job: JobListing, profile: UserProfile,
                    resume_path: str) -> ApplicationResult  # no cover_letter — Phase 7
    async def check_status(self, application_id: str) -> ApplicationStatus
    async def close(self) -> None
    # Note: search_jobs is NOT on adapters — scraping is platform-level
```

### Session Management (Per-User)

```python
# workers/browser/session_manager.py
class SessionManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.playwright = None

    async def get_or_create(self, user_id: str, portal: str) -> BrowserContext:
        session_key = f"session:{user_id}:{portal}"
        cookies = self.redis.get(session_key)  # restore saved cookies

        context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=f"/tmp/sessions/{user_id}/{portal}",
            headless=True,
        )
        if cookies:
            await context.add_cookies(json.loads(cookies))
        return context

    async def save(self, user_id: str, portal: str, context: BrowserContext):
        cookies = await context.cookies()
        self.redis.setex(
            f"session:{user_id}:{portal}",
            43200,               # 12 hour TTL
            json.dumps(cookies)
        )
```

### Anti-detection
- Randomized mouse movements, typing delays (playwright-stealth)
- Rotating user agents and viewport sizes per session
- Exponential backoff on 429 / CAPTCHA detection
- Human-review queue for unresolvable CAPTCHAs

---

## Apache Airflow (Platform Layer Only)

**Airflow is only for platform-wide cron jobs. Never for per-user work.**

### Version: Airflow 2.9+
### Executor: KubernetesExecutor (prod) / LocalExecutor (dev)

### DAG Schedule

| DAG | Schedule | Purpose |
|-----|----------|---------|
| `scrape_jobs_dag` | `0 */2 * * *` | Scrape all portals → global job pool |
| `dedup_jobs_dag` | `30 */2 * * *` | Deduplicate scraped jobs by fingerprint |
| `portal_health_dag` | `0 * * * *` | Check portal availability, alert on failures |
| `cleanup_dag` | `0 2 * * 0` | Archive stale jobs, expired sessions |

### What Airflow does NOT do
- Score jobs for users → **Celery task** triggered by Go API
- Apply to jobs → **Celery task** triggered by Go API
- Tailor resumes → **Celery task** triggered by Go API
- Sync application statuses → **Celery beat** scheduled task

This separation means Airflow stays lightweight regardless of user count.

---

## Frontend (Next.js)

### Version: Next.js 14 (App Router)
### Styling: Tailwind CSS + shadcn/ui
### State: Zustand + TanStack Query
### Charts: Recharts

### Pages

| Route | Description |
|-------|-------------|
| `/dashboard` | Overview: jobs found, applied, interviews, queue status |
| `/jobs` | Job feed with personal scores, approve/skip controls |
| `/applications` | Application history + status timeline |
| `/resume` | Upload, manage, preview tailored resume versions |
| `/settings` | Job prefs, portal credentials, auto-apply rules |
| `/analytics` | Funnel, response rates, portal effectiveness |
| `/billing` | Subscription plan, usage meters, upgrade |

---

## Database Schema

### PostgreSQL — Full Multi-Tenant Schema

```sql
-- ─────────────────────────────────────────────
-- PLATFORM TABLES (shared across all users)
-- ─────────────────────────────────────────────

-- Global job pool — scraped once, shared by all users
CREATE TABLE jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portal          TEXT NOT NULL,
    external_id     TEXT NOT NULL,
    title           TEXT NOT NULL,
    company         TEXT NOT NULL,
    location        TEXT,
    remote          BOOLEAN,
    description     TEXT,
    apply_url       TEXT,
    salary_min      INTEGER,
    salary_max      INTEGER,
    posted_at       TIMESTAMPTZ,
    scraped_at      TIMESTAMPTZ DEFAULT NOW(),
    fingerprint             TEXT UNIQUE,  -- within-portal dedup hash (portal + external_id)
    cross_portal_fingerprint TEXT,        -- cross-portal dedup: hash(lower(company) + lower(title) + lower(location) + date_trunc('day', posted_at))
    raw_data        JSONB
    -- NOTE: No user_id here. This is platform-level.
    -- cross_portal_fingerprint prevents applying to the same role twice from LinkedIn + Greenhouse + Indeed
);
CREATE INDEX idx_jobs_portal ON jobs(portal);
CREATE INDEX idx_jobs_scraped ON jobs(scraped_at DESC);
CREATE INDEX idx_jobs_cross_portal ON jobs(cross_portal_fingerprint);

-- ─────────────────────────────────────────────
-- TENANT TABLES (row-level security applied)
-- ─────────────────────────────────────────────

-- Users + subscription plans
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE NOT NULL,
    password    TEXT NOT NULL,
    plan        TEXT NOT NULL DEFAULT 'free',  -- free | pro | team
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- User profiles
CREATE TABLE profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES users(id) ON DELETE CASCADE,
    full_name           TEXT,
    phone               TEXT,
    location            TEXT,
    linkedin_url        TEXT,
    github_url          TEXT,
    portfolio_url       TEXT,
    target_roles        TEXT[],
    target_locations    TEXT[],
    min_salary          INTEGER,
    skills              TEXT[],
    auto_apply_config   JSONB,           -- thresholds, blacklists, max per day
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Per-user personalized scores for global jobs
-- This is what shows in each user's job feed
CREATE TABLE user_job_scores (
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    job_id      UUID REFERENCES jobs(id) ON DELETE CASCADE,
    score       FLOAT NOT NULL,
    status      TEXT DEFAULT 'new',      -- new | approved | skipped | blacklisted
    scored_at   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, job_id)
);
CREATE INDEX idx_user_job_scores_user ON user_job_scores(user_id, score DESC);

-- Resume versions
CREATE TABLE resumes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    s3_key      TEXT NOT NULL,           -- s3://bucket/resumes/{user_id}/{id}/base.pdf
    is_default  BOOLEAN DEFAULT false,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Applications
CREATE TABLE applications (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID REFERENCES users(id) ON DELETE CASCADE,
    job_id                  UUID REFERENCES jobs(id),
    resume_id               UUID REFERENCES resumes(id),
    -- tailored_resume_s3_key TEXT,   DEFERRED — Phase 7
    -- cover_letter_s3_key    TEXT,   DEFERRED — Phase 7
    status                  TEXT DEFAULT 'queued',
    applied_at              TIMESTAMPTZ,
    last_updated            TIMESTAMPTZ DEFAULT NOW(),
    notes                   TEXT,
    error_message           TEXT
);
CREATE INDEX idx_applications_user ON applications(user_id);
CREATE INDEX idx_applications_status ON applications(user_id, status);

-- Portal credentials (reference to Secrets Manager ARN)
CREATE TABLE portal_credentials (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    portal      TEXT NOT NULL,
    username    TEXT NOT NULL,
    secret_arn  TEXT NOT NULL,           -- AWS Secrets Manager ARN
    is_active   BOOLEAN DEFAULT true,
    UNIQUE (user_id, portal)
);

-- Usage metering (for plan enforcement)
CREATE TABLE usage_daily (
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    date        DATE NOT NULL,
    portal      TEXT NOT NULL,
    applies     INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, date, portal)
);

-- ─────────────────────────────────────────────
-- ROW LEVEL SECURITY
-- ─────────────────────────────────────────────

-- Enable RLS on all tenant tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_job_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_daily ENABLE ROW LEVEL SECURITY;

-- Policy template (repeat for each table)
CREATE POLICY tenant_isolation ON applications
    USING (user_id = current_setting('app.current_user_id')::uuid);

-- Go backend sets this before every query:
-- SET LOCAL app.current_user_id = '<uuid>';
```

### Subscription Plan Limits

```sql
-- Enforced in Go middleware, stored as config
-- free:  10 applies/day, LinkedIn only, no ML tailoring
-- pro:   50 applies/day, all portals, full ML
-- team:  200 applies/day, all portals, full ML, team analytics
```

---

## Docker & Docker Compose

### docker-compose.yml (local dev)

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: jobassistant
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  backend:
    build: ./backend
    ports: ["8080:8080"]
    env_file: .env
    depends_on: [postgres, redis]

  ml-service:
    build: ./ml-service
    ports: ["8001:8001"]
    env_file: .env
    volumes: [./models:/models]

  celery-worker:
    build: ./workers
    command: celery -A tasks.celery_app worker --concurrency=4 --loglevel=info
    env_file: .env
    depends_on: [redis, postgres]
    volumes: [./workers:/app]     # hot reload in dev

  celery-beat:
    build: ./workers
    command: celery -A tasks.celery_app beat --loglevel=info
    env_file: .env
    depends_on: [redis]

  airflow:
    image: apache/airflow:2.9.0
    ports: ["8082:8080"]
    env_file: .env
    volumes: [./airflow/dags:/opt/airflow/dags]
    depends_on: [postgres, redis]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    env_file: .env

  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes: [./monitoring/prometheus:/etc/prometheus]

  grafana:
    image: grafana/grafana:latest
    ports: ["3001:3000"]
    volumes: [./monitoring/grafana:/var/lib/grafana]

volumes:
  pgdata:
```

---

## Kubernetes (EKS) + KEDA

### Cluster Layout

```
Namespace: applypilot
  Deployments:
    - backend          (HPA: min=2, max=10, CPU 70%)
    - ml-service       (HPA: min=1, max=8, CPU 70%)
    - frontend         (HPA: min=2, max=6)
    - celery-workers   (KEDA: scale on Redis queue depth)
    - celery-beat      (1 replica, no scaling)
    - pgbouncer        (2 replicas)

Namespace: airflow
    - airflow-webserver  (1 replica)
    - airflow-scheduler  (1 replica)
    - airflow workers    (KubernetesExecutor — ephemeral)

Namespace: monitoring
    - prometheus   (1 replica + PVC)
    - grafana      (1 replica + PVC)
```

### KEDA ScaledObject for Celery workers

```yaml
# infra/k8s/workers/keda-scaledobject.yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: celery-worker-scaler
  namespace: applypilot
spec:
  scaleTargetRef:
    name: celery-workers
  minReplicaCount: 2
  maxReplicaCount: 50
  cooldownPeriod: 120
  triggers:
    - type: redis
      metadata:
        address: redis.applypilot.svc.cluster.local:6379
        listName: celery
        listLength: "10"    # 1 new worker per 10 queued tasks
```

### Resource Budgets (cost-conscious)

```yaml
backend:
  requests: { cpu: 100m, memory: 128Mi }
  limits:   { cpu: 500m, memory: 512Mi }

ml-service:
  requests: { cpu: 500m, memory: 1Gi }
  limits:   { cpu: 2,    memory: 4Gi }

celery-worker:
  requests: { cpu: 200m, memory: 512Mi }
  limits:   { cpu: 1,    memory: 2Gi }
```

### Node Groups (cost optimization)

- **System pool**: 2x t3.medium (always on — API, Airflow scheduler, monitoring)
- **Worker pool**: Spot instances, t3.large, auto-scaled by KEDA (Celery workers, ML pods)
- Using spot saves ~70% on worker compute

---

## AWS Services

### Services Used

| Service | Purpose | Notes |
|---------|---------|-------|
| EKS | Kubernetes cluster | Control plane + EC2 node groups |
| ECR | Container registry | One repo per service |
| S3 | Resumes, cover letters, JD archives | Namespaced by `user_id` |
| Secrets Manager | Portal credentials per user, API keys | `$0.40/secret/mo` |
| ALB | HTTPS ingress | One ALB shared across services |
| Route53 | DNS | Optional |

### What we avoid
- RDS managed PostgreSQL (run in k8s, saves ~$50/mo)
- ElastiCache (run Redis in k8s)
- SQS (Redis handles our queue)
- Lambda (Celery + Airflow handle all scheduling)

### S3 Bucket Structure

```
s3://applypilot-docs/
├── resumes/
│   └── {user_id}/
│       ├── {resume_id}/base.pdf
│       └── {resume_id}/tailored_{job_id}.pdf
├── cover-letters/
│   └── {user_id}/{application_id}.pdf
└── jd-archives/
    └── {portal}/{year}/{month}/{job_id}.json
```

---

## Prometheus & Grafana

### Metrics Exposed (Go API `/metrics`)

```
# Platform metrics (no user_id — aggregate only)
job_assistant_jobs_scraped_total{portal}
job_assistant_jobs_in_pool

# Per-user work metrics (tenant label = hashed user_id for privacy)
job_assistant_applications_total{status, portal, plan}
job_assistant_apply_duration_seconds{portal}
job_assistant_queue_depth{queue_type}          # apply, score, tailor

# API metrics
http_requests_total{method, path, status, plan}
http_request_duration_seconds{method, path}

# Worker metrics (from Celery)
celery_tasks_total{task_name, state}
celery_task_duration_seconds{task_name}
```

### Grafana Dashboards

1. **Platform Overview** — total users, jobs scraped/day, total applications/day
2. **Job Funnel** — scraped → scored → approved → applied → response rates
3. **Worker Queue Depth** — queue depth over time, worker pod count, task latency
4. **Portal Health** — success rate per portal, last successful scrape, error rates
5. **Per-Tenant Drill-Down** — search by user to see their personal funnel (admin only)
6. **Subscription Metrics** — plan distribution, usage vs limits, upgrade triggers

---

## ML/AI Subsystem

> **Current scope (Phase 1–4): Job scoring only.**
> Resume tailoring pipeline and cover letter generation are deferred to Phase 7 (paid tier).

### Job Scoring Pipeline (active)

```
Input: { resume_text, job_description }
  │
  ▼
1. Extract JD skills/keywords (spaCy + JobBERT)
  │
  ▼
2. Cosine similarity: resume vs JD (sentence-transformers all-MiniLM-L6-v2)
  │
  ▼
3. Combine weighted score (see formula below)
  │
  ▼
Output: { score: 0.0-1.0, matched_skills, missing_skills }
```

### Job Scoring Formula

```python
score = (
    0.40 * skill_match_score +      # sentence-transformer cosine similarity
    0.20 * title_match_score +       # role title fuzzy match
    0.15 * location_preference +     # remote / target city match
    0.10 * salary_fit +              # salary range overlap
    0.10 * company_size_fit +        # user preference match
    0.05 * recency_score             # jobs < 3 days old scored higher
)
```

### Auto-apply Config (per user, stored in profiles.auto_apply_config)

```json
{
  "auto_apply_threshold": 0.75,
  "require_review_below": 0.60,
  "blacklisted_companies": [],
  "blacklisted_keywords": ["commission only", "unpaid"],
  "max_applies_per_day": 30,
  "preferred_portals": ["linkedin", "greenhouse"],
  "skip_if_already_applied": true
}
```

---

## Portal Adapters

### Adding a New Portal

1. Create `workers/adapters/newportal.py` implementing `BaseAdapter`
2. Create `workers/scrapers/newportal_scraper.py` (platform-level, not per-user)
3. Add portal constant to Go `internal/models/job.go`
4. Add Secrets Manager path convention for this portal
5. Add portal entry to Airflow `scrape_jobs_dag.py`
6. Write integration tests

### LinkedIn Notes
- Easy Apply: form submission detected by `<button data-control-name="submit_unify">`
- Standard apply: opens external URL — captured and routed to the appropriate ATS adapter
- Cap: 40 Easy Applies/day per account; we enforce 30 with buffer
- Session cookies stored in Redis (TTL 12h)

### Workday Notes
- No public API — full browser automation required
- Unique subdomain per company: `{company}.wd1.myworkdayjobs.com`
- Multi-step forms: personal info → resume upload → questionnaire → review
- Cache questionnaire answers per `(user_id, company_workday_domain)` in Redis

---

## Configuration & Secrets

### .env.example

```env
# App
PORT=8080
ENV=development
LOG_LEVEL=debug

# Database
DATABASE_URL=postgres://user:pass@localhost:5432/jobassistant

# Redis
REDIS_URL=redis://localhost:6379

# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
S3_BUCKET=applypilot-docs

# Services
ML_SERVICE_URL=http://localhost:8001

# Auth
JWT_SECRET=dev-secret-changeme
JWT_EXPIRY_HOURS=24

# AI APIs
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Workers
BROWSER_HEADLESS=true
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### Secrets Manager Paths (production)

```
/applypilot/prod/db-url
/applypilot/prod/jwt-secret
/applypilot/prod/openai-key
/applypilot/prod/anthropic-key
/applypilot/users/{user_id}/linkedin
/applypilot/users/{user_id}/workday
/applypilot/users/{user_id}/jobright
```

Portal credentials are **never in environment variables in production**. Workers call Secrets Manager at task start time with the user's specific ARN from the `portal_credentials` table.

---

## CI/CD Pipeline

### GitHub Actions Workflows

```
.github/workflows/
├── ci.yml        # On PR: lint + test all services
├── build.yml     # On merge to main: build + push to ECR
└── deploy.yml    # On git tag: kubectl apply to EKS
```

### Pipeline Stages

```
PR opened
  ├── go test ./... + golangci-lint
  ├── pytest workers/ ml-service/
  ├── npm run test (frontend)
  └── docker build --no-push (all services)

Merge to main
  ├── docker build + push to ECR (tagged :sha + :latest)
  └── helm upgrade → staging

Git tag v1.x.x
  ├── helm upgrade → production
  ├── kubectl rollout status
  └── smoke tests against prod
```

---

## Testing Strategy

### Go Backend
- Unit: service layer with mocked repos
- Integration: handler tests with real DB via testcontainers-go (RLS policies included)
- Run: `go test ./... -v`

### Python ML Service
- Unit: model outputs with sample resumes/JDs
- Run: `pytest ml-service/tests/`

### Celery Workers
- Unit: tasks with mocked DB, mocked adapter
- Integration: full flow against staging portal accounts
- Mock mode in CI using Playwright record/replay
- Run: `pytest workers/tests/`

### Frontend
- Component: React Testing Library
- E2E: Playwright against docker compose stack
- Run: `npm run test` / `npm run e2e`

---

## Coding Standards

### Go
- `gofmt` + `golangci-lint` enforced in CI
- No global state; dependency injection via constructors
- All DB queries go through repository layer
- Repository functions always receive `userID` explicitly (belt + suspenders alongside RLS)

### Python
- `ruff` for linting + formatting
- Type hints required on all function signatures
- Pydantic for all API schemas
- Async-first in workers and ML service
- Never log credential values, even at DEBUG level

### Git
- Branch: `feat/`, `fix/`, `chore/`, `docs/`
- Commit: `feat(workers): add Greenhouse adapter`
- PRs: passing CI + 1 review, squash merge to main

---

## Scale Reference

| Users | Key bottleneck | Solution |
|-------|---------------|---------|
| 1–10 | Nothing | Docker Compose is enough |
| 10–100 | DB connections | Add PgBouncer |
| 100–1,000 | Worker capacity | KEDA auto-scale Celery workers |
| 1,000–10,000 | DB write throughput | Read replica for analytics; connection pooling |
| 10,000+ | DB at primary limits | Citus sharding by tenant_id, or CockroachDB |
| 100,000+ | Multi-region latency | Multi-region EKS, S3 replication, global CDN |
