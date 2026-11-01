"""Built-in skill/title aliases used when the DB seed is empty or as a bootstrap set."""

from __future__ import annotations

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
