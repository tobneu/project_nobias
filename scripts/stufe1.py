"""Stufe 1: Bleiben die ESCO-Labels eines CVs stabil, wenn ein Zwilling nur den Stil ändert?

Gate: mittlerer Jaccard >= 0,85 zwischen Original und Zwilling, gemessen mit ESCOX (korrigierte Zerlegung,
nur IT-Skills) auf den Kombinations-Zwillingen (all) des Haupttests (Ring A + B).

Aufruf im Ordner scripts:  python stufe1.py
"""
from collections import Counter
from functools import lru_cache
from pathlib import Path

import pandas as pd
from esco_skill_extractor import SkillExtractor

from matching import (ESCO_SKILLS, ESCOX_MODEL, IT_SKILLS, NOISE_SKILLS, SIMILARITY_THRESHOLD, extract_skills,
                      find_skills_by_meaning)

ROOT = Path(__file__).resolve().parents[1]
TWINS_FILE = ROOT / "data/processed/twins_vollauf_v2.parquet"
CV_FILE = ROOT / "data/raw/djinni/cv_profiles_en.parquet"

GATE_VARIANT = "all"
GATE_TEST_GROUP = "haupttest"
MIN_MEAN_JACCARD = 0.85
MIN_MEAN_LABELS = 5
MAX_SHARE_BOTH_EMPTY = 0.05

UNCHANGED_ESCOX = SkillExtractor(model=ESCOX_MODEL, skills_threshold=SIMILARITY_THRESHOLD, device="cpu")
SKILL_NAMES = dict(zip(ESCO_SKILLS["conceptUri"], ESCO_SKILLS["preferredLabel"]))


@lru_cache(maxsize=None)
def labels_with_fix(text):
    """Das, was Stufe 1 prüft: nur ESCOX, korrigierte Zerlegung, nur IT-Skills."""
    return frozenset(find_skills_by_meaning(text) & IT_SKILLS - NOISE_SKILLS)


@lru_cache(maxsize=None)
def labels_hybrid(text):
    """Vergleichswert: die Labels, mit denen das Matching rechnet (Wortsuche und ESCOX)."""
    return frozenset(extract_skills(text))


@lru_cache(maxsize=None)
def labels_unchanged_escox(text):
    """Vergleichswert: ESCOX so, wie die Bibliothek es liefert."""
    return frozenset(UNCHANGED_ESCOX.get_skills([text])[0])


def load_gate_pairs():
    """Die Zwillinge des Gates mit dem Text ihres Originals (Djinni: Position, Highlights, Moreinfo)."""
    twins = pd.read_parquet(TWINS_FILE)
    twins = twins[(twins["variante"] == GATE_VARIANT) & (twins["test"] == GATE_TEST_GROUP)]
    cvs = pd.read_parquet(CV_FILE, columns=["id", "Position", "Highlights", "Moreinfo"]).drop_duplicates("id")
    cvs["original_text"] = cvs[["Position", "Highlights", "Moreinfo"]].fillna("").agg("\n".join, axis=1).str.strip()
    return twins.merge(cvs[["id", "original_text"]], on="id", how="left", validate="one_to_one")


def jaccard(labels_a, labels_b):
    """Anteil gemeinsamer Labels. None, wenn beide Mengen leer sind (nicht auswertbar)."""
    if not labels_a and not labels_b:
        return None
    return len(labels_a & labels_b) / len(labels_a | labels_b)


def compare_labels(pairs, extract_labels):
    """Hängt die Labels von Original und Zwilling und deren Jaccard an."""
    original_labels = pairs["original_text"].map(extract_labels)
    twin_labels = pairs["text_zwilling"].map(extract_labels)
    jaccards = [jaccard(a, b) for a, b in zip(original_labels, twin_labels)]
    return pairs.assign(original_labels=original_labels, twin_labels=twin_labels,
                        jaccard=pd.to_numeric(pd.Series(jaccards, index=pairs.index)))


def print_gate(compared):
    mean_jaccard = compared["jaccard"].mean()
    mean_labels = compared["original_labels"].map(len).mean()
    share_both_empty = compared["jaccard"].isna().mean()

    is_valid = mean_labels >= MIN_MEAN_LABELS and share_both_empty <= MAX_SHARE_BOTH_EMPTY
    is_passed = is_valid and mean_jaccard >= MIN_MEAN_JACCARD
    result = "BESTANDEN" if is_passed else "UNGÜLTIG" if not is_valid else "NICHT BESTANDEN"

    print(f"Gate ({GATE_VARIANT}, {GATE_TEST_GROUP}, {len(compared)} Paare): {result}")
    print(f" --> Mittlerer Jaccard:  {mean_jaccard:.3f}  (Ziel >= {MIN_MEAN_JACCARD})")
    print(f" Labels pro CV:      {mean_labels:.1f}  (Ziel >= {MIN_MEAN_LABELS})")
    print(f" Beide Mengen leer:  {share_both_empty:.1%}  (erlaubt <= {MAX_SHARE_BOTH_EMPTY:.0%})")


def print_changed_labels(compared, top_n=10):
    lost, gained = Counter(), Counter()
    for original, twin in zip(compared["original_labels"], compared["twin_labels"]):
        lost.update(original - twin)
        gained.update(twin - original)
    for title, counter in [("Häufig verloren", lost), ("Häufig gewonnen", gained)]:
        print(f"\n{title}:")
        for skill, count in counter.most_common(top_n):
            print(f"- {count:3d} {SKILL_NAMES.get(skill, skill)}")


def main():
    pairs = load_gate_pairs()
    gate = compare_labels(pairs, labels_with_fix)
    print_gate(gate)

    print("\nMittlerer Jaccard je Methode:")
    print(f"ESCOX mit Fix (Gate): {gate['jaccard'].mean():.3f}")
    print(f"Hybrid (Matching): {compare_labels(pairs, labels_hybrid)['jaccard'].mean():.3f}")
    print(f"ESCOX unverändert: {compare_labels(pairs, labels_unchanged_escox)['jaccard'].mean():.3f}")

    print_changed_labels(gate)


if __name__ == "__main__":
    main()
