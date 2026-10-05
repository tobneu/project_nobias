import argparse

import pandas as pd

from esco_extractor import EscoExtractor, EscoxConfig

CVS = "data/raw/djinni/cv_profiles_en.parquet"


def try_random_cv(seed: int | None, threshold: float):
    """Picks a random CV, prints its text and the extracted ESCO skills."""
    cv = pd.read_parquet(CVS).sample(1, random_state=seed).iloc[0]

    print(f"CV {cv['id']} | {cv['Position']}\n")
    print(cv["CV"].strip(), "\n")

    extractor = EscoExtractor(EscoxConfig(skills_threshold=threshold))
    for skill in extractor.extract(cv["CV"]):
        print(f"> [SKILL] {skill.label}: {skill.uri}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract ESCO skills from a random CV.")
    parser.add_argument("--seed", type=int, help="same seed = same CV")
    parser.add_argument("--threshold", type=float, default=EscoxConfig.skills_threshold)
    args = parser.parse_args()
    try_random_cv(args.seed, args.threshold)
