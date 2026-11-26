# Warum kein Wu-Palmer-Bonus für Extra-Skills: Der ESCO-Baum ist für IT zu flach.
# "computer science" liegt so nah an Python (0,73-0,80) wie Java (0,73-0,83),
# obwohl nur Java Python fachlich ersetzen kann.
#
# Wu-Palmer: 2 * Tiefe(gemeinsamer Vorfahre) / (Tiefe(a) + Tiefe(b)), Wurzel hat Tiefe 1
# https://aclanthology.org/P94-1019/
# https://www.nltk.org/howto/wordnet.html (wup_similarity)
import base64
import json
import zlib
from pathlib import Path

import pandas as pd

ESCO_DIR = Path(__file__).resolve().parents[1] / "data/raw/esco"

SKILL_PAIRS = [
    ("Python (computer programming)", "Java (computer programming)"),
    ("Python (computer programming)", "computer science"),
    ("Python (computer programming)", "PostgreSQL"),
    ("PostgreSQL", "SQL Server"),
    ("SQL", "NoSQL"),
    ("SQL", "computer science"),
    ("Hadoop", "data warehouse"),
    ("data engineering", "computer science"),
    ("data engineering", "data science"),
]


def load_esco_tree():
    relations = pd.read_csv(ESCO_DIR / "broaderRelationsSkillPillar_en.csv")
    name_by_uri = {}
    parents_by_uri = {}
    for row in relations.itertuples():
        name_by_uri[row.conceptUri] = row.conceptLabel
        name_by_uri[row.broaderUri] = row.broaderLabel
        parents_by_uri.setdefault(row.conceptUri, []).append(row.broaderUri)
    return name_by_uri, parents_by_uri


NAME_BY_URI, PARENTS_BY_URI = load_esco_tree()
URI_BY_NAME = {name: uri for uri, name in NAME_BY_URI.items()}


def paths_to_root(uri):
    """Ein Skill kann mehrere Eltern haben, daher mehrere Wege bis zur Wurzel."""
    parents = PARENTS_BY_URI.get(uri, [])
    if not parents:
        return [[uri]]
    paths = []
    for parent in parents:
        for path_above in paths_to_root(parent):
            paths.append([uri] + path_above)
    return paths


def depth_of_common_ancestor(path_a, path_b):
    from_root_a = list(reversed(path_a))
    from_root_b = list(reversed(path_b))
    depth = 0
    for node_a, node_b in zip(from_root_a, from_root_b):
        if node_a != node_b:
            break
        depth += 1
    return depth


def wu_palmer(path_a, path_b):
    return 2 * depth_of_common_ancestor(path_a, path_b) / (len(path_a) + len(path_b))


def wu_palmer_range(skill_a, skill_b):
    values = []
    for path_a in paths_to_root(URI_BY_NAME[skill_a]):
        for path_b in paths_to_root(URI_BY_NAME[skill_b]):
            values.append(wu_palmer(path_a, path_b))
    return min(values), max(values)


def tree_edges(skills):
    """Kanten Kind -> Elternteil als Namen, gleichnamige Knoten werden zu einem."""
    edges = set()
    for skill in skills:
        for path in paths_to_root(URI_BY_NAME[skill]):
            names = [NAME_BY_URI[uri] for uri in path]
            for child, parent in zip(names, names[1:]):
                if child != parent:
                    edges.add((child, parent))
    return sorted(edges)


def mermaid_diagram(edges):
    node_names = sorted({name for edge in edges for name in edge})
    node_id = {name: f"n{number}" for number, name in enumerate(node_names)}
    lines = ["graph BT"]
    for name in node_names:
        lines.append(f'    {node_id[name]}["{name}"]')
    for child, parent in edges:
        lines.append(f"    {node_id[child]} --> {node_id[parent]}")
    return "\n".join(lines)


def mermaid_live_link(diagram):
    editor_state = json.dumps({"code": diagram, "mermaid": '{"theme": "default"}'})
    compressed = zlib.compress(editor_state.encode())
    return "https://mermaid.live/edit#pako:" + base64.urlsafe_b64encode(compressed).decode()


print(f"{'Skill A':32}{'Skill B':30}{'Wu-Palmer min':>15}{'max':>6}")
for skill_a, skill_b in SKILL_PAIRS:
    lowest, highest = wu_palmer_range(skill_a, skill_b)
    print(f"{skill_a:32}{skill_b:30}{lowest:>15.2f}{highest:>6.2f}")

skills_in_pairs = {skill for pair in SKILL_PAIRS for skill in pair}
diagram = mermaid_diagram(tree_edges(skills_in_pairs))
print()
print(diagram)
print()
print(mermaid_live_link(diagram))
