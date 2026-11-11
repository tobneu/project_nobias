"""Stufe 1: Bleiben die ESCOX-Labels gleich, wenn ein Zwilling nur den Stil ändert?"""
from functools import lru_cache

from esco_skill_extractor import SkillExtractor

from matching import ESCOX_MODEL, IT_SKILLS, NOISE_SKILLS, SIMILARITY_THRESHOLD, find_skills_by_meaning

GATE_MIN_MEAN_JACCARD = 0.85

UNCHANGED_ESCOX = SkillExtractor(model=ESCOX_MODEL, skills_threshold=SIMILARITY_THRESHOLD, device="cpu")


@lru_cache(maxsize=None)
def labels_with_fix(text):
    """Das, was Stufe 1 prüft: nur ESCOX, korrigierte Zerlegung, nur IT-Skills."""
    return frozenset(find_skills_by_meaning(text) & IT_SKILLS - NOISE_SKILLS)


@lru_cache(maxsize=None)
def labels_unchanged_escox(text):
    """Vergleichswert: ESCOX so, wie die Bibliothek es liefert."""
    return frozenset(UNCHANGED_ESCOX.get_skills([text])[0])


def jaccard(labels_a, labels_b):
    """Anteil gemeinsamer Labels. None, wenn beide Mengen leer sind (nicht auswertbar)."""
    if not labels_a and not labels_b:
        return None
    # https://en.wikipedia.org/wiki/Jaccard_index
    return len(labels_a & labels_b) / len(labels_a | labels_b)


def gate_passed(jaccards):
    """Gate: mittlerer Jaccard aller auswertbaren Paare mindestens 0,85."""
    evaluable = [value for value in jaccards if value is not None]
    return sum(evaluable) / len(evaluable) >= GATE_MIN_MEAN_JACCARD


def main():
    original = ("Data Engineer\n"
                "Built ETL pipelines with Python and Apache Airflow.\n"
                "Designed a data warehouse on PostgreSQL, and created dashboards in Power BI.\n"
                "Bachelor's Degree in Computer Science")
    twin = ("Data Engineer\n"
            "Previously worked in customer support before moving into IT.\n"
            "Built ETL pipelines with Python and Apache Airflow.\n"
            "Designed a data warehouse on PostgreSQL, and created dashboards in Power BI.\n"
            "Self-taught developer, learned through online resources and personal projects")

    for method, extract_labels in [("mit Fix", labels_with_fix), ("ESCOX unverändert", labels_unchanged_escox)]:
        value = jaccard(extract_labels(original), extract_labels(twin))
        print(f"{method:18} Jaccard {value:.3f}  Gate: {gate_passed([value])}")


if __name__ == "__main__":
    main()
