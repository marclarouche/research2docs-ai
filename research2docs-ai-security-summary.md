# Research2Docs-AI Security Summary

Date: 2026-10-18. Scope: `src/`, `ui/`, `scripts/`, config, dependencies, git history. Checklist source: `security-tests.md`.
Tools were installed in a throwaway venv (Python 3.13, outside the project). The project `.venv` and `pyproject.toml` were not touched. No commits or pushes.

## Tools run

| Tool | Version | Target | Result |
|---|---|---|---|
| Bandit | 1.9.4 | src, ui, scripts (5,026 LOC) | 11 Low, 0 Medium, 0 High (all triaged, see below) |
| Semgrep | 1.181.0 | `p/python` + `p/security-audit` (201 rules, 57 files) | 0 findings |
| pip-audit | 2.10.1 | project `.venv` site-packages | No known vulnerabilities (local package skipped, not on PyPI) |
| Safety | 3.8.1 | `pip freeze` of project `.venv` (73 packages) | 0 vulnerabilities |
| Gitleaks | 8.30.1 (preinstalled) | git history (2 commits) | No leaks |
| Gitleaks | 8.30.1 | working dir | 3 hits, all false positives (see below) |
| `scripts/scan_secrets.py` (project's own) | n/a | tracked and untracked source snapshot | No leaks |
| Manual Streamlit review (grep + code read) | n/a | `ui/`, `src/` | No issues |

TruffleHog, git-secrets, Dependabot and Snyk were not run. Gitleaks covers the secret-scanning requirement, and Dependabot and Snyk are hosted services.

## Findings

| # | Severity | Location | Tool | Status |
|---|---|---|---|---|
| 1 | Low | `src/research2docs/ingestion/runner.py:5,52` (B404, B603) | Bandit | False positive, accepted |
| 2 | Low | `scripts/scan_secrets.py:7,19,45` (B404, B603, B607) | Bandit | False positive, accepted |
| 3 | Low | `scripts/smoke_test.py:29-47` (B101, 5x assert) | Bandit | False positive, accepted |
| 4 | Info | `outputs/gitleaks-manifest.json:41` (generic-api-key) | Gitleaks (dir) | False positive (gitignored) |
| 5 | Info | `.venv/share/jupyter/.../pydeck/index.js.map` (2 hits) | Gitleaks (dir) | False positive (third-party, gitignored) |

No Medium or High findings. No real vulnerabilities were found.

## What was fixed

No code or dependency changes were needed, so none were made.

## False positives and accepted risks

- **1, `runner.py` subprocess:** The command is a fixed argv list: `sys.executable -I -m research2docs.ingestion.worker` plus internally generated paths. There is no `shell=True` and no user-controlled executable. Stdin, stdout and stderr are discarded. The worker is sandboxed. `tests/security/test_ingestion_boundaries.py` covers timeout kill and reap, a memory monitor, and an audit hook that denies sockets and child execution.
- **2, `scripts/scan_secrets.py`:** This is a developer-run script. It runs `git` and `gitleaks` from fixed argv lists, with the gitleaks path resolved via `shutil.which`. It has no untrusted input. It also refuses symlinks and outside-root files.
- **3, `smoke_test.py` asserts:** This is a test script, so asserts are the intended behavior. It is not shipped in the app path.
- **4, gitleaks-manifest.json:** The flagged value is a SHA-256 file hash in a generated manifest. It is not a credential. The file is gitignored (`outputs/`) and not published.
- **5, pydeck source map:** This is a vendored third-party JS source map inside `.venv`, which is gitignored.

## Streamlit-specific checks (security-tests.md section 4)

- **`unsafe_allow_html` / XSS:** Not used anywhere in `ui/` or `src/`. Only `st.caption`, `st.write` and `st.code` render text. The HTML export uses Jinja2 `Environment(autoescape=True)` and a restrictive CSP meta tag (`default-src 'none'`).
- **Pickle / cache deserialization:** There is no `pickle`, `marshal`, `yaml.load`, `st.cache_data` or `st.cache_resource` in the code. Persistence is SQLite plus JSON.
- **Secrets:** There is no use of `st.secrets` and no hardcoded credentials. `.env*` and `.streamlit/secrets.toml` are gitignored. The Ollama connection is local (loopback only).
- **Auth:** The app has no authentication. The server binds to `127.0.0.1` (`.streamlit/config.toml` and `core/config.py`) and the app is single-user and local. `showErrorDetails="none"`, `gatherUsageStats=false` and `maxUploadSize=10` are set. See "Needs the owner" below.
- **Upload handling:** DOCX package validation covers zip-slip paths, symlinks, encrypted entries, vbaproject, expansion and ratio limits, and entry counts. Uploaded filenames never become filesystem paths (tested).

## Needs the owner / remaining

- **Authentication, only if the deployment model changes.** If the app is ever exposed beyond localhost (a non-loopback address or a shared host), put it behind an identity-aware proxy (OAuth2-Proxy, Keycloak, Authentik) or add `streamlit-authenticator`. This is not needed for the current loopback-only design.
- **Optional:** enable Dependabot or Snyk on the GitHub repo. This is hosted-service configuration and I did not set it up.
- The project dev tools list `pip-audit` in `pyproject.toml`. Running `uv`-based audits needs `uv`, which is not installed on this machine, so the audit used the installed `.venv` instead.

## Tests

- `pytest` (project `.venv`, Python 3.12.15): **212 passed**, 1 deselected (the optional `ollama` marker test), 5 warnings, with no code changes. Re-running the scanners after the test run gave the same results, because nothing changed.
- `git status` was clean before and after. The only new file is this report.
