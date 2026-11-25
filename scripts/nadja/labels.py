"""Text -> ESCO-Labels für MeritMe.

Eine gemeinsame Label-Funktion für Stufe 1, Matching und Dashboard, damit alle mit denselben Labels rechnen.
Herleitung und Begründung: notebooks/eda_escox_extraktion.ipynb.

Methoden:
    "escox"     reines ESCOX (Wrapper scripts/esco_extractor.py, Schwelle 0,5)
    "escox_it"  ESCOX, nur IT-Skills
    "hybrid"    Wortsuche ∪ (ESCOX ∩ IT-Skills)

Benutzung im Notebook:
    import sys; sys.path.append("../scripts")
    from labels import load_market, label_market, label_names
    market = label_market(load_market(), method="hybrid_v2")
    label_names(market.loc[0, "labels"])

Kommandozeile (aus dem Repo-Ordner):
    python scripts/labels.py --method hybrid_v2
"""
import argparse
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ESCO_DIR = ROOT / "data/raw/esco"
DJINNI_DIR = ROOT / "data/raw/djinni"
PROCESSED = ROOT / "data/processed"
MARKET_FILE = PROCESSED / "jobmarket_data-engineer_180cv_2026-10-20.parquet"   # eingefrorener Markt

METHODS = ("escox", "escox_it", "hybrid", "escox_v2_it", "hybrid_v2", "hybrid_v2_noedu")
DEFAULT_METHOD = "hybrid_v2"

# STOPLIST aus eda_jobmarket_final.ipynb: ESCO-Skills, deren Namen oder Synonyme im Freitext falsch treffen
STOP_SKILLS = {
    "statistics",                               # Synonym „big data“
    "Scratch (computer programming)",           # trifft „from scratch“
    "Visual Basic",                             # Synonym „.NET“
    "SPARK",                                    # in ESCO ein Java-Framework, nicht Apache Spark
    "Source (digital game creation systems)",   # trifft „source“
    "computer programming",                     # Synonym „io“
}
# Einzelne Synonyme, die normale englische Wörter oder Namen sind („it“ -> computer technology, „less“ -> LESS)
STOP_PHRASES = {"it", "less", "pos", "saas", "io", "ar", "ct", "ort", "nec", "ada", "ann", "nn", "iam", "obs", "spe",
                "sai", "vam", "pow", "noc"}
# Studienfächer, die ESCO als Skill führt. Im CV meinen sie fast immer den Abschluss ("Bachelor's Degree in Computer
# Science"), nicht eine Fähigkeit -> Bildungsweg würde über das Label in den Score rutschen (siehe
# eda_zwillinge_auswertung.ipynb). Teamentscheidung offen; "hybrid_v2_noedu" nimmt sie heraus.
EDUCATION_SKILLS = {"computer science"}       # Synonyme ("informatics") fallen mit dem Skill weg

# v2-Zerlegung für ESCOX (aus Tobis matching.py): Stellen, an denen ein Text in Phrasen zerfällt
LINE_BREAK = r"[\r\n\t]+"
SENTENCE_END = r"\.(?=\s|$)"            # Punkt nur am Satzende, "Node.js" bleibt ganz
LIST_SEPARATOR = r"[,;/|•·&]"           # Achtung: trennt auch "CI/CD", "PL/SQL", "R&D" (nur für ESCOX relevant)
DASH_WITH_SPACES = r"\s[-–—]\s"         # " - " trennt, "self-taught" nicht
CONJUNCTION = r"\band\b|\bor\b"         # nur ganze Wörter, nicht "and" in "standard"
PHRASE_BOUNDARY = re.compile("|".join([LINE_BREAK, SENTENCE_END, LIST_SEPARATOR, DASH_WITH_SPACES, CONJUNCTION]),
                             re.IGNORECASE)


# --------------------------------------------------------------------------------------------- Daten

def load_market(path: Path = MARKET_FILE) -> pd.DataFrame:
    """Markt-Parquet + Texte aus den Djinni-Rohdaten (Textdefinition wie in eda_jobmarket_final.ipynb)."""
    market = pd.read_parquet(path)
    cv = pd.read_parquet(DJINNI_DIR / "cv_profiles_en.parquet", columns=["id", "Position", "Highlights", "Moreinfo"])
    jobs = pd.read_parquet(DJINNI_DIR / "job_postings_en.parquet", columns=["id", "Position", "Long Description"])
    cv["text"] = cv[["Position", "Highlights", "Moreinfo"]].fillna("").agg("\n".join, axis=1).str.strip()
    jobs["text"] = jobs[["Position", "Long Description"]].fillna("").agg("\n".join, axis=1).str.strip()
    texts = pd.concat([cv[["id", "text"]], jobs[["id", "text"]]])
    market = market.merge(texts, on="id", how="left")
    missing = market["text"].isna().sum()
    if missing:
        raise ValueError(f"{missing} Dokumente ohne Text – fehlen die Djinni-Rohdaten in {DJINNI_DIR}?")
    return market


# --------------------------------------------------------------------------------------------- ESCO

@lru_cache(maxsize=1)
def _esco_skills() -> pd.DataFrame:
    return pd.read_csv(ESCO_DIR / "skills_en.csv").fillna("").drop_duplicates("conceptUri")


@lru_cache(maxsize=1)
def it_skills() -> frozenset:
    """Digitale ESCO-Skills, die mindestens einem IT-Beruf (ISCO 25) zugeordnet sind (wie eda_jobmarket_final.ipynb)."""
    occupations = pd.read_csv(ESCO_DIR / "occupations_en.csv").fillna("")
    occ_skills = pd.read_csv(ESCO_DIR / "occupationSkillRelations_en.csv")
    digital = set(pd.read_csv(ESCO_DIR / "digitalSkillsCollection_en.csv")["conceptUri"])
    it_occ = occupations.loc[occupations["iscoGroup"].astype(str).str.startswith("25"), "conceptUri"]
    return frozenset(set(occ_skills.loc[occ_skills["occupationUri"].isin(it_occ), "skillUri"]) & digital)


@lru_cache(maxsize=1)
def _label_of() -> dict:
    s = _esco_skills()
    return dict(zip(s["conceptUri"], s["preferredLabel"]))


def _uris_of(names) -> frozenset:
    s = _esco_skills()
    return frozenset(s.loc[s["preferredLabel"].isin(names), "conceptUri"])


def label_names(uris) -> list[str]:
    """URIs -> sortierte ESCO-Namen (zum Lesen)."""
    label_of = _label_of()
    return sorted(label_of.get(u, u) for u in uris)


# --------------------------------------------------------------------------------------------- Wortsuche

@lru_cache(maxsize=1)
def _vocabulary() -> tuple[dict, re.Pattern]:
    """Suchbegriff -> URIs, aus Namen + Synonymen aller IT-Skills, ohne Stopplisten."""
    s = _esco_skills()
    s = s[s["conceptUri"].isin(it_skills()) & ~s["preferredLabel"].isin(STOP_SKILLS)]
    phrase_to_uris = {}
    for label, alt, uri in zip(s["preferredLabel"], s["altLabels"], s["conceptUri"]):
        for name in [label] + alt.split("\n"):
            name = re.sub(r"\s*\(.*?\)", "", name).strip().lower()      # "Python (computer programming)" -> "python"
            if len(name) >= 2 and name not in STOP_PHRASES:
                phrase_to_uris.setdefault(name, set()).add(uri)
    # ein Muster für alle Begriffe, längste zuerst ("sql server" vor "sql"); ganze Wörter, c++/c# bleiben ganz
    alternatives = "|".join(re.escape(p) for p in sorted(phrase_to_uris, key=len, reverse=True))
    pattern = re.compile(rf"(?<![\w+#])(?:{alternatives})(?![\w+#])", re.IGNORECASE)
    return phrase_to_uris, pattern


def word_labels(text: str) -> set:
    """ESCO-IT-Skills, deren Name oder Synonym wörtlich im Text steht."""
    phrase_to_uris, pattern = _vocabulary()
    # .get: Unicode-Sonderfälle (z. B. türkisches "ı") treffen das Muster, aber nicht den Schlüssel
    return set().union(*(phrase_to_uris.get(m.lower(), set()) for m in pattern.findall(text)))


# --------------------------------------------------------------------------------------------- ESCOX

@lru_cache(maxsize=1)
def _escox():
    import sys
    sys.path.append(str(ROOT / "scripts"))
    from esco_extractor import EscoExtractor, EscoxConfig
    return EscoExtractor(EscoxConfig(esco_csv=ESCO_DIR / "skills_en.csv"))._escox   # SkillExtractor der Bibliothek


def split_into_phrases(text: str) -> list[str]:
    """v2-Zerlegung: 'Python and SQL, Node.js' -> ['Python', 'SQL', 'Node.js']"""
    return [p for p in (x.strip() for x in PHRASE_BOUNDARY.split(text)) if p]


_ESCOX_MEMO = {}   # (Version, Text) -> Labels, damit mehrere Methoden ESCOX nicht doppelt rechnen


def escox_labels(texts: list[str], version: str = "v1") -> list[set]:
    """ESCOX auf alle Texte. v1 = Zerlegung der Bibliothek, v2 = split_into_phrases."""
    texts = list(texts)
    todo = list(dict.fromkeys(t for t in texts if (version, t) not in _ESCOX_MEMO))
    if todo:
        sx = _escox()
        if version == "v2":
            sx._texts_to_tokens = lambda ts: [split_into_phrases(t) for t in ts]
        try:
            for t, uris in zip(todo, sx.get_skills(todo)):
                _ESCOX_MEMO[(version, t)] = set(uris)
        finally:
            if version == "v2":
                del sx._texts_to_tokens          # Original-Zerlegung der Bibliothek wiederherstellen
    return [set(_ESCOX_MEMO[(version, t)]) for t in texts]


# --------------------------------------------------------------------------------------------- Hauptfunktion

def extract_labels(texts, method: str = DEFAULT_METHOD) -> list[set]:
    """Liste von Texten -> Liste von Label-Mengen (ESCO-URIs)."""
    if method not in METHODS:
        raise ValueError(f"method muss eines von {METHODS} sein, nicht {method!r}")
    texts = list(texts)
    it = it_skills()

    if method in ("escox", "escox_it", "hybrid"):                  # v1
        escox = escox_labels(texts, "v1")
        if method == "escox":
            return escox
        if method == "escox_it":
            return [e & it for e in escox]
        return [word_labels(t) | (e & it) for t, e in zip(texts, escox)]

    allowed = it - _uris_of(STOP_SKILLS)                             # v2
    if method == "hybrid_v2_noedu":
        allowed = allowed - _uris_of(EDUCATION_SKILLS)
    escox = escox_labels(texts, "v2")
    if method == "escox_v2_it":
        return [e & allowed for e in escox]
    return [(word_labels(t) | e) & allowed for t, e in zip(texts, escox)]


def label_market(market: pd.DataFrame, method: str = DEFAULT_METHOD, cache: bool = True) -> pd.DataFrame:
    """Hängt die Spalte `labels` (Menge von URIs) an. ESCOX dauert ~0,1 s pro Text, daher Cache pro Methode.

    Cache: data/processed/labels_<method>.parquet (nach id). Nach Änderungen an Stopplisten oder ESCOX-Schwelle
    die Datei löschen, damit neu gerechnet wird.
    """
    path = PROCESSED / f"labels_{method}.parquet"
    known = {}
    if cache and path.exists():
        cached = pd.read_parquet(path)
        known = dict(zip(cached["id"], cached["labels"].apply(set)))
    todo = market.loc[~market["id"].isin(known), ["id", "text"]]
    if len(todo):
        known.update(zip(todo["id"], extract_labels(todo["text"], method)))
        if cache:
            pd.DataFrame({"id": list(known), "labels": [sorted(v) for v in known.values()]}).to_parquet(path, index=False)
    return market.assign(labels=market["id"].map(known))


# --------------------------------------------------------------------------------------------- Kommandozeile

def main():
    parser = argparse.ArgumentParser(description="ESCO-Labels für den Jobmarkt berechnen.")
    parser.add_argument("--method", choices=METHODS, default=DEFAULT_METHOD)
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    market = label_market(load_market(), args.method, cache=not args.no_cache)
    n = market["labels"].str.len()
    print(f"Methode: {args.method} | IT-Skills: {len(it_skills())} | Suchbegriffe: {len(_vocabulary()[0]):,}")
    print("Ø Labels pro Dokument:", market.assign(n=n).groupby(["role", "ring"])["n"].mean().round(1).to_dict())

    trainee = market[market["position"].str.contains("trainee", case=False)].iloc[0]
    print(f"\nBeispiel „{trainee['position']}“:", label_names(trainee["labels"]))


if __name__ == "__main__":
    main()
