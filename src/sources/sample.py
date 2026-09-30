"""Fake but realistic opportunities so you can try the whole pipeline and the
dashboard offline: python -m src.pipeline --sample"""
from ..models import Opportunity, make_id

SAMPLES = [
    ("Junior Data Engineer (Remote, Worldwide)", "Nimbus Analytics", "Worldwide", "remote",
     "We are a fully remote team hiring a junior data engineer. You will build ETL pipelines with Python, "
     "Airflow and dbt on Snowflake. 0-2 years of experience. Open to candidates anywhere; we hire "
     "international contractors through Deel. 4 hours overlap with CET preferred."),
    ("Machine Learning Engineer, LLM Applications", "Brightpath AI (San Francisco)", "USA Only", "remote",
     "Build RAG systems with LangChain. Must be authorized to work in the United States. No visa sponsorship. "
     "3+ years experience."),
    ("Graduate Data Analyst", "Gulf Logistics Group", "Dubai, UAE", "relocation",
     "Graduate program for fresh graduates in data analytics. SQL, Python, Power BI. Employment visa, "
     "flight and housing allowance provided for international hires. Applications close 2026-10-31."),
    ("Data Engineering Intern → Full-time", "Riyadh FinTech Co.", "Riyadh, Saudi Arabia", "relocation",
     "Entry-level role for Saudi nationals only as part of our Saudization program. Spark and SQL."),
    ("Blue Book Traineeship – European Commission", "European Commission", "Brussels, Belgium", "early_career",
     "Paid 5-month traineeship for recent university graduates, open to EU and non-EU nationals. "
     "Monthly grant provided. Applications open until 2026-10-15."),
    ("Fully Funded MSc Data Science Scholarship", "University of Example", "Germany", "scholarship",
     "Fully funded master's scholarship for students from Africa and the MENA region. Covers tuition, "
     "monthly stipend and travel. Deadline 2026-11-30."),
    ("Senior Staff Data Platform Engineer", "Hyperscale Inc.", "Europe", "remote",
     "10+ years of experience leading data platform teams. Remote within Europe."),
    ("Analytics Engineer (dbt) – Remote EMEA", "Carta Verde", "EMEA", "remote",
     "Remote across EMEA. Junior to mid level. dbt, SQL, Airflow. French is a plus. Contract via Remote.com."),
]


def fetch_sample() -> list[Opportunity]:
    return [
        Opportunity(
            id=make_id("sample", title), source="Sample", title=title, organization=org,
            url="https://example.com/" + make_id("s", title), description=desc,
            location=loc, category_hint=hint,
        )
        for title, org, loc, hint, desc in SAMPLES
    ]
