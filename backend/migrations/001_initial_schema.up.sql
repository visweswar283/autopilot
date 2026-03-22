-- ─────────────────────────────────────────────
-- PLATFORM TABLES (shared across all users)
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS jobs (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portal                   TEXT NOT NULL,
    external_id              TEXT NOT NULL,
    title                    TEXT NOT NULL,
    company                  TEXT NOT NULL,
    location                 TEXT,
    remote                   BOOLEAN DEFAULT false,
    description              TEXT,
    apply_url                TEXT,
    salary_min               INTEGER,
    salary_max               INTEGER,
    posted_at                TIMESTAMPTZ,
    scraped_at               TIMESTAMPTZ DEFAULT NOW(),
    fingerprint              TEXT UNIQUE,
    cross_portal_fingerprint TEXT,
    raw_data                 JSONB
);

CREATE INDEX IF NOT EXISTS idx_jobs_portal       ON jobs(portal);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped      ON jobs(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_cross_portal ON jobs(cross_portal_fingerprint);

-- ─────────────────────────────────────────────
-- TENANT TABLES
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email      TEXT UNIQUE NOT NULL,
    password   TEXT NOT NULL,
    plan       TEXT NOT NULL DEFAULT 'free',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS profiles (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID REFERENCES users(id) ON DELETE CASCADE,
    full_name         TEXT,
    phone             TEXT,
    location          TEXT,
    linkedin_url      TEXT,
    github_url        TEXT,
    portfolio_url     TEXT,
    target_roles      TEXT[],
    target_locations  TEXT[],
    min_salary        INTEGER,
    skills            TEXT[],
    auto_apply_config JSONB,
    updated_at        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id)
);

CREATE TABLE IF NOT EXISTS resumes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    s3_key      TEXT NOT NULL,
    is_default  BOOLEAN DEFAULT false,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resumes_user ON resumes(user_id);

CREATE TABLE IF NOT EXISTS user_job_scores (
    user_id   UUID REFERENCES users(id) ON DELETE CASCADE,
    job_id    UUID REFERENCES jobs(id)  ON DELETE CASCADE,
    score     FLOAT NOT NULL,
    status    TEXT DEFAULT 'new',
    scored_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_user_job_scores_user ON user_job_scores(user_id, score DESC);

CREATE TABLE IF NOT EXISTS applications (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID REFERENCES users(id)   ON DELETE CASCADE,
    job_id        UUID REFERENCES jobs(id),
    resume_id     UUID REFERENCES resumes(id),
    status        TEXT DEFAULT 'queued',
    applied_at    TIMESTAMPTZ,
    last_updated  TIMESTAMPTZ DEFAULT NOW(),
    notes         TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_applications_user   ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(user_id, status);

CREATE TABLE IF NOT EXISTS portal_credentials (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    portal     TEXT NOT NULL,
    username   TEXT NOT NULL,
    secret_arn TEXT NOT NULL,
    is_active  BOOLEAN DEFAULT true,
    UNIQUE (user_id, portal)
);

CREATE TABLE IF NOT EXISTS usage_daily (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    date    DATE NOT NULL,
    portal  TEXT NOT NULL,
    applies INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, date, portal)
);

-- ─────────────────────────────────────────────
-- ROW LEVEL SECURITY
-- ─────────────────────────────────────────────

ALTER TABLE profiles           ENABLE ROW LEVEL SECURITY;
ALTER TABLE resumes            ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_job_scores    ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications       ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_daily        ENABLE ROW LEVEL SECURITY;

-- RLS Policies — Go API sets app.current_user_id before every query
CREATE POLICY tenant_isolation ON profiles
    USING (user_id = current_setting('app.current_user_id')::uuid);

CREATE POLICY tenant_isolation ON resumes
    USING (user_id = current_setting('app.current_user_id')::uuid);

CREATE POLICY tenant_isolation ON user_job_scores
    USING (user_id = current_setting('app.current_user_id')::uuid);

CREATE POLICY tenant_isolation ON applications
    USING (user_id = current_setting('app.current_user_id')::uuid);

CREATE POLICY tenant_isolation ON portal_credentials
    USING (user_id = current_setting('app.current_user_id')::uuid);

CREATE POLICY tenant_isolation ON usage_daily
    USING (user_id = current_setting('app.current_user_id')::uuid);
