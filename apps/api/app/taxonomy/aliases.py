"""Built-in skill/title aliases used when the DB seed is empty or as a bootstrap set."""

from __future__ import annotations

import re

# alias (casefolded key) -> canonical display label
SKILL_ALIASES: dict[str, str] = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "psql": "PostgreSQL",
    "react.js": "React",
    "reactjs": "React",
    "vue.js": "Vue",
    "vuejs": "Vue",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "py": "Python",
    "golang": "Go",
    "tf": "Terraform",
    "aws": "Amazon Web Services",
    "gcp": "Google Cloud",
    "azure": "Microsoft Azure",
    "ml": "Machine Learning",
    "ai": "Artificial Intelligence",
    "nlp": "Natural Language Processing",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "rest": "REST",
    "graphql": "GraphQL",
}


def canonicalize_skill(raw: str) -> str:
    key = raw.strip().casefold()
    return SKILL_ALIASES.get(key, raw.strip())


# Comparison-only aliases: folding spelling variants before set membership tests.
# These never change what is stored or displayed.
_COMPARE_ALIASES: dict[str, str] = {
    "postgres": "postgresql",
    "psql": "postgresql",
    "js": "javascript",
    "ts": "typescript",
    "k8s": "kubernetes",
    "golang": "go",
    "ml": "machinelearning",
    "node": "nodejs",
    "node.js": "nodejs",
    "c++": "cplusplus",
    "c#": "csharp",
    ".net": "dotnet",
}


def skill_tokens(name: str) -> list[str]:
    """Split a skill name into normalized tokens (case folded, aliases folded)."""
    parts = [p for p in re.split(r"[^a-z0-9+#.]+", name.lower().strip()) if p]
    return [_COMPARE_ALIASES.get(p, p) for p in parts]


def skill_key(name: str) -> str:
    """Normalized comparison key for a skill name."""
    return " ".join(skill_tokens(name))


def same_skill(a: str, b: str) -> bool:
    return bool(a) and skill_key(a) == skill_key(b)
