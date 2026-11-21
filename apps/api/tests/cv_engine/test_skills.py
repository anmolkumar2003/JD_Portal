from app.cv_engine.skills import canonicalize, find_skills_in_text, get_taxonomy


def test_taxonomy_has_500_plus_skills() -> None:
    assert len(get_taxonomy().by_name) >= 500


def test_canonicalize_synonyms() -> None:
    assert canonicalize("JS") == "JavaScript"
    assert canonicalize("k8s") == "Kubernetes" or canonicalize("kubernetes") == "Kubernetes"
    assert canonicalize("python3") == "Python"


def test_find_skills_in_text() -> None:
    text = "Built APIs with Python, FastAPI and PostgreSQL; also used Kubernetes (k8s)."
    found = find_skills_in_text(text)
    assert "Python" in found
    assert "PostgreSQL" in found
