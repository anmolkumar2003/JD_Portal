# Department golden CV accuracy (parser rule-1.1)

Evaluated in-process: `extract_text` + `RuleBasedParser` + `run_ats_check` + `score_match` against a same-department required-skill job (min 3 years). Live DB untouched.

| File | Name | Email | Phone | Skills | Exp yrs | ATS | Match | Notes |
| ---- | ---- | ----- | ----- | ------ | ------- | --- | ----- | ----- |
| content_writing.pdf/docx | Aisha Khan | Y | Y | 5 | 6.9 | 100 | 89 | |
| shopify.pdf/docx | Rohan Mehta | Y | Y | 5 | 6.9 | 100 | 94 | |
| ppc.pdf/docx | Neha Kapoor | Y | Y | 5 | 6.9 | 100 | 94 | |
| android.pdf/docx | Arjun Patel | Y | Y | 5 | 6.9 | 100 | 94 | |
| ios.pdf/docx | Meera Iyer | Y | Y | 5 | 6.9 | 100 | 94 | |
| flutter.pdf/docx | Kabir Singh | Y | Y | 5 | 6.9 | 100 | 94 | |
| quality_analyst.pdf/docx | Sana Rahman | Y | Y | 5 | 6.9 | 100 | 100 | |
| ux_design.pdf/docx | Diya Nair | Y | Y | 5 | 6.9 | 100 | 91 | |
| project_manager.pdf/docx | Vikram Desai | Y | Y | 5 | 6.9 | 100 | 100 | |
| two_column_shopify.pdf | Rohan Mehta | Y | Y | 6 | 13.5* | 68 | 100 | ATS flags multi-column; exp inflated by column merge |
| unusual_dates.pdf/docx | Jane Unusual | Y | Y | 3 | 7.9 | 100 | — | Dates `01/15/2019 - current` / `Jan'19` parsed; sparse skills vs full Shopify JD |
| scanned_unusual.pdf | Jane Unusual | Y | Y | 3 | 7.9 | 77 | — | OCR path (`tesseract`); name + years OK |

\* Two-column extract merges left/right timelines; experience years can double-count.

Fixes in this pass: unusual date tokens, prefer multi-token names over truncated NER (`Jane` → `Jane Unusual`), taxonomy synonyms for QA/content/PM/analytics without alias collisions.
