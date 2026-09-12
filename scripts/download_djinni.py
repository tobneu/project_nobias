from datasets import load_dataset
from pathlib import Path

RAW_DIR = Path("data/raw/djinni")
RAW_DIR.mkdir(parents=True, exist_ok=True)

cvs = load_dataset("lang-uk/recruitment-dataset-candidate-profiles-english")["train"]
cvs.to_parquet(RAW_DIR / "cv_profiles_en.parquet")

jobs = load_dataset("lang-uk/recruitment-dataset-job-descriptions-english")["train"]
jobs.to_parquet(RAW_DIR / "job_postings_en.parquet")

print(f"CVs: {len(cvs)} | Jobs: {len(jobs)}")

