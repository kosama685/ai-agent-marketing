from __future__ import annotations

from datetime import datetime, timedelta
from random import Random

from .database import add_company, execute, fetch_one, log_workflow, utc_now

RNG = Random(42)

INDUSTRIES = [
    "Hotel", "Restaurant", "Clinic", "Ecommerce", "Construction", "Travel Agency",
    "Salon", "Real Estate", "Dental Clinic", "Luxury Retail", "Tour Operator", "Hospitality Group"
]
COUNTRIES = ["Saudi Arabia", "UAE", "Pakistan", "Qatar", "Bahrain", "Kuwait", "United Kingdom", "Estonia"]
CITIES = {
    "Saudi Arabia": ["Riyadh", "Jeddah", "Dammam", "Al Khobar", "Makkah", "Madinah"],
    "UAE": ["Dubai", "Abu Dhabi", "Sharjah"],
    "Pakistan": ["Karachi", "Lahore", "Islamabad", "Multan"],
    "Qatar": ["Doha"],
    "Bahrain": ["Manama"],
    "Kuwait": ["Kuwait City"],
    "United Kingdom": ["London", "Manchester"],
    "Estonia": ["Tallinn", "Tartu"],
}
NAME_PREFIX = ["Royal", "Pearl", "Noble", "Nova", "Elite", "Crescent", "Falcon", "Atlas", "Oasis", "Vertex", "Urban", "Prime", "Golden", "Blue", "Desert", "Harbor", "Palm", "Crystal"]
NAME_SUFFIX = ["Group", "Solutions", "Hospitality", "Clinic", "Homes", "Tours", "Kitchen", "Studios", "Trading", "Residence", "Market", "Labs", "Center", "Digital", "Heights", "Plaza"]
FIRST_NAMES = ["Ahmed", "Sara", "Usman", "Fatima", "Omar", "Aisha", "Bilal", "Mariam", "Khalid", "Noor", "Zain", "Huda", "Fahad", "Amina", "Imran", "Lina"]
LAST_NAMES = ["Khan", "Al Saud", "Malik", "Hussain", "Al Qasimi", "Rehman", "Farooq", "Al Mansour", "Siddiqui", "Al Harbi", "Sheikh", "Mirza"]
ROLES = ["Owner", "Marketing Director", "General Manager", "Managing Partner", "Head of Sales", "Operations Director"]


def slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-").replace("--", "-")


def score_from_gaps(has_website: bool, rating: float, reviews: int, has_social: bool) -> tuple[str, int, str]:
    score = 35
    reasons: list[str] = []
    if not has_website:
        score += 32
        reasons.append("no visible conversion website")
    else:
        score += 8
        reasons.append("website exists but needs SEO/CRO audit")
    if reviews < 80:
        score += 14
        reasons.append("low review volume")
    if rating < 4.2:
        score += 12
        reasons.append("rating pressure")
    if not has_social:
        score += 14
        reasons.append("weak social footprint")
    score = min(98, score)
    label = "HOT" if score >= 75 else "WARM" if score >= 52 else "COLD"
    return label, score, "; ".join(reasons)


def make_company(index: int) -> dict:
    country = RNG.choice(COUNTRIES)
    city = RNG.choice(CITIES[country])
    industry = RNG.choice(INDUSTRIES)
    name = f"{RNG.choice(NAME_PREFIX)} {RNG.choice(NAME_SUFFIX)} {index:02d}"
    has_website = RNG.random() > 0.18
    website = f"https://www.{slugify(name)}.com" if has_website else None
    reviews = RNG.randint(5, 850)
    rating = round(RNG.uniform(3.5, 4.9), 1)
    has_social = RNG.random() > 0.28
    score, score_value, reason = score_from_gaps(has_website, rating, reviews, has_social)
    first = RNG.choice(FIRST_NAMES)
    last = RNG.choice(LAST_NAMES)
    email_domain = slugify(name).replace("-", "") + ".com"
    revenue = RNG.randint(180_000, 4_500_000)
    return {
        "name": name,
        "website": website,
        "industry": industry,
        "country": country,
        "city": city,
        "revenue_estimate": revenue,
        "source": RNG.choice(["Google Maps Demo", "Exhibition Demo", "Directory Import", "LinkedIn Demo", "Manual Referral"]),
        "instagram": f"https://instagram.com/{slugify(name)}" if has_social else None,
        "linkedin": f"https://linkedin.com/company/{slugify(name)}" if RNG.random() > 0.35 else None,
        "reviews": reviews,
        "rating": rating,
        "lead_score": score,
        "score_value": score_value,
        "score_reason": reason,
        "status": RNG.choice(["NEW", "QUALIFIED", "CONTACTED", "PROPOSAL_SENT", "NEGOTIATION"]),
        "contact": {
            "full_name": f"{first} {last}",
            "role": RNG.choice(ROLES),
            "email": f"{first.lower()}.{last.lower().replace(' ', '')}@{email_domain}",
            "phone": f"+9665{RNG.randint(10000000, 99999999)}" if country == "Saudi Arabia" else f"+9715{RNG.randint(10000000, 99999999)}",
            "whatsapp": f"+9665{RNG.randint(10000000, 99999999)}" if country == "Saudi Arabia" else f"+9715{RNG.randint(10000000, 99999999)}",
            "linkedin": f"https://linkedin.com/in/{first.lower()}-{last.lower().replace(' ', '-')}",
        },
    }


def seed_demo_data(force: bool = False) -> None:
    current = fetch_one("SELECT COUNT(*) AS total FROM companies WHERE deleted_at IS NULL")
    if current and int(current["total"]) > 0 and not force:
        return

    if force:
        from .database import connect
        with connect() as conn:
            for table in [
                "workflow_logs", "exhibition_leads", "exhibitions", "seo_audits", "content_pieces", "campaigns",
                "invoices", "proposals", "meetings", "notes", "tasks", "communications", "deals", "contacts", "companies",
            ]:
                conn.execute(f"DELETE FROM {table}")

    for idx in range(1, 57):
        add_company(make_company(idx))

    now = datetime.utcnow()
    exhibitions = [
        ("Saudi Hospitality Expo", "Riyadh, Saudi Arabia", now + timedelta(days=19), now + timedelta(days=21)),
        ("Arabian Travel Market", "Dubai, UAE", now + timedelta(days=42), now + timedelta(days=45)),
        ("GITEX Global", "Dubai, UAE", now + timedelta(days=95), now + timedelta(days=99)),
        ("Web Summit", "Lisbon, Portugal", now + timedelta(days=150), now + timedelta(days=153)),
        ("ITCN Asia", "Karachi, Pakistan", now + timedelta(days=70), now + timedelta(days=72)),
        ("Saudi Build", "Riyadh, Saudi Arabia", now + timedelta(days=115), now + timedelta(days=118)),
    ]
    for name, location, start, end in exhibitions:
        execute(
            "INSERT INTO exhibitions(name, location, start_date, end_date, booth_status, qr_code_data, created_at) VALUES(?,?,?,?,?,?,?)",
            (name, location, start.date().isoformat(), end.date().isoformat(), "PLANNED", f"salesforge://exhibition/{slugify(name)}", utc_now()),
        )

    campaign_rows = [
        ("KSA Hospitality Direct Booking Sprint", "EMAIL", "ACTIVE", "Hotels in Riyadh and Jeddah"),
        ("Clinic SEO & Arabic GEO Campaign", "WHATSAPP", "DRAFT", "Dental and aesthetic clinics in GCC"),
        ("Real Estate Lead Nurture", "LINKEDIN", "ACTIVE", "Developers and brokers"),
    ]
    for name, ctype, status, audience in campaign_rows:
        execute(
            "INSERT INTO campaigns(name, type, status, target_audience, leads_found, leads_contacted, responses, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (name, ctype, status, audience, RNG.randint(18, 140), RNG.randint(8, 65), RNG.randint(0, 14), utc_now(), utc_now()),
        )

    log_workflow("SEED", "DEMO_DATA", "SUCCESS", "Loaded 56 realistic demo leads and exhibitions")


def create_mock_scraped_leads(industry: str, country: str, city: str, count: int, source: str) -> list[int]:
    ids: list[int] = []
    for idx in range(count):
        company = make_company(RNG.randint(100, 999))
        company["industry"] = industry
        company["country"] = country
        company["city"] = city
        company["source"] = source
        ids.append(add_company(company))
    log_workflow("LEAD_DISCOVERY", "SCRAPE_DEMO", "SUCCESS", f"Generated {count} lead records for {industry} in {city}, {country}")
    return ids
