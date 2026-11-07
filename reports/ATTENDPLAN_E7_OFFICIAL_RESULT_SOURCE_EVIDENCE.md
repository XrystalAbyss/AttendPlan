# AttendPlan Phase E.7 Source Evidence & Discovery Audit
## Supervised Live Inspection of University Official Results

**Date:** 2026-11-07  
**Student Profile Verified:** [REDACTED_STUDENT_IDENTITY] · B.Tech CSE AIML  
**Institution:** Manav Rachna Educational Institutions (MREI) · iCloudEMS  
**Target Scope:** Academic Year 2025–2026 · Semester 4 (Class 2508)  
**Evidence Artifacts:**
- Structured Capture Evidence: `reports/evidence/semester_4_official_result_source_evidence.json`
- Full Raw DOM Dump: `reports/evidence/semester_4_myreportcard_gu.html`
- Captured SHA-256 Checksum: `ac18b537058fdfe1c98db4b12026b0848b57bedcf630c480e09fbcb8648888a8`

---

## 1. Discovered Route Topography

During discovery (Budget: 1, Consumed: 1), AttendPlan inspected the student portal's navigation tree under the authenticated session. Two separate grades endpoints exist within iCloudEMS:

| Feature Label | Route Path | Purpose & Data Classification |
| :--- | :--- | :--- |
| **Performances** | `/corecampus/student/grades/new/myreportcard.php` | **Data Class A:** Continuous Evaluation / Internal Marks. Contains course assessment components (CE, CE 2, Mid-term, Viva, End Sem raw field). |
| **My Report Card** | `/corecampus/student/grades/myreportcard_gu.php` | **Data Class B:** Institutional Grade Card / Official Results. Dedicated COE interface for official grades, credits, SGPA, and CGPA. |

---

## 2. Forensic Source Inspection: `/grades/myreportcard_gu.php`

### Navigation Target
- URL: `https://mrei.icloudems.com/corecampus/student/grades/myreportcard_gu.php`
- HTTP Response: `200 OK`
- DOM Title: `My Report Card`

### Source Content Rendered
The portal page mounts the standard student identity header and navigation sidebar, but renders an explicit administrative deactivation block inside the main content container:

```html
<div class="col-md-12">
    <div class="alert alert-danger" role="alert" style="margin-top: 20px; font-size: 16px;">
        This page has been deactivated by the COE Office.Kindly contact the COE Office for activation or further assistance.
    </div>
</div>
```

### Forensic Hash Verification
- Checksum computed on raw extracted response body:
  `SHA-256: ac18b537058fdfe1c98db4b12026b0848b57bedcf630c480e09fbcb8648888a8`
- Retained in offline evidence store at `reports/evidence/semester_4_myreportcard_gu.html`.

---

## 3. Institutional Policy Context & Outcome Classification

Under Section 14 of the Phase E.7 engineering specification, this outcome represents:
- **Outcome C (WITHHELD)** & **Outcome D (SOURCE DEACTIVATED / UNAVAILABLE)**.

### Policy Rules Enforced:
1. **Never Fabricate Grades:** When the COE Office deactivates the official grade card interface, AttendPlan refuses to synthesize or infer letter grades (`O`, `A+`, `A`, `B+`, etc.) from internal assessment percentages.
2. **Never Speculate Grade Points:** Grade points (`10.0`, `9.0`, etc.) and SGPA/CGPA cannot be calculated without the official COE conversion schema and external examination marks (which remain withheld).
3. **Truthful Record Creation:** AttendPlan persists a `WITHHELD` publication checkpoint so the application accurately reflects the university's institutional status without crashing or generating false positives.

