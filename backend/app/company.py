from functools import lru_cache

from app.config import get_settings
from app.schemas import CompanyProfile

# Last resort only: used when the corpus ships no company_profile.json.
DEFAULT_PROFILE = CompanyProfile(
    name="당사",
    headcount=50,
    annual_revenue_krw=10_000_000_000,
    regions=["서울", "경기", "인천", "수도권"],
    certifications=["소프트웨어사업자 신고"],
    tech_stack=["python", "react", "데이터 분석"],
    target_margin=0.15,
    min_project_budget_krw=300_000_000,
    max_concurrent_projects=5,
    current_active_projects=0,
)


@lru_cache
def load_company_profile() -> CompanyProfile:
    from app.screening.dataset import load_company

    root = get_settings().corpus_path
    return (load_company(root) if root.is_dir() else None) or DEFAULT_PROFILE
