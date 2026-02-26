# Contributing to TAOTF

*TAOTF is by [Vivid Studio](https://vividstudio.me).*

Thank you for considering contributing to **The Archive of the Future**. We welcome code, documentation, dataset improvements, and ideas that align with our data governance (anonymization, no resale, collective signal mapping).

## How to contribute

### Code

1. **Fork** the repository and create a branch from `main` (e.g. `feature/api-cache`, `fix/pipeline-resume`).
2. **Implement** your change. Keep the pipeline and API compatible with the existing JSONL schema.
3. **Test** locally: run `python index.py` (with a small test file if needed) and `uvicorn api:app --reload`.
4. **Open a Pull Request** with a short description and reference any issue.

### Documentation

- Fix typos or clarify README/API docs in the same way (fork → branch → PR).
- Dataset documentation lives in `docs/DATASET.md`.

### Data

- **Contributing wishes:** Use the API `POST /v1/contribute` or the Omnia gateway; do not submit PII.
- **Dataset corrections:** Open an issue describing the correction (e.g. schema, license, citation).

### Ideas and research

- Open a **Discussion** or **Issue** for research use cases, longitudinal analysis ideas, or collaboration.

## Code style

- **Python:** PEP 8; we use a single `requirements.txt` and no mandatory formatter in-repo (formatting in PRs is appreciated).
- **API:** FastAPI + Pydantic; keep responses aligned with the existing `/v1/*` schemas.

## What we don’t accept

- Code or data that re-identifies individuals or resells personal data.
- Breaking the existing JSONL schema without a clear migration path and discussion.

## License

By contributing, you agree that your contributions will be licensed under the same [MIT License](LICENSE) as the codebase. Dataset contributions are subject to the dataset license (CC BY 4.0) as described in [docs/DATASET.md](docs/DATASET.md).

---

*TAOTF — Mapping where humanity wants to go.*
