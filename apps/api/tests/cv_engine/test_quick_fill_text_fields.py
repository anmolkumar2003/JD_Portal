"""Quick fill: names, location, company, title, skills, source, tags and hints."""

from typing import Any

import pytest

from app.cv_engine.quick_fill import MAX_CHARS, parse_quick_fill


def value_of(text: str, field: str) -> Any:
    return parse_quick_fill(text).value(field)


def name_of(text: str) -> tuple[Any, Any]:
    result = parse_quick_fill(text)
    return result.value("first_name"), result.value("last_name")


# --- Names ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "first", "last"),
    [
        ("Rahul Sharma, Pune, 5 years", "Rahul", "Sharma"),
        ("Name: Priya Nair", "Priya", "Nair"),
        ("my name is Amit Verma", "Amit", "Verma"),
        ("Mr. Suresh Kumar Iyer, 5 yrs", "Suresh Kumar", "Iyer"),
        ("candidate: Neha Gupta", "Neha", "Gupta"),
        ("first name: Anil, last name: Kapoor", "Anil", "Kapoor"),
        ("Sneha Rao | Pune | 3 yrs", "Sneha", "Rao"),
        ("ravi kumar from hyderabad", "Ravi", "Kumar"),
        ("Dr. Meera Krishnan, Chennai", "Meera", "Krishnan"),
        ("Ms Divya Menon, divya@x.com", "Divya", "Menon"),
        ("rahul sharma", "Rahul", "Sharma"),
        ("SNEHA PATEL", "Sneha", "Patel"),
        ("Pooja Singh-Rathore, Jaipur", "Pooja", "Singh-Rathore"),
        ("Anjali D'Souza, Goa", "Anjali", "D'Souza"),
        ("Mohammed Irfan Khan, Hyderabad", "Mohammed Irfan", "Khan"),
        ("Full name: Karan Malhotra", "Karan", "Malhotra"),
        ("Rahul Sharma is a senior java developer based in Pune", "Rahul", "Sharma"),
        ("C. Ramesh, Chennai", "C", "Ramesh"),
        ("Name - Asha Rani\nCity - Kochi", "Asha", "Rani"),
    ],
)
def test_name(text: str, first: str, last: str) -> None:
    assert name_of(text) == (first, last)


def test_a_single_known_first_name_gives_a_first_name_only() -> None:
    result = parse_quick_fill("Aarav, Mumbai, 3 yrs")

    assert result.value("first_name") == "Aarav"
    assert result.value("last_name") is None
    field = result.get("first_name")
    assert field is not None
    assert field.confidence == "medium"


@pytest.mark.parametrize(
    "text",
    [
        "Pune, 5 years",
        "Senior Java Developer",
        "Infosys",
        "5 years",
        "Java",
        "Product Manager",
        "current 8 LPA",
        "Mumbai",
        "Referral",
        "Engineering",
        "xyz",
    ],
)
def test_text_that_is_not_a_name_is_not_taken_as_one(text: str) -> None:
    first, last = name_of(text)

    assert first is None
    assert last is None


def test_two_possible_names_are_listed_and_neither_is_chosen() -> None:
    result = parse_quick_fill("Sneha Rao, Pune, Amit Shah, Delhi")

    for name in ("first_name", "last_name"):
        field = result.get(name)
        assert field is not None
        assert field.value is None
        assert len(field.candidates) == 2
        assert field.warning
    first = result.get("first_name")
    assert first is not None
    assert [c.display for c in first.candidates] == ["Sneha Rao", "Amit Shah"]


def test_an_unknown_lowercase_phrase_is_only_low_confidence() -> None:
    field = parse_quick_fill("xyz abc qwerty").get("first_name")

    assert field is not None
    assert field.confidence == "low"


def test_the_name_is_never_used_to_guess_other_fields() -> None:
    # Same text with different names: the other extracted fields must not change.
    a = parse_quick_fill("Rahul Sharma, Pune, 5 years, current 8 LPA, 30 days notice")
    b = parse_quick_fill("Priya Nair, Pune, 5 years, current 8 LPA, 30 days notice")

    def others(result: Any) -> dict[str, Any]:
        return {f.field: (f.value, f.confidence) for f in result.fields if "name" not in f.field}

    assert others(a) == others(b)


# --- Location ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "place"),
    [
        ("Rahul, Pune, 5 years", "Pune"),
        ("from Mumbai", "Mumbai"),
        ("based in Bengaluru", "Bengaluru"),
        ("Bangalore", "Bengaluru"),
        ("location: Hyderabad", "Hyderabad"),
        ("currently in Chennai", "Chennai"),
        ("Noida, Uttar Pradesh", "Noida, Uttar Pradesh"),
        ("Pune, Maharashtra, India", "Pune, Maharashtra"),
        ("residing in Kolkata", "Kolkata"),
        ("lives in Ahmedabad", "Ahmedabad"),
        ("city: Jaipur", "Jaipur"),
        ("Kochi; 4 years; 30 days notice", "Kochi"),
        ("Dubai", "Dubai"),
        ("current location - Gurgaon", "Gurugram"),
        ("Rahul Sharma from salem", "Salem"),
        ("PUNE", "Pune"),
        ("based out of Indore, MP", "Indore"),
    ],
)
def test_location(text: str, place: str) -> None:
    assert value_of(text, "current_location") == place


@pytest.mark.parametrize(
    "text",
    [
        "willing to relocate to Delhi",
        "native: Patna",
        "preferred location: Pune",
        "Rahul, 5 years",
        "Salem",
        "open to relocation in Mumbai",
        "hometown Lucknow",
    ],
)
def test_location_not_filled(text: str) -> None:
    assert value_of(text, "current_location") is None


def test_two_places_are_listed_not_guessed() -> None:
    field = parse_quick_fill("Pune, Mumbai").get("current_location")

    assert field is not None
    assert field.value is None
    assert {c.value for c in field.candidates} == {"Pune", "Mumbai"}


def test_current_location_beats_a_preferred_one() -> None:
    result = parse_quick_fill("from Pune, willing to relocate to Delhi")

    assert result.value("current_location") == "Pune"


# --- Company ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "company"),
    [
        ("works at Infosys", "Infosys"),
        ("Senior QA Engineer at TCS", "TCS"),
        ("company: Wipro", "Wipro"),
        ("currently working with Tata Consultancy Services", "TCS"),
        ("Infosys", "Infosys"),
        ("working at Acme Technologies Pvt Ltd as a data analyst", "Acme Technologies Pvt Ltd"),
        ("current company: Zoho Corporation", "Zoho Corporation"),
        ("employer: HCL", "HCL"),
        ("Rahul, Cognizant, 5 years", "Cognizant"),
        ("Amit @ Flipkart", "Flipkart"),
        ("employed at Razorpay", "Razorpay"),
        ("Rahul, Pune, Globex Solutions Pvt Ltd, 5 yrs", "Globex Solutions Pvt Ltd"),
        ("Organization: Deloitte", "Deloitte"),
        ("ex-Infosys, now at Swiggy", "Swiggy"),
        ("working for Capgemini since 2019", "Capgemini"),
        ("Senior Developer at Hooli Labs", "Hooli Labs"),
    ],
)
def test_company(text: str, company: str) -> None:
    assert value_of(text, "current_company") == company


@pytest.mark.parametrize(
    "text",
    [
        "Rahul, Pune, 5 years",
        "SAP consultant",
        "Oracle DBA",
        "works at Pune",
        "at 8 LPA",
        "Java Developer",
    ],
)
def test_company_not_filled(text: str) -> None:
    assert value_of(text, "current_company") is None


def test_a_past_employer_is_flagged_not_trusted() -> None:
    field = parse_quick_fill("ex-Infosys").get("current_company")

    assert field is not None
    assert field.confidence == "low"
    assert field.warning


# --- Title ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "title"),
    [
        ("Rahul, Senior Java Developer, Pune", "Senior Java Developer"),
        ("designation: Project Manager", "Project Manager"),
        ("working as a data analyst", "Data Analyst"),
        ("QA Engineer", "QA Engineer"),
        ("title: Lead Software Engineer II", "Lead Software Engineer II"),
        ("Senior QA Engineer at TCS", "Senior QA Engineer"),
        ("DevOps engineer", "DevOps Engineer"),
        ("role: UI/UX Designer", "UI/UX Designer"),
        ("currently working as an HR Executive", "HR Executive"),
        ("Product Manager | Pune", "Product Manager"),
        ("is a full stack developer", "Full Stack Developer"),
        ("Business Analyst, 6 yrs", "Business Analyst"),
        ("Head of Engineering", "Head of Engineering"),
        ("data scientist", "Data Scientist"),
        ("Rahul works as a Technical Recruiter at Naukri", "Technical Recruiter"),
        ("Sales Executive; 3 years; Mumbai", "Sales Executive"),
    ],
)
def test_title(text: str, title: str) -> None:
    assert value_of(text, "current_title") == title


@pytest.mark.parametrize(
    "text",
    [
        "Rahul Sharma",
        "Pune, 5 years",
        "applied for Senior Java Developer",
        "Infosys",
        "current 8 LPA",
        "wants to be a developer someday maybe",
    ],
)
def test_title_not_filled(text: str) -> None:
    assert value_of(text, "current_title") is None


# --- Skills and tags --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "skills"),
    [
        ("Skills: Java, Spring Boot, AWS", ["Java", "Spring Boot", "AWS"]),
        ("tech stack: python, django, postgres", ["Python", "Django", "PostgreSQL"]),
        ("Rahul, Python, SQL, 5 yrs", ["Python", "SQL"]),
        ("key skills - react, node, typescript", ["React", "Node.js", "TypeScript"]),
        ("Skills: Python; Excel; Communication", ["Python", "Excel", "Communication"]),
        ("expert in java and kubernetes", ["Java", "Kubernetes"]),
        ("knows docker", ["Docker"]),
        ("Skills: Go, R", ["Go", "R"]),
        ("Skill set: selenium, jira", ["Selenium", "Jira"]),
        ("primary skills: SAP FICO", ["SAP FICO"]),
        ("worked on react and angular projects", ["React", "Angular"]),
        ("Skills: Mulesoft", ["Mulesoft"]),
        ("python python PYTHON", ["Python"]),
        ("Java Developer", ["Java"]),
        ("Tableau, Power BI", ["Tableau", "Power BI"]),
    ],
)
def test_skills(text: str, skills: list[str]) -> None:
    value = value_of(text, "skills")

    assert value is not None
    assert [s.casefold() for s in value] == [s.casefold() for s in skills]


@pytest.mark.parametrize("text", ["Rahul, Pune", "go to the market", "r u there", "5 years"])
def test_skills_not_found(text: str) -> None:
    assert value_of(text, "skills") is None


@pytest.mark.parametrize(
    ("text", "tags"),
    [
        ("tags: hot, referral-ready", ["hot", "referral-ready"]),
        ("Tag: priority", ["priority"]),
        ("#priority #urgent", ["priority", "urgent"]),
        ("Rahul, Pune, #shortlist", ["shortlist"]),
        ("labels: senior, remote", ["senior", "remote"]),
        ("tags: A, B, a", ["a", "b"]),
        ("#top-talent", ["top talent"]),
    ],
)
def test_tags(text: str, tags: list[str]) -> None:
    value = value_of(text, "tags")

    assert value is not None
    assert sorted(value) == sorted(tags)


# --- Source, department, job -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "source"),
    [
        ("source: referral", "referral"),
        ("Source: LinkedIn", "linkedin"),
        ("sourced via linkedin", "linkedin"),
        ("referred by Mohan", "referral"),
        ("source - agency", "agency"),
        ("through consultancy", "agency"),
        ("walk-in", "manual"),
        ("source: career site", "career_site"),
        ("applied via career page", "career_site"),
        ("source: direct", "manual"),
        ("Referral from Priya", "referral"),
        ("from agency", "agency"),
    ],
)
def test_source(text: str, source: str) -> None:
    assert value_of(text, "source") == source


def test_an_unknown_source_asks_instead_of_guessing() -> None:
    field = parse_quick_fill("source: Naukri").get("source")

    assert field is not None
    assert field.value is None
    assert len(field.candidates) == 5


@pytest.mark.parametrize("text", ["Rahul, Pune", "linkedin.com/in/rahul", "the agency was nice"])
def test_source_not_filled(text: str) -> None:
    assert value_of(text, "source") is None


@pytest.mark.parametrize(
    ("text", "department"),
    [
        ("department: Engineering", "Engineering"),
        ("dept: sales", "Sales"),
        ("in the marketing department", "Marketing"),
        ("Finance team", "Finance"),
        ("for the HR department", "HR"),
        ("team: Customer Support", "Customer Support"),
    ],
)
def test_department_hint(text: str, department: str) -> None:
    assert value_of(text, "department_hint") == department


@pytest.mark.parametrize(
    ("text", "job"),
    [
        ("applied for Senior Java Developer", "Senior Java Developer"),
        ("job: Data Analyst", "Data Analyst"),
        ("applying for the QA Engineer role", "QA Engineer"),
        ("position applied: Product Manager", "Product Manager"),
        ("interested in Backend Engineer position", "Backend Engineer"),
        ("applied for DevOps Engineer, 5 yrs", "DevOps Engineer"),
    ],
)
def test_job_hint(text: str, job: str) -> None:
    assert value_of(text, "job_hint") == job


# --- Whole sentences, styles and robustness --------------------------------------------------


def test_the_example_sentence_from_the_form() -> None:
    result = parse_quick_fill(
        "Rahul Sharma, Pune, 5 years, current 8 LPA, expected 12 LPA, 30 days notice, "
        "rahul@mail.com"
    )

    assert result.value("first_name") == "Rahul"
    assert result.value("last_name") == "Sharma"
    assert result.value("current_location") == "Pune"
    assert result.value("total_experience_years") == 5.0
    assert result.value("current_ctc") == {"amount": 800000, "currency": "INR", "unit": "pa"}
    assert result.value("expected_ctc") == {"amount": 1200000, "currency": "INR", "unit": "pa"}
    assert result.value("notice_period_days") == 30
    assert result.value("email") == "rahul@mail.com"
    assert all(f.confidence == "high" for f in result.fields)
    assert result.ignored == []
    assert not result.multiple_candidates


def test_key_value_lines() -> None:
    result = parse_quick_fill(
        "Name: Priya Nair\nPhone: 98765 43210\nEmail: priya.n@gmail.com\n"
        "Location: Bangalore, Karnataka\nCurrent company: Infosys\n"
        "Designation: Senior Java Developer\nExp: 6.5 yrs\nCCTC: 18 LPA\nECTC: 24 LPA\n"
        "Notice: 60 days\nSkills: Java, Spring Boot, AWS"
    )

    assert result.value("first_name") == "Priya"
    assert result.value("phone") == "+91 98765 43210"
    assert result.value("current_location") == "Bengaluru, Karnataka"
    assert result.value("current_company") == "Infosys"
    assert result.value("current_title") == "Senior Java Developer"
    assert result.value("total_experience_years") == 6.5
    assert result.value("notice_period_days") == 60
    assert result.value("skills") == ["Java", "Spring Boot", "AWS"]


def test_semicolon_style() -> None:
    result = parse_quick_fill(
        "Amit Verma; Mumbai; Senior QA Engineer at TCS; 4 yrs exp; ctc 9.5 lakhs; "
        "expecting 14; np 1 month"
    )

    assert result.value("first_name") == "Amit"
    assert result.value("current_location") == "Mumbai"
    assert result.value("current_company") == "TCS"
    assert result.value("current_title") == "Senior QA Engineer"
    assert result.value("notice_period_days") == 30
    assert result.value("current_ctc") == {"amount": 950000, "currency": "INR", "unit": "pa"}
    assert result.value("expected_ctc") == {"amount": 1400000, "currency": "INR", "unit": "pa"}


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "\n\n\n",
        ",,,;;;",
        "😀😀😀",
        "रमेश कुमार, पुणे, 5 साल",
        "李雷, 北京, 5年",
        "Rahul 🙂 Sharma | Pune 📍 | 5y",
        "a" * (MAX_CHARS + 500),
        "9" * 1500,
        "@" * 500,
        "\x00\x01\x02 Rahul \x7f",
        "Rahul\r\nSharma\r\nPune",
        "NaN Infinity -1 1e999 0x10",
        "lakh lakh lakh crore crore",
        "-" * 800,
        "1,2,3,4,5,6,7,8,9,10,11,12" * 20,
    ],
)
def test_odd_input_never_crashes(text: str) -> None:
    result = parse_quick_fill(text)

    assert result.warnings or result.fields or result.ignored or not text.strip()


def test_too_long_input_is_cut_and_says_so() -> None:
    result = parse_quick_fill("Rahul Sharma, Pune, " + "x" * (MAX_CHARS + 10))

    assert result.truncated
    assert any("longer than" in w for w in result.warnings)
    assert result.value("current_location") == "Pune"


def test_empty_input_has_a_warning_and_no_fields() -> None:
    result = parse_quick_fill("  \n ")

    assert result.fields == []
    assert result.warnings


def test_emoji_only_input_says_there_is_no_readable_text() -> None:
    result = parse_quick_fill("😀🎉")

    assert result.fields == []
    assert any("No readable text" in w for w in result.warnings)


def test_unknown_words_are_reported_not_hidden() -> None:
    result = parse_quick_fill("Rahul Sharma, Pune, zzzz qqqq wwww")

    assert result.value("first_name") == "Rahul"
    assert any("zzzz" in piece for piece in result.ignored)


# --- Several candidates in one text -----------------------------------------------------------


def test_blank_line_separated_people_are_split_not_mixed() -> None:
    result = parse_quick_fill(
        "Rahul Sharma, rahul@x.com, 9876543210\n\nAmit Verma, amit@y.com, 9123456780"
    )

    assert result.multiple_candidates
    assert result.fields == []
    assert len(result.segments) == 2
    assert "rahul@x.com" in result.segments[0]
    assert "amit@y.com" in result.segments[1]


def test_repeated_name_lines_are_split() -> None:
    result = parse_quick_fill("Name: A B\nEmail: a@x.com\nName: C D\nEmail: c@y.com")

    assert result.multiple_candidates
    assert result.segments == ["Name: A B\nEmail: a@x.com", "Name: C D\nEmail: c@y.com"]


def test_one_person_per_line_is_split() -> None:
    result = parse_quick_fill("Rahul Sharma, r@x.com\nAmit Verma, a@y.com")

    assert result.multiple_candidates
    assert len(result.segments) == 2


def test_each_segment_extracts_cleanly_on_its_own() -> None:
    result = parse_quick_fill("Name: Anil Kapoor\nEmail: a@x.com\nName: Neha Gupta\nEmail: n@y.com")

    first = parse_quick_fill(result.segments[0])
    second = parse_quick_fill(result.segments[1])

    assert (first.value("first_name"), first.value("email")) == ("Anil", "a@x.com")
    assert (second.value("first_name"), second.value("email")) == ("Neha", "n@y.com")


def test_one_person_with_two_emails_is_not_called_several_people() -> None:
    result = parse_quick_fill("Priya, personal p@x.com, work p@work.com")

    assert not result.multiple_candidates


def test_a_normal_multi_line_profile_is_one_person() -> None:
    result = parse_quick_fill("Rahul Sharma\nrahul@x.com\n9876543210\nPune, 5 years")

    assert not result.multiple_candidates
    assert result.value("first_name") == "Rahul"


# --- Result shape -----------------------------------------------------------------------------


def test_every_field_has_a_reason_and_a_confidence() -> None:
    result = parse_quick_fill(
        "Rahul Sharma, Pune, 5 years, current 8 LPA, expected 12 LPA, 30 days notice, "
        "rahul@mail.com, +91 9876543210, linkedin.com/in/rahul, Python, Django"
    )

    assert result.fields
    for field in result.fields:
        assert field.confidence in {"high", "medium", "low"}
        assert field.reason
        assert field.display


def test_ambiguous_fields_have_no_value_but_do_have_choices_and_a_warning() -> None:
    result = parse_quick_fill("Rahul, 10 LPA, 9876543210 and 9123456780")

    for field in result.fields:
        if field.value is None:
            assert field.candidates
            assert field.warning


def test_fields_come_back_in_the_documented_order() -> None:
    result = parse_quick_fill("rahul@mail.com, Pune, Rahul Sharma, 5 years")

    names = [f.field for f in result.fields]
    assert names == sorted(names, key=names.index)
    assert names.index("first_name") < names.index("email") < names.index("current_location")
