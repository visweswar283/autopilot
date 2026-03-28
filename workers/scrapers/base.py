from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from loguru import logger


@dataclass
class JobListing:
    portal:      str
    external_id: str
    title:       str
    company:     str
    location:    str
    apply_url:   str
    remote:      bool          = False
    description: str           = ""
    salary_min:  Optional[int] = None
    salary_max:  Optional[int] = None
    posted_at:   Optional[date] = None
    raw_data:    dict          = field(default_factory=dict)


class BaseScraper(ABC):
    """All scrapers implement this interface."""

    def __init__(self, roles: list[str], locations: list[str], headless: bool = True):
        self.roles     = roles
        self.locations = locations
        self.headless  = headless

    @abstractmethod
    async def scrape(self) -> list[JobListing]:
        """Discover and return job listings."""
        ...

    def _is_relevant(self, title: str) -> bool:
        """Quick title relevance check against target roles."""
        title_lower = title.lower()
        return any(
            role.lower().split()[0] in title_lower   # "Software" matches "Senior Software Engineer"
            for role in self.roles
        )

    def log(self, msg: str):
        logger.info(f"[{self.__class__.__name__}] {msg}")
