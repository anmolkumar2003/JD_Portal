8. CV Intelligence Engine
Lives in apps/api/app/cv_engine/  as a pure Python package: extract.py , parser.py ,
skills.py , ats_check.py , matcher.py , explain.py . Executed by a Celery task
process_document(document_id) .
Pipeline
1. Validate: MIME and magic-byte check, size limit 5 MB, malware scan (ClamAV), page
count limit.
2. Extract text: PDF via pdfplumber, falling back to PyMuPDF; DOCX via python-docx; if
extracted text is under 200 characters, run Tesseract OCR and flag ocr_used .
3. Parse: section segmentation by headings, regex for email/phone/URLs/dates, spaCy
NER for names, orgs and locations, skill extraction against a taxonomy (synonym map
such as "JS" = "JavaScript", "k8s" = "Kubernetes"), experience date-range parsing to
compute total years (merging overlaps).
4. Normalize: canonical skill names, ISO dates, title normalization.
5. ATS check: run the checklist below on the file structure and parsed result.
6. Match: for each application on this candidate, compute the JD match.
7. Persist: write parsed_profiles , ats_checks , match_results ; update candidate
fields that are empty; emit an activity-log entry and a notification.
Parser adapter. Define CVParser  with parse(text, file) -> ParsedProfile . Ship
RuleBasedParser  first; later add AffinaParser , LLMParser  behind the same interface,
selected by config. If an LLM is used, validate its output against the Pydantic schema,
never send data to a provider without a privacy and DPA review, and log the parser
version.
8.1 ATS-friendliness checklist (score 0–100)
There is no universal ATS standard, so this is a documented heuristic. Each check has a
weight; the score is the weighted sum of passed checks.
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 12 of 27

Bands: 80–100 Good (green), 60–79 Needs improvement (amber), below 60 Poor (red).
Store the checks as JSON [{id, label, passed, weight, detail, suggestion}] .
8.2 JD match scoring (score 0–100)
Default weights (configurable per organization and overridable per job):
ID Check Weight Fail suggestion
A1 Text is extractable (not image-only
PDF)
15 Export as a text-based PDF or
DOCX
A2 Standard file type (PDF/DOCX) and
under 5 MB
5 Use PDF or DOCX
A3 Contact info parsed (name, email,
phone)
10 Put contact details in the body, not
the header/footer
A4 Standard section headings found
(Experience, Education, Skills)
15 Use conventional headings
A5 No multi-column or table layout
detected
10 Use a single-column layout
A6 No text boxes, images holding text,
or key info in headers/footers
8 Move content into the main body
A7 Dates consistently formatted and
parseable
7 Use "MMM YYYY – MMM YYYY"
A8 Work history has title, company and
dates per role
10 List title, company, dates on
separate clear lines
A9 Skills section present with
recognizable skills
7 Add a dedicated Skills section
A10 Reasonable length (1–4 pages) 5 Trim or condense
A11 No unusual characters, excessive
graphics, icons as bullets
4 Use standard bullets and fonts
A12 Parse completeness (share of
expected fields extracted)
4 Simplify the layout
Component Weight How computed
Required skills 40 matched required skills / total required (weighted
by skill weight); synonym-aware
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 13 of 27

overall = sum(component_score * weight) / 100 . Renormalize weights if a
component has no data (for example no preferred skills defined).
Hard filters (flags, not rejections): a missing mandatory requirement (for example a
mandatory certification or work authorization) shows a red flag chip but never auto-
rejects.
Progression: v1 keyword + synonym + TF-IDF; v2 adds sentence-transformer embeddings
(pgvector) for semantic skill and role similarity; v3 optional LLM to write the narrative
explanation (not to decide the score).
Explanation payload (stored in match_results.explanation ):
{
  "summary": "Strong match on backend skills; lacks Kubernetes and has 1.5 
years less experience than required.",
  "strengths": ["6 of 7 required skills", "Relevant fintech domain"],
  "concerns": ["No Kubernetes", "Notice period 90 days"],
  "component_scores": {"skills": 82, "experience": 65, "education": 100, 
"title": 74, "location": 90},
  "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
  "missing_required": ["Kubernetes"],
  "missing_preferred": ["Terraform"],
  "extra_skills": ["Go", "Kafka"],
  "score_version": "match-1.0"
}
Fairness and governance. Never use name, gender, age, photo, nationality or address as
features. Offer a blind-review toggle. Log engine version and input hash. Display "Score is
advisory; a recruiter makes the decision". Plan an annual bias review of score distributions
across groups where legally permitted.
Component Weight How computed
Preferred skills 10 matched preferred / total preferred
Experience 20 100 if within [min, max]; linear penalty below min;
mild penalty above max; also relevant-role-years
via title similarity
Title / domain relevance 10 similarity between candidate titles and job title
(TF-IDF now, embeddings later)
Education and
certifications
10 level meets requirement; certifications matched
Location / notice period 10 work-mode compatibility; notice period vs. target
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 14 of 27

Quality testing. Build a golden set of 50–100 CVs with hand-labeled fields; track parser
precision/recall per field in CI; fail the build if accuracy drops below thresholds.
