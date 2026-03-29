-- Ensure gen_random_uuid() is available on older PostgreSQL (<13)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Add is_active column to users if not already present (from migration 002)
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active      BOOLEAN DEFAULT true;
ALTER TABLE users ADD COLUMN IF NOT EXISTS mobile_number  TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS address        TEXT;

-- Index on password_reset_tokens for faster lookups
CREATE INDEX IF NOT EXISTS idx_prt_token    ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_prt_user_id  ON password_reset_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_prt_expires  ON password_reset_tokens(expires_at) WHERE used = false;
