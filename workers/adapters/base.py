from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ApplyResult(Enum):
    SUCCESS       = "applied"
    ALREADY_APPLIED = "already_applied"
    CAPTCHA       = "captcha"
    FAILED        = "failed"
    UNSUPPORTED   = "unsupported"


@dataclass
class UserProfile:
    user_id:      str
    full_name:    str
    email:        str
    phone:        str
    location:     str
    linkedin_url: str
    github_url:   str
    resume_path:  str            # local path to downloaded PDF
    skills:       list[str]
    experience_years: Optional[int] = None


@dataclass
class JobInfo:
    id:        str
    title:     str
    company:   str
    apply_url: str
    portal:    str
    location:  str


@dataclass
class ApplicationResult:
    status:       ApplyResult
    message:      str = ""
    confirmation: str = ""      # confirmation number if provided


class BaseAdapter(ABC):
    """Every portal adapter implements this interface."""

    def __init__(self, session_manager):
        self.session_manager = session_manager

    @abstractmethod
    async def login(self, credentials: dict) -> bool:
        """Log into the portal. Returns True if successful."""
        ...

    @abstractmethod
    async def apply(self, job: JobInfo, profile: UserProfile) -> ApplicationResult:
        """Apply to a job. Returns the result."""
        ...

    @abstractmethod
    async def is_already_applied(self, job: JobInfo) -> bool:
        """Check if already applied to avoid duplicates."""
        ...
