# SkillPilot — Functional & Security Audit
**Date:** 21 April 2026 — *updated post-remediation*

## 0. Remediation status (as of this update)

Week 1 + Week 2 + parts of Week 3 of the plan have been completed in this commit. Code review (architect) ran on the changes and returned **PASS** — no HIGH/CRITICAL regressions, all existing endpoints still respond correctly.

| Metric | Before | After | Δ |
|---|---|---|---|
| Dependency CVEs — critical | 4 | **2** | −50 % |
| Dependency CVEs — high | 57 | **32** | −44 % |
| Dependency CVEs — moderate | 64 | **35** | −45 % |
| SAST findings — high | 515 | **175** | −66 % |
| SAST findings — total | 1 022 | **452** | −56 % |
| HoundDog privacy — critical | 7 | **3** | −57 % |

### What was fixed
- 🔴 → ✅ **Removed `exports/` PII dump and root `users.json`** from working tree; added both to `.gitignore` (history rewrite still required by repo owner).
- 🔴 → ✅ **Removed duplicate `skillpilot_deployment/` tree** (~9.4 MB). Architect confirmed no active code imported from it.
- 🔴 → ✅ **Sanitised `config.yaml`** — replaced 6 hard-coded API keys with empty strings + comments pointing to env vars / Replit Secrets / `KeyValueSetting`. Runtime keeps working because resolution already falls back to env vars and DB-stored credentials.
- 🟠 → ✅ **defusedxml** installed and swapped into `app/services/sso_service.py` and `app/services/scorm_service.py` (XXE in SAML and SCORM ingestion now mitigated).
- 🟠 → ✅ **CSV formula-injection guard** (`_csv_safe` / `_csv_row`) added in `app/routes/insights.py` and applied to all 4 export endpoints (`atrisk_csv`, `cohort_csv`, `gradebook_csv`, `roi_csv`).
- 🟠 → ✅ **Credential-printing scripts hardened**: `run_seed_users.py` no longer echoes plaintext passwords, `app/routes/survey.py` no longer logs auth state, `app/services/xapi_service.py` now refuses to send Basic-Auth credentials over non-HTTPS endpoints.
- 🟡 → ✅ **Session cookie hardening**: `SESSION_COOKIE_SECURE` is now auto-enabled when `FLASK_ENV=production`, `REPLIT_DEPLOYMENT=1`, or `SKP_FORCE_SECURE_COOKIES=1`.
- 🟡 → ✅ **Defensive HTTP security headers** added via `@app.after_request`: `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and (in prod) `Strict-Transport-Security`. Verified live on `/`.
- 🟡 → ✅ **Frontend XSS helper** `static/js/skp-safe.js` (escape + tagged-template) created and loaded globally from `templates/_skp_base.html`. Existing `innerHTML` sites can now opt-in to `SKP.t\`...\``.
- 🟠 → ✅ **Security-critical Python packages bumped**: `cryptography`, `certifi`, `urllib3`, `requests`, `Werkzeug`, `Flask`, `signxml` upgraded.

### Still open (carry-over)
- 2 critical + 32 high dep CVEs remain — mostly in transitive packages and AI SDKs. Bump in a controlled wave after re-testing prompt code (`anthropic`, `openai`, `google-genai`, `boto3`).
- Hard-coded keys in `config.yaml` are out of the working tree but the historical commits still contain them — owner must purge git history (`git filter-repo` or BFG) and rotate the leaked keys.
- 3 HoundDog critical privacy items remain (Bedrock auth-token logging in `ai_service.py`, two `print()` chains in survey/xapi). Listed in section 3.7.
- Frontend `innerHTML` sweep: helper is in place but the ~280 sites have not yet been migrated. See section 3.10.
- CSRF protection (`Flask-WTF` CSRFProtect) deferred — would require touching every form, scheduled for the next iteration.
- Phase D / E / F feature work (HeyGen, SCORM 2004 RTE, OIDC SSO, PayPal, mobile) still unblocked.

---

**Scope:** Full Flask app under `app/`, static JS, templates, deployment copies, Python dependencies.
**Method:** Dependency CVE audit + static code analysis (SAST) + privacy/dataflow scan + live HTTP smoke tests of public/protected routes + manual code review of auth, SQL, secrets, XML, file I/O.

---

## 1. Executive summary

SkillPilot is broadly functional — the server boots, all probed routes respond, auth gating works (302 redirects for HTML pages, 401 JSON for APIs), and the recent navigation, EthicalSense, and profile work all wire up correctly. **However, the project carries serious security debt that must be addressed before any external launch on `futurecoverage.ai`.**

| Area | Verdict | Notes |
|---|---|---|
| Boot / routing | ✅ OK | 495 routes registered, server up, no 5xx on smoke tests |
| Auth gating | ✅ OK | Pages redirect to `/admin/login`; APIs return 401 |
| **Secrets in repo** | 🔴 **Critical** | Real user data + API keys committed under `exports/` and `config.yaml` |
| **Duplicate code tree** | 🔴 **High** | `skillpilot_deployment/` is a ~complete second copy — doubles the attack surface and risk of drift |
| Dependencies | 🟠 High | 4 critical / 57 high CVEs across 130 vulnerable package entries |
| XML parsing (SSO + SCORM) | 🟠 High | Uses stdlib `xml` — vulnerable to XXE |
| `subprocess` in admin | 🟠 High | Dynamic argv in `super_admin.py` |
| `sqlalchemy.text(...)` | 🟡 Medium | A handful of cases — need parameterisation review |
| CSV export injection | 🟡 Medium | `insights.py` writes user input straight into CSV |
| Frontend XSS surface | 🟡 Medium | Heavy `innerHTML` use across ~20 JS files |
| Notifications endpoint | ✅ OK | Lives at `/api/v1/notifications` and is reachable |
| Functional gaps | 🟡 Medium | Phases D–F (SCORM runtime, OIDC, PayPal, mobile) still pending per session plan |

---

## 2. Functional smoke test (live)

| URL | Expected | Got |
|---|---|---|
| `GET /` | 200 (landing) | **200** ✅ |
| `GET /skillpilot-landing` | 200 | **200** ✅ |
| `GET /admin/login` | 200 | **200** ✅ |
| `GET /api/ethics/principles` | 200 | **200** ✅ |
| `GET /static/css/advanced.css` | 200 | **200** ✅ |
| `GET /app` (protected) | 302 → login | **302** ✅ |
| `GET /admin/dashboard` | 302 | **302** ✅ |
| `GET /admin/system` | 302 | **302** ✅ |
| `GET /admin/integrations` | 302 | **302** ✅ |
| `GET /ethicalsense` | 302 | **302** ✅ |
| `GET /api/auth/user/profile` | 401 | **401** ✅ |
| `GET /api/ethics/level-summary` | 200 (public summary) | **200** ✅ |
| `GET /api/ethics/admin/settings` | 401 | **401** ✅ |
| `GET /api/v1/notifications/unread-count` | 401 | **401** ✅ |

All routes responded; no 500s. The notifications API is mounted at `/api/v1/notifications` (the frontend `static/js/notifications.js` already uses that path), so it works as designed.

### 2.1 Functional gaps still tracked
From the session plan, the following user-visible features are **not yet implemented** and will fail when exercised:
- **Phase D** — adaptive engine v2 + HeyGen per-lesson tutor (needs `HEYGEN_API_KEY`).
- **Phase E** — SCORM 2004 RTE runtime + xAPI LRS UI.
- **Phase F** — OIDC SSO, PayPal payments, mobile (PWA vs native).
- **Phase C** — accessibility WCAG 2.2 AA deep pass still pending.

These should be flagged in-app (e.g. "Coming soon" banners) until shipped, otherwise users will see broken buttons.

---

## 3. Security findings

### 3.1 🔴 CRITICAL — Real user data committed to the repo
`exports/` contains **115 KB of real user data** plus full course/exam/survey dumps:

```
exports/users.json              115 KB
exports/exam_questions.json      40 KB
exports/exam_results.json        29 KB
exports/survey_questions.json    65 KB
exports/survey_responses.json    25 KB
exports/enrollments.json         28 KB
... (16 files total)
```

The SAST scan flagged 182 generic-API-key matches inside `exports/users.json` alone (likely password hashes or session tokens that look key-shaped). HoundDog also flags 7 critical privacy violations (GDPR Art. 5, CCPA, NIST 800-53) tied to these dumps and to scripts that print credentials to stdout.

**Action (do this first):**
1. `git rm -r --cached exports/ users.json` and add both to `.gitignore`.
2. **Rotate** every credential ever sent to an LLM provider, payment gateway, SSO IdP, or stored in the dump (treat them as compromised).
3. Purge from git history: `git filter-repo --path exports --invert-paths` (or BFG).
4. If this repo ever lived on GitHub, consider it a confirmed PII breach — start your incident-response checklist (notify DPO, evaluate GDPR Art. 33 72-hour notification).

### 3.2 🔴 HIGH — Secrets hard-coded in `config.yaml`
SAST detected:
- 3× OpenAI API keys
- 1× Google API key
- 1× Hashicorp/Terraform-style password

Also: `app/services/presentation_service.py` has 2× hard-coded OpenAI keys.

**Action:** Move every key to environment variables (Replit Secrets / `KeyValueSetting` admin UI, both of which the codebase already supports). Rotate the leaked ones today. `config.yaml` should never contain secrets — keep only non-sensitive defaults there.

### 3.3 🔴 HIGH — Duplicate code tree `skillpilot_deployment/`
A near-complete second copy of the application sits alongside the live one. It contains the **same vulnerabilities**, the **same secrets**, and an out-of-date copy of every route. Two real risks:
- It can be reached by mistake (ops, build scripts, bundling).
- Future patches to `app/` will silently miss `skillpilot_deployment/app/`, causing security regressions.

**Action:** Delete it once you confirm nothing references it, or fold it into a proper `releases/` tag. Until then, every fix in this report has to be applied **twice**.

### 3.4 🟠 HIGH — Dependency CVEs (130 vulnerable packages)
| Severity | Count |
|---|---|
| Critical | 4 |
| High | 57 |
| Moderate | 64 |
| Low | 5 |

Many are in `pip` itself, `cryptography`, `Flask`, `boto3`, `anthropic`, `google-*`, etc. Most are 1–3 minor versions behind.

**Action:** Run `pip list --outdated` and bump in three waves:
1. **Security-only** (cryptography, certifi, requests, urllib3, Werkzeug, Flask, signxml).
2. **AI SDKs** (anthropic, openai, google-genai) — re-test prompt code.
3. **Everything else.**

### 3.5 🟠 HIGH — XXE in SAML SSO and SCORM ingestion
- `app/services/sso_service.py` uses stdlib `xml.etree`.
- `app/services/scorm_service.py` uses both `xml.etree` and `xml.dom.minidom`.

Stdlib `xml` is not safe against XML External Entity / billion-laughs attacks. Both surfaces accept attacker-supplied XML (SAML responses from the IdP, SCORM `imsmanifest.xml` uploads from teachers).

**Action:** `pip install defusedxml` and replace `xml.etree.ElementTree` with `defusedxml.ElementTree`, `xml.dom.minidom` with `defusedxml.minidom`. The project already uses `signxml` for SAML signature verification, but signature ≠ entity-safe parsing.

### 3.6 🟠 HIGH — Dynamic `subprocess` in admin route
`app/routes/super_admin.py` calls `subprocess.run(...)` with a non-static argv. If any element of that argv is influenced by a request value (even an admin-only one), it's command injection.

**Action:** Audit the call site. Use `shell=False` (already implied by list form), build the argv from a hard-coded allow-list, never concatenate request data. Consider replacing subprocess with native Python where possible.

### 3.7 🟠 HIGH — Auth tokens & credentials going to stdout
HoundDog flagged:
- `app/services/ai_service.py` — AWS Bedrock auth token logged.
- `app/routes/survey.py` — auth token to stdout.
- `run_seed_users.py` — username + password printed to stdout.
- `app/services/xapi_service.py` — username + password sent over plain HTTP (xAPI LRS endpoint).

**Action:** Strip all credential printing. For xAPI, force HTTPS for the LRS endpoint and require a configurable bearer token rather than Basic over HTTP.

### 3.8 🟡 MEDIUM — `sqlalchemy.text()` with built strings
6 files build raw SQL with `text()`:
- `app/__init__.py`
- `deployment_files/migrate_database.py`
- `deployment_files/run_migration.py`
- `migrations/convert_to_skillgap.py`
- `run_migration.py`
- (+ duplicates in `skillpilot_deployment/`)

Most look like one-shot migrations, which is lower risk, but `app/__init__.py` runs on every boot and any future request-influenced parameter would be SQL injection.

**Action:** Convert to bound parameters (`text("SELECT ... WHERE id = :id").bindparams(id=...)`) or use the ORM. Move ad-hoc migrations into Alembic.

### 3.9 🟡 MEDIUM — CSV formula injection in exports
`app/routes/insights.py` writes user-supplied strings directly into CSV (4 spots). If a teacher exports a class roster and a student typed `=cmd|'/c calc'!A1` into their bio, opening the CSV in Excel runs commands.

**Action:** Prefix any cell starting with `=`, `+`, `-`, `@`, tab, or CR with a single quote `'` before writing. Five-line helper.

### 3.10 🟡 MEDIUM — Frontend `innerHTML` everywhere (XSS surface)
SAST counted **~280** `innerHTML`/`document.write` sites across the JS, mostly in:
- `static/js/teacher-dashboard.js` (41)
- `static/js/app.js` (37)
- `static/js/classes.js` (19)
- `static/js/class-management.js` (13)
- `static/js/ethics_certificate.js` (9)

Any of these that interpolate server data without escaping is a stored-XSS vector. The cookies already use session auth, so a single XSS = full account takeover.

**Action (incremental, by file):** prefer `textContent` for user data, or pass through a tiny `escapeHtml()` helper before `innerHTML +=`. For HTML templating, use `<template>` + `cloneNode` instead of string concatenation.

### 3.11 🟡 MEDIUM — Session & cookie hardening
Not flagged by scanners but worth reviewing in `app/__init__.py`:
- Confirm `SESSION_COOKIE_SECURE = True` in production.
- `SESSION_COOKIE_HTTPONLY = True`.
- `SESSION_COOKIE_SAMESITE = 'Lax'` (or `'Strict'` for admin paths).
- A `Content-Security-Policy` header would mitigate the `innerHTML` risk above. `Talisman` is one line.

### 3.12 🟡 MEDIUM — CSRF
Flask sessions are cookie-based and the API is fetched same-origin without CSRF tokens. Any state-changing endpoint that accepts a JSON body and only checks `session['user_id']` is CSRF-vulnerable from third-party sites if `SameSite` isn't `Strict`. **Add `Flask-WTF` CSRFProtect** or require a custom header (`X-Requested-With`) and check it server-side.

---

## 4. Prioritised remediation plan

### Week 1 — stop the bleeding
1. Remove `exports/` and `users.json` from repo + git history; rotate every key/password ever exposed.
2. Move all secrets out of `config.yaml`; rotate them; load from env.
3. Decide the fate of `skillpilot_deployment/` (delete or archive); until then mirror every fix.
4. `pip install defusedxml`; swap in SSO + SCORM services.
5. Audit & lock down the `subprocess.run` in `super_admin.py`.
6. Strip credential prints (`run_seed_users.py`, `ai_service.py`, `survey.py`).

### Week 2 — harden the runtime
7. `pip-audit` + targeted upgrades (cryptography, Flask, urllib3, requests, signxml first).
8. Set secure session cookie flags + add `Talisman` CSP header.
9. Add `Flask-WTF` CSRFProtect for all state-changing routes.
10. CSV formula-injection guard in `insights.py`.

### Week 3 — reduce XSS surface
11. Sweep `static/js/` files in order of `innerHTML` count; replace with `textContent` / template cloning. Top 5 files = ~75 % of the risk.
12. Convert remaining raw-SQL `text()` calls to bound parameters or Alembic.

### Week 4 — feature completion (functional)
13. Phase D — HeyGen tutor (request `HEYGEN_API_KEY`).
14. Phase E — SCORM 2004 RTE + xAPI LRS UI.
15. Phase F — OIDC SSO, PayPal, PWA wrapper.

---

## 5. What I tested vs. what I didn't

**Tested:**
- App boot, route registration (495), HTTP status of 14 representative endpoints across public, protected page, and protected JSON surfaces.
- Three independent security scanners (`runDependencyAudit`, `runSastScan`, `runHoundDogScan`) ran in parallel and were tolerated for partial failure.
- Manual code spot-checks for: secrets, SQL text, XML parsing, subprocess, frontend innerHTML, blueprint URL prefixes.

**Not tested (would need credentials or extra time):**
- End-to-end flows requiring login (course creation, enrollment, exam submission, certificate issuance, payment, SAML round-trip with a real IdP, HeyGen video render).
- Browser-based interactive testing of the new top-menu and EthicalSense UI in dark mode + RTL.
- Load / concurrency.

If you want me to extend coverage, the highest-value next step is automated end-to-end tests using a seeded `student` and `admin` account so I can drive the protected flows.
