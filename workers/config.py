import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

# Job search preferences — read from env or use defaults
TARGET_ROLES = os.getenv("TARGET_ROLES", "Software Engineer,Backend Engineer,Full Stack Engineer").split(",")
TARGET_LOCATIONS = os.getenv("TARGET_LOCATIONS", "Remote,San Francisco,New York").split(",")
MIN_SALARY = int(os.getenv("MIN_SALARY", "120000"))

# Scraper settings
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
SCRAPER_INTERVAL_HOURS = int(os.getenv("SCRAPER_INTERVAL_HOURS", "2"))
MAX_JOBS_PER_SEARCH = int(os.getenv("MAX_JOBS_PER_SEARCH", "50"))

# LinkedIn credentials
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# Workday target companies — list of (company_name, workday_subdomain)
WORKDAY_COMPANIES = [
    ("Google",      "google",      "jobs"),
    ("Amazon",      "amazon",      "External_Career_Site"),
    ("Microsoft",   "microsoft",   "Global_Talent_Acquisition"),
    ("Salesforce",  "salesforce",  "External_Career_Site"),
    ("Adobe",       "adobe",       "External_Career_Site"),
    ("Nvidia",      "nvidia",      "NVIDIAExternalCareerSite"),
    ("Uber",        "uber",        "External_Career_Site"),
    ("Airbnb",      "airbnb",      "Airbnb"),
    ("Stripe",      "stripe",      "StripeUS"),
    ("Databricks",  "databricks",  "External_Career_Site"),
]
