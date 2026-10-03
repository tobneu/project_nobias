import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import torch
from esco_skill_extractor import SkillExtractor

ESCO_CSV = Path("data/raw/esco/skills_en.csv")


@dataclass(frozen=True)
class EscoxConfig:
    model: str = "all-MiniLM-L6-v2"
    skills_threshold: float = 0.5
    device: str = "cpu"
    esco_csv: Path = ESCO_CSV


@dataclass(frozen=True)
class Skill:
    uri: str
    label: str | None
    skill_type: str | None

    def to_dict(self) -> dict:
        return {"uri": self.uri, "label": self.label, "skill_type": self.skill_type}


class EscoExtractor:
    def __init__(self, config: EscoxConfig = EscoxConfig()):
        self.config = config
        torch.manual_seed(0)
        torch.use_deterministic_algorithms(True)
        self._escox = SkillExtractor(
            model=config.model,
            skills_threshold=config.skills_threshold,
            device=config.device,
        )
        self._labels = self._load_labels(config.esco_csv)

    @staticmethod
    def _load_labels(path: Path) -> dict[str, tuple[str, str]]:
        if not path.exists():
            print(f"Warning: {path} not found", file=sys.stderr)
            return {}
        
        esco = pd.read_csv(path).fillna("")
        labels = {}
        for _, row in esco.iterrows():
            labels[row["conceptUri"]] = (row["preferredLabel"], row["skillType"])
        
        return labels

    def extract(self, text: str) -> list[Skill]:
        uris = self._escox.get_skills([text])[0]
        skills = [Skill(uri, *self._labels.get(uri, (None, None))) for uri in uris]
        return sorted(skills, key=lambda s: (s.label or "", s.uri))


def main():
    parser = argparse.ArgumentParser(description="Extract ESCO skills from a raw text.")
    parser.add_argument("--raw", required=True, help="raw CV or job posting text")
    parser.add_argument("--threshold", type=float, default=EscoxConfig.skills_threshold)
    args = parser.parse_args()

    config = EscoxConfig(skills_threshold=args.threshold)
    skills = EscoExtractor(config).extract(args.raw)

    for skill in skills:
        print(f"> [SKILL] {skill.label}: {skill.uri}")


if __name__ == "__main__":
    main()
