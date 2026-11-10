import re
from pathlib import Path

import pandas as pd

ESCO_DIR = Path(__file__).resolve().parents[1] / "data/raw/esco"

ISCO_GROUP_IT = "25"
MIN_PHRASE_LENGTH = 2

# ESCO-Skills, deren Namen oder Synonyme in Freitext falsch treffen
NOISE_SKILL_NAMES = {
    "statistics",                               # Synonym "big data"
    "Scratch (computer programming)",           # trifft "from scratch"
    "Visual Basic",                             # Synonym ".NET"
    "SPARK",                                    # in ESCO ein Java-Framework, nicht Apache Spark
    "Source (digital game creation systems)",   # trifft "source"
    "computer programming",                     # Synonym "io"
}
# Andere Seite: Synonyme, die normale englische Wörter oder Namen sind und wir keine Skills davon haben wollen
NOISE_PHRASES = {"it", "less", "pos", "saas", "io", "ar", "ct", "ort", "nec", "ada", "ann", "nn", "iam", "obs", "spe",
                 "sai", "vam", "pow", "noc"}

# Ein Treffer darf nicht mitten in einem Wort beginnen oder enden.
# "+" und "#" zählen zum Wort, sonst würde "c" auch in "c++" treffen.
NOT_INSIDE_WORD_BEFORE = r"(?<![\w+#])"
NOT_INSIDE_WORD_AFTER = r"(?![\w+#])"


def load_esco_skills():
    skills = pd.read_csv(ESCO_DIR / "skills_en.csv").fillna("")
    return skills.drop_duplicates("conceptUri")


def load_it_skills():
    """Digitale ESCO-Skills, die mindestens einem IT-Beruf zugeordnet sind."""
    occupations = pd.read_csv(ESCO_DIR / "occupations_en.csv").fillna("")
    occupation_skills = pd.read_csv(ESCO_DIR / "occupationSkillRelations_en.csv")
    digital_skills = pd.read_csv(ESCO_DIR / "digitalSkillsCollection_en.csv")

    is_it_occupation = occupations["iscoGroup"].astype(str).str.startswith(ISCO_GROUP_IT)
    it_occupations = occupations.loc[is_it_occupation, "conceptUri"]
    is_it_relation = occupation_skills["occupationUri"].isin(it_occupations)
    skills_of_it_occupations = set(occupation_skills.loc[is_it_relation, "skillUri"])

    return skills_of_it_occupations & set(digital_skills["conceptUri"])


def find_noise_skills(esco_skills):
    is_noise = esco_skills["preferredLabel"].isin(NOISE_SKILL_NAMES)
    return set(esco_skills.loc[is_noise, "conceptUri"])


def to_search_phrase(skill_name):
    """'Python (computer programming)' -> 'python'"""
    return skill_name.split("(")[0].strip().lower()


def is_searchable(phrase):
    return len(phrase) >= MIN_PHRASE_LENGTH and phrase not in NOISE_PHRASES


def build_skills_by_phrase(esco_skills, allowed_skills):
    """Suchbegriff -> ESCO-Skills, aus Namen und Synonymen der erlaubten Skills."""
    skills_by_phrase = {}
    allowed_rows = esco_skills[esco_skills["conceptUri"].isin(allowed_skills)]
    for skill in allowed_rows.itertuples():
        for name in [skill.preferredLabel, *skill.altLabels.split("\n")]:
            phrase = to_search_phrase(name)
            if is_searchable(phrase):
                skills_by_phrase.setdefault(phrase, set()).add(skill.conceptUri)
    return skills_by_phrase


def build_phrase_pattern(phrases):
    """Sucht einen der Begriffe, aber nicht mitten in einem Wort."""
    # Längste Begriffe zuerst, damit "sql server" nicht nur als "sql" erkannt wird
    phrases_longest_first = sorted(phrases, key=len, reverse=True)
    any_phrase = "|".join(re.escape(phrase) for phrase in phrases_longest_first)
    return re.compile(NOT_INSIDE_WORD_BEFORE + "(" + any_phrase + ")" + NOT_INSIDE_WORD_AFTER, re.IGNORECASE)


ESCO_SKILLS = load_esco_skills()
IT_SKILLS = load_it_skills()
NOISE_SKILLS = find_noise_skills(ESCO_SKILLS)
SKILLS_BY_PHRASE = build_skills_by_phrase(ESCO_SKILLS, IT_SKILLS - NOISE_SKILLS)
SKILL_PHRASE_PATTERN = build_phrase_pattern(SKILLS_BY_PHRASE)


def find_skills_by_name(text):
    """ESCO-IT-Skills, deren Name oder Synonym wörtlich im Text steht."""
    found_skills = set()
    for phrase in SKILL_PHRASE_PATTERN.findall(text):
        found_skills |= SKILLS_BY_PHRASE.get(phrase.lower(), set())
    return found_skills
