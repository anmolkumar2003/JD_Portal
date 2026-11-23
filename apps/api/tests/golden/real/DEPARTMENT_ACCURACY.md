# Department golden CV accuracy

| File | Name | Email | Skills hit/exp | Exp yrs | ATS | Match | Misses | OCR |
| ---- | ---- | ----- | -------------- | ------- | --- | ----- | ------ | --- |
| content_writing.pdf | OK | aisha.khan@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| content_writing.docx | OK | aisha.khan@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| shopify.pdf | OK | rohan.mehta@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| shopify.docx | OK | rohan.mehta@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| ppc.pdf | OK | neha.kapoor@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| ppc.docx | OK | neha.kapoor@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| android.pdf | OK | arjun.patel@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| android.docx | OK | arjun.patel@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| ios.pdf | OK | meera.iyer@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| ios.docx | OK | meera.iyer@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| flutter.pdf | OK | kabir.singh@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| flutter.docx | OK | kabir.singh@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| quality_analyst.pdf | OK | sana.rahman@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| quality_analyst.docx | OK | sana.rahman@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| ux_design.pdf | OK | diya.nair@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| ux_design.docx | OK | diya.nair@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| project_manager.pdf | OK | vikram.desai@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| project_manager.docx | OK | vikram.desai@example.com | 5/5 | 6.9 | 100 | 100 | — | False |
| unusual_dates.pdf | OK | jane.unusual@example.com | 3/3 | 7.9 | 100 | 100 | — | False |
| scanned_unusual.pdf | OK | jane.unusual@example.com | 3/3 | 7.9 | 77 | 100 | — | True |
| two_column_shopify.pdf | OK | rohan.mehta@example.com | 4/5 | 13.5 | 68 | 88 | CSS | False |

```json
[
  {
    "file": "content_writing.pdf",
    "slug": "content_writing",
    "parsed_name": "Aisha Khan",
    "expected_name": "Aisha Khan",
    "email": "aisha.khan@example.com",
    "phone": "+91 98100 11101",
    "skills_found": 5,
    "skills_expected": [
      "Content Writing",
      "Copywriting",
      "SEO",
      "SEO Writing",
      "WordPress"
    ],
    "skills_hit": [
      "Content Writing",
      "Copywriting",
      "SEO",
      "SEO Writing",
      "WordPress"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 501
  },
  {
    "file": "content_writing.docx",
    "slug": "content_writing",
    "parsed_name": "Aisha Khan",
    "expected_name": "Aisha Khan",
    "email": "aisha.khan@example.com",
    "phone": "+91 98100 11101",
    "skills_found": 5,
    "skills_expected": [
      "Content Writing",
      "Copywriting",
      "SEO",
      "SEO Writing",
      "WordPress"
    ],
    "skills_hit": [
      "Content Writing",
      "Copywriting",
      "SEO",
      "SEO Writing",
      "WordPress"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 501
  },
  {
    "file": "shopify.pdf",
    "slug": "shopify",
    "parsed_name": "Rohan Mehta",
    "expected_name": "Rohan Mehta",
    "email": "rohan.mehta@example.com",
    "phone": "+91 98100 11102",
    "skills_found": 5,
    "skills_expected": [
      "CSS",
      "JavaScript",
      "Liquid",
      "Shopify",
      "Shopify Themes"
    ],
    "skills_hit": [
      "CSS",
      "JavaScript",
      "Liquid",
      "Shopify",
      "Shopify Themes"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 516
  },
  {
    "file": "shopify.docx",
    "slug": "shopify",
    "parsed_name": "Rohan Mehta",
    "expected_name": "Rohan Mehta",
    "email": "rohan.mehta@example.com",
    "phone": "+91 98100 11102",
    "skills_found": 5,
    "skills_expected": [
      "CSS",
      "JavaScript",
      "Liquid",
      "Shopify",
      "Shopify Themes"
    ],
    "skills_hit": [
      "CSS",
      "JavaScript",
      "Liquid",
      "Shopify",
      "Shopify Themes"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 516
  },
  {
    "file": "ppc.pdf",
    "slug": "ppc",
    "parsed_name": "Neha Kapoor",
    "expected_name": "Neha Kapoor",
    "email": "neha.kapoor@example.com",
    "phone": "+91 98100 11103",
    "skills_found": 5,
    "skills_expected": [
      "Google Ads",
      "Google Analytics",
      "PPC",
      "SEM",
      "SEO"
    ],
    "skills_hit": [
      "Google Ads",
      "Google Analytics",
      "PPC",
      "SEM",
      "SEO"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 488
  },
  {
    "file": "ppc.docx",
    "slug": "ppc",
    "parsed_name": "Neha Kapoor",
    "expected_name": "Neha Kapoor",
    "email": "neha.kapoor@example.com",
    "phone": "+91 98100 11103",
    "skills_found": 5,
    "skills_expected": [
      "Google Ads",
      "Google Analytics",
      "PPC",
      "SEM",
      "SEO"
    ],
    "skills_hit": [
      "Google Ads",
      "Google Analytics",
      "PPC",
      "SEM",
      "SEO"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 488
  },
  {
    "file": "android.pdf",
    "slug": "android",
    "parsed_name": "Arjun Patel",
    "expected_name": "Arjun Patel",
    "email": "arjun.patel@example.com",
    "phone": "+91 98100 11104",
    "skills_found": 5,
    "skills_expected": [
      "Android SDK",
      "Firebase",
      "Java",
      "Jetpack Compose",
      "Kotlin"
    ],
    "skills_hit": [
      "Android SDK",
      "Firebase",
      "Java",
      "Jetpack Compose",
      "Kotlin"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 495
  },
  {
    "file": "android.docx",
    "slug": "android",
    "parsed_name": "Arjun Patel",
    "expected_name": "Arjun Patel",
    "email": "arjun.patel@example.com",
    "phone": "+91 98100 11104",
    "skills_found": 5,
    "skills_expected": [
      "Android SDK",
      "Firebase",
      "Java",
      "Jetpack Compose",
      "Kotlin"
    ],
    "skills_hit": [
      "Android SDK",
      "Firebase",
      "Java",
      "Jetpack Compose",
      "Kotlin"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 495
  },
  {
    "file": "ios.pdf",
    "slug": "ios",
    "parsed_name": "Meera Iyer",
    "expected_name": "Meera Iyer",
    "email": "meera.iyer@example.com",
    "phone": "+91 98100 11105",
    "skills_found": 5,
    "skills_expected": [
      "Swift",
      "SwiftUI",
      "UIKit",
      "Xcode",
      "iOS"
    ],
    "skills_hit": [
      "Swift",
      "SwiftUI",
      "UIKit",
      "Xcode",
      "iOS"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 466
  },
  {
    "file": "ios.docx",
    "slug": "ios",
    "parsed_name": "Meera Iyer",
    "expected_name": "Meera Iyer",
    "email": "meera.iyer@example.com",
    "phone": "+91 98100 11105",
    "skills_found": 5,
    "skills_expected": [
      "Swift",
      "SwiftUI",
      "UIKit",
      "Xcode",
      "iOS"
    ],
    "skills_hit": [
      "Swift",
      "SwiftUI",
      "UIKit",
      "Xcode",
      "iOS"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 466
  },
  {
    "file": "flutter.pdf",
    "slug": "flutter",
    "parsed_name": "Kabir Singh",
    "expected_name": "Kabir Singh",
    "email": "kabir.singh@example.com",
    "phone": "+91 98100 11106",
    "skills_found": 5,
    "skills_expected": [
      "Dart",
      "Firebase",
      "Flutter",
      "Git",
      "REST"
    ],
    "skills_hit": [
      "Dart",
      "Firebase",
      "Flutter",
      "Git",
      "REST"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 470
  },
  {
    "file": "flutter.docx",
    "slug": "flutter",
    "parsed_name": "Kabir Singh",
    "expected_name": "Kabir Singh",
    "email": "kabir.singh@example.com",
    "phone": "+91 98100 11106",
    "skills_found": 5,
    "skills_expected": [
      "Dart",
      "Firebase",
      "Flutter",
      "Git",
      "REST"
    ],
    "skills_hit": [
      "Dart",
      "Firebase",
      "Flutter",
      "Git",
      "REST"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 470
  },
  {
    "file": "quality_analyst.pdf",
    "slug": "quality_analyst",
    "parsed_name": "Sana Rahman",
    "expected_name": "Sana Rahman",
    "email": "sana.rahman@example.com",
    "phone": "+91 98100 11107",
    "skills_found": 5,
    "skills_expected": [
      "Appium",
      "Cypress",
      "Jira",
      "QA",
      "Selenium"
    ],
    "skills_hit": [
      "Appium",
      "Cypress",
      "Jira",
      "QA",
      "Selenium"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 483
  },
  {
    "file": "quality_analyst.docx",
    "slug": "quality_analyst",
    "parsed_name": "Sana Rahman",
    "expected_name": "Sana Rahman",
    "email": "sana.rahman@example.com",
    "phone": "+91 98100 11107",
    "skills_found": 5,
    "skills_expected": [
      "Appium",
      "Cypress",
      "Jira",
      "QA",
      "Selenium"
    ],
    "skills_hit": [
      "Appium",
      "Cypress",
      "Jira",
      "QA",
      "Selenium"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 483
  },
  {
    "file": "ux_design.pdf",
    "slug": "ux_design",
    "parsed_name": "Diya Nair",
    "expected_name": "Diya Nair",
    "email": "diya.nair@example.com",
    "phone": "+91 98100 11108",
    "skills_found": 5,
    "skills_expected": [
      "Adobe XD",
      "Figma",
      "Prototyping",
      "UX Design",
      "Wireframing"
    ],
    "skills_hit": [
      "Adobe XD",
      "Figma",
      "Prototyping",
      "UX Design",
      "Wireframing"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 476
  },
  {
    "file": "ux_design.docx",
    "slug": "ux_design",
    "parsed_name": "Diya Nair",
    "expected_name": "Diya Nair",
    "email": "diya.nair@example.com",
    "phone": "+91 98100 11108",
    "skills_found": 5,
    "skills_expected": [
      "Adobe XD",
      "Figma",
      "Prototyping",
      "UX Design",
      "Wireframing"
    ],
    "skills_hit": [
      "Adobe XD",
      "Figma",
      "Prototyping",
      "UX Design",
      "Wireframing"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 476
  },
  {
    "file": "project_manager.pdf",
    "slug": "project_manager",
    "parsed_name": "Vikram Desai",
    "expected_name": "Vikram Desai",
    "email": "vikram.desai@example.com",
    "phone": "+91 98100 11109",
    "skills_found": 5,
    "skills_expected": [
      "Agile",
      "Jira",
      "Project Management",
      "Scrum",
      "Stakeholder Management"
    ],
    "skills_hit": [
      "Agile",
      "Jira",
      "Project Management",
      "Scrum",
      "Stakeholder Management"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 522
  },
  {
    "file": "project_manager.docx",
    "slug": "project_manager",
    "parsed_name": "Vikram Desai",
    "expected_name": "Vikram Desai",
    "email": "vikram.desai@example.com",
    "phone": "+91 98100 11109",
    "skills_found": 5,
    "skills_expected": [
      "Agile",
      "Jira",
      "Project Management",
      "Scrum",
      "Stakeholder Management"
    ],
    "skills_hit": [
      "Agile",
      "Jira",
      "Project Management",
      "Scrum",
      "Stakeholder Management"
    ],
    "skills_miss": [],
    "exp_years": 6.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 522
  },
  {
    "file": "unusual_dates.pdf",
    "slug": "unusual",
    "parsed_name": "Jane Unusual",
    "expected_name": "Jane Unusual",
    "email": "jane.unusual@example.com",
    "phone": "+91 99999 88877",
    "skills_found": 3,
    "skills_expected": [
      "Kotlin",
      "Python",
      "Shopify"
    ],
    "skills_hit": [
      "Kotlin",
      "Python",
      "Shopify"
    ],
    "skills_miss": [],
    "exp_years": 7.9,
    "ats": 100,
    "match": 100,
    "ocr": false,
    "chars": 368
  },
  {
    "file": "scanned_unusual.pdf",
    "slug": "unusual",
    "parsed_name": "Jane Unusual",
    "expected_name": "Jane Unusual",
    "email": "jane.unusual@example.com",
    "phone": "+91 99999 88877",
    "skills_found": 3,
    "skills_expected": [
      "Kotlin",
      "Python",
      "Shopify"
    ],
    "skills_hit": [
      "Kotlin",
      "Python",
      "Shopify"
    ],
    "skills_miss": [],
    "exp_years": 7.9,
    "ats": 77,
    "match": 100,
    "ocr": true,
    "chars": 379
  },
  {
    "file": "two_column_shopify.pdf",
    "slug": "shopify",
    "parsed_name": "Rohan Mehta",
    "expected_name": "Rohan Mehta",
    "email": "rohan.mehta@example.com",
    "phone": "+91 98100 11102",
    "skills_found": 5,
    "skills_expected": [
      "CSS",
      "JavaScript",
      "Liquid",
      "Shopify",
      "Shopify Themes"
    ],
    "skills_hit": [
      "JavaScript",
      "Liquid",
      "Shopify",
      "Shopify Themes"
    ],
    "skills_miss": [
      "CSS"
    ],
    "exp_years": 13.5,
    "ats": 68,
    "match": 88,
    "ocr": false,
    "chars": 434
  }
]
```
