import hashlib
import re
from datetime import date


def make_fingerprint(portal: str, external_id: str) -> str:
    """
    Within-portal dedup: same job reposted on same portal.
    """
    raw = f"{portal}:{external_id}".lower()
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def make_cross_portal_fingerprint(company: str, title: str, location: str, posted_date: date | None) -> str:
    """
    Cross-portal dedup: same job posted on LinkedIn AND Greenhouse AND Workday.
    Prevents applying to the same role 3 times from different portals.
    """
    norm_company  = _normalize(company)
    norm_title    = _normalize(title)
    norm_location = _normalize(location)
    date_str      = posted_date.isoformat() if posted_date else "unknown"

    raw = f"{norm_company}|{norm_title}|{norm_location}|{date_str}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
