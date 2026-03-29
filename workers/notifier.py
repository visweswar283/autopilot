"""
Notification system — email + webhook alerts for apply bot events.

Supports:
  - Email via SendGrid (SENDGRID_API_KEY) or SMTP fallback
  - Webhook POST to user-configured URL
  - Daily digest summary (called by scheduler)
  - Redis pub/sub event publishing (consumed by Go SSE endpoint)
"""
import json
import os
import redis
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from loguru import logger

# --- Config ---
SENDGRID_API_KEY   = os.getenv("SENDGRID_API_KEY", "")
SMTP_HOST          = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT          = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER          = os.getenv("SMTP_USER", "")
SMTP_PASSWORD      = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL         = os.getenv("FROM_EMAIL", "noreply@applypilot.io")
REDIS_URL          = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Redis channel for SSE real-time events
EVENTS_CHANNEL = "apply:events"


def _redis() -> redis.Redis:
    return redis.from_url(REDIS_URL, decode_responses=True)


# ---------------------------------------------------------------------------
# Core notification dispatcher
# ---------------------------------------------------------------------------

async def notify_application(user_id: str, job: dict, status: str):
    """
    Fire-and-forget notification when bot applies to a job.
    Publishes to Redis (SSE), sends email if configured.
    """
    event = {
        "type":    "application",
        "user_id": user_id,
        "status":  status,
        "job": {
            "id":      job.get("id"),
            "title":   job.get("title"),
            "company": job.get("company"),
            "portal":  job.get("portal"),
        },
        "ts": time.time(),
    }

    # Publish to Redis for SSE endpoint
    _publish_event(event)

    # Email notification (non-blocking — errors don't fail the apply)
    try:
        user_email = await _get_user_email(user_id)
        if user_email:
            _send_application_email(user_email, job, status)
    except Exception as e:
        logger.warning(f"Email notification failed for user {user_id}: {e}")

    # Webhook (non-blocking)
    try:
        webhook_url = await _get_user_webhook(user_id)
        if webhook_url:
            await _post_webhook(webhook_url, event)
    except Exception as e:
        logger.warning(f"Webhook notification failed for user {user_id}: {e}")


async def send_daily_digest(user_id: str, user_email: str, stats: dict):
    """
    Send a daily summary email: how many jobs were applied, failed, etc.
    Called by the scheduler once per day.
    """
    applied = stats.get("applied", 0)
    failed  = stats.get("failed",  0)
    captcha = stats.get("captcha", 0)
    total   = stats.get("total",   0)

    subject = f"ApplyPilot Daily Digest — {applied} applications sent today"
    body    = f"""
<html><body style="font-family:sans-serif;max-width:600px;margin:auto">
  <h2 style="color:#6366f1">ApplyPilot Daily Summary</h2>
  <p>Here's what the bot did for you today:</p>
  <table style="width:100%;border-collapse:collapse">
    <tr><td style="padding:8px;background:#f0fdf4;border-radius:4px"><b>✅ Applied</b></td>
        <td style="padding:8px;font-size:24px;font-weight:bold;color:#16a34a">{applied}</td></tr>
    <tr><td style="padding:8px"><b>❌ Failed</b></td>
        <td style="padding:8px;color:#dc2626">{failed}</td></tr>
    <tr><td style="padding:8px"><b>🤖 CAPTCHA hits</b></td>
        <td style="padding:8px;color:#d97706">{captcha}</td></tr>
    <tr><td style="padding:8px;background:#f8fafc"><b>Total processed</b></td>
        <td style="padding:8px">{total}</td></tr>
  </table>
  <p style="margin-top:24px;color:#64748b;font-size:12px">
    You're receiving this because auto-apply is enabled on your account.
    <a href="https://applypilot.io/settings">Manage preferences</a>
  </p>
</body></html>
"""
    _send_email(user_email, subject, body, html=True)


# ---------------------------------------------------------------------------
# Redis pub/sub (consumed by Go SSE handler)
# ---------------------------------------------------------------------------

def _publish_event(event: dict):
    try:
        r = _redis()
        r.publish(EVENTS_CHANNEL, json.dumps(event))
    except Exception as e:
        logger.warning(f"Redis publish failed: {e}")


# ---------------------------------------------------------------------------
# Email sending
# ---------------------------------------------------------------------------

def _send_application_email(to_email: str, job: dict, status: str):
    icon    = "✅" if status == "applied" else "❌"
    subject = f"{icon} Bot applied to {job.get('title')} @ {job.get('company')}"
    body    = f"""
<html><body style="font-family:sans-serif;max-width:600px;margin:auto">
  <h2 style="color:#6366f1">New Application — {icon}</h2>
  <p>Your ApplyPilot bot just submitted an application:</p>
  <table style="width:100%;border-collapse:collapse;margin-top:12px">
    <tr><td style="padding:8px;color:#64748b">Position</td>
        <td style="padding:8px;font-weight:bold">{job.get('title', '—')}</td></tr>
    <tr style="background:#f8fafc">
        <td style="padding:8px;color:#64748b">Company</td>
        <td style="padding:8px;font-weight:bold">{job.get('company', '—')}</td></tr>
    <tr><td style="padding:8px;color:#64748b">Portal</td>
        <td style="padding:8px">{job.get('portal', '—').title()}</td></tr>
    <tr style="background:#f8fafc">
        <td style="padding:8px;color:#64748b">Status</td>
        <td style="padding:8px;color:{'#16a34a' if status == 'applied' else '#dc2626'}">{status.upper()}</td></tr>
  </table>
  <p style="margin-top:24px">
    <a href="https://applypilot.io/applications"
       style="background:#6366f1;color:white;padding:10px 20px;border-radius:6px;text-decoration:none">
      View all applications →
    </a>
  </p>
  <p style="margin-top:24px;color:#64748b;font-size:12px">ApplyPilot • automated job applications</p>
</body></html>
"""
    _send_email(to_email, subject, body, html=True)


def _send_email(to_email: str, subject: str, body: str, html: bool = False):
    """Send via SendGrid HTTP API or SMTP fallback."""
    if SENDGRID_API_KEY:
        _send_via_sendgrid(to_email, subject, body, html)
    elif SMTP_USER and SMTP_PASSWORD:
        _send_via_smtp(to_email, subject, body, html)
    else:
        logger.debug(f"[DRY RUN] Would send email to {to_email}: {subject}")


def _send_via_sendgrid(to_email: str, subject: str, body: str, html: bool):
    import httpx
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from":    {"email": FROM_EMAIL, "name": "ApplyPilot"},
        "subject": subject,
        "content": [{"type": "text/html" if html else "text/plain", "value": body}],
    }
    resp = httpx.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=10,
    )
    if resp.status_code not in (200, 202):
        raise RuntimeError(f"SendGrid error {resp.status_code}: {resp.text}")
    logger.debug(f"Email sent via SendGrid to {to_email}")


def _send_via_smtp(to_email: str, subject: str, body: str, html: bool):
    msg = MIMEMultipart("alternative")
    msg["From"]    = FROM_EMAIL
    msg["To"]      = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html" if html else "plain"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(FROM_EMAIL, to_email, msg.as_string())
    logger.debug(f"Email sent via SMTP to {to_email}")


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

async def _post_webhook(url: str, payload: dict):
    import httpx
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
    logger.debug(f"Webhook delivered to {url}")


# ---------------------------------------------------------------------------
# DB helpers (fetch user email + webhook from profiles table)
# ---------------------------------------------------------------------------

async def _get_user_email(user_id: str) -> Optional[str]:
    try:
        from db import get_conn
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT email FROM users WHERE id = %s", (user_id,))
                row = cur.fetchone()
                return row[0] if row else None
    except Exception:
        return None


async def _get_user_webhook(user_id: str) -> Optional[str]:
    try:
        from db import get_conn
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT webhook_url FROM profiles WHERE user_id = %s", (user_id,))
                row = cur.fetchone()
                return row[0] if (row and row[0]) else None
    except Exception:
        return None
