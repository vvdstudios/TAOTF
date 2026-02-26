# TAOTF — Open Source Readiness Checklist (Silicon Valley Style)

This document tracks what is **done** and what is **missing** to make TAOTF a strong, research-grade open source project. Use it as a roadmap and for external evaluators.

---

## ✅ Done

| Item | Status |
|------|--------|
| **LICENSE** (MIT for code) | ✅ In repo root |
| **README** with vision, install, usage, API, data governance | ✅ |
| **CONTRIBUTING.md** with how to contribute code/data/docs | ✅ |
| **Dataset documentation** (schema, pillars, license, citation) | ✅ `docs/DATASET.md` |
| **.env.example** (no secrets committed) | ✅ |
| **requirements.txt** (pipeline + API) | ✅ |
| **REST API** (FastAPI) with docs, CORS, pagination, stats | ✅ `api.py` |
| **Contribute endpoint** (submit future intentions without PII) | ✅ `POST /v1/contribute` |
| **Data governance stated** (anonymization, no resale, collective mapping) | ✅ README + DATASET.md |

---

## 🔲 Missing (recommended next steps)

### Code & quality

| Item | Priority | Notes |
|------|----------|--------|
| **Automated tests** | High | Unit tests for pipeline (pre_filter, parsing), API (endpoints, stats logic). |
| **CI (GitHub Actions or similar)** | High | Run tests on push/PR; optional lint (ruff/black). |
| **Type hints** | Medium | Full typing in `index.py` and `api.py` for maintainability. |
| **Pre-commit or CI lint** | Medium | Ruff/Black + isort so contributions stay consistent. |

### Security & operations

| Item | Priority | Notes |
|------|----------|--------|
| **SECURITY.md** | Medium | How to report vulnerabilities; no PII in issues. |
| **Rate limiting on API** | Medium | Especially on `/v1/contribute` and public `/v1/signals` to avoid abuse. |
| **API authentication** | Low | Optional API key or OAuth for write/admin if you expose publicly. |
| **Dependency scanning** | Low | Dependabot or similar for `requirements.txt`. |

### Dataset & research

| Item | Priority | Notes |
|------|----------|--------|
| **Stable dataset releases** | High | Versioned releases (e.g. `taotf-signals-2026.1.jsonl`) on GitHub Releases or Zenodo with DOI. |
| **Data statement / datasheet** | Medium | Short “Datasheet for Datasets” style: motivation, composition, collection, preprocessing, uses, limitations. |
| **Optional anonymized public export** | Medium | Script or artifact that strips or generalizes `_raw_text` for maximum privacy in public share. |
| **Citation file (CFF)** | Low | `CITATION.cff` in repo root for tools and Zenodo. |

### Community & discoverability

| Item | Priority | Notes |
|------|----------|--------|
| **CODE_OF_CONDUCT.md** | Medium | Contributor Covenant or similar. |
| **Issue / PR templates** | Low | `.github/ISSUE_TEMPLATE`, `.github/PULL_REQUEST_TEMPLATE.md`. |
| **Badges** | Low | CI status, license, version in README (optional). |
| **Changelog (CHANGELOG.md)** | Low | Human-readable list of changes per version. |

### Product & docs

| Item | Priority | Notes |
|------|----------|--------|
| **OpenAPI export** | Low | `GET /openapi.json` is default with FastAPI; document in README. |
| **Docker / Docker Compose** | Low | Optional container for API + data dir for easy “run and try”. |
| **Longitudinal docs** | Medium | How to use TAOTF for time-series (e.g. by `_written_at` or release version). |

---

## Summary: “What’s missing”

**To be “Silicon Valley style” and research-grade:**

1. **Tests + CI** — So contributors and users trust changes.
2. **Stable, versioned dataset releases** — With clear license (CC BY 4.0) and citation.
3. **SECURITY.md + optional rate limiting** — For safe public API.
4. **CODE_OF_CONDUCT + optional issue/PR templates** — For community health.
5. **Data statement / anonymized export option** — For transparency and privacy.

The repo is already **open source ready** for early adopters and research use; the checklist above gets it to **production-style** open source and longitudinal research use.

---

*TAOTF — The Archive of the Future. VERSION: 2026.1. By [Vivid Studio](https://vividstudio.me).*
