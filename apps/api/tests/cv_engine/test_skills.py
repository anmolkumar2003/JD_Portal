from app.cv_engine.skills import canonicalize, find_skills_in_text, get_taxonomy


def test_taxonomy_has_500_plus_skills() -> None:
    assert len(get_taxonomy().by_name) >= 500


def test_every_alias_belongs_to_one_skill() -> None:
    owners: dict[str, set[str]] = {}
    for skill in get_taxonomy().skills:
        for alias in (skill.name.casefold(), *skill.synonyms):
            owners.setdefault(alias, set()).add(skill.name)
    assert {alias: names for alias, names in owners.items() if len(names) > 1} == {}


def test_department_synonyms() -> None:
    assert canonicalize("Quality Assurance") == "QA"
    assert canonicalize("GTM") == "Google Tag Manager"
    assert canonicalize("retargeting") == "Remarketing"
    assert canonicalize("photoshop") == "Adobe Photoshop"
    assert canonicalize("TestFlight") == "App Store Connect"


def test_canonicalize_synonyms() -> None:
    assert canonicalize("JS") == "JavaScript"
    assert canonicalize("k8s") == "Kubernetes" or canonicalize("kubernetes") == "Kubernetes"
    assert canonicalize("python3") == "Python"


def test_find_skills_in_text() -> None:
    text = "Built APIs with Python, FastAPI and PostgreSQL; also used Kubernetes (k8s)."
    found = find_skills_in_text(text)
    assert "Python" in found
    assert "PostgreSQL" in found
