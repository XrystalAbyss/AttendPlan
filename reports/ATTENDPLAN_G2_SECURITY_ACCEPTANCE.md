# AttendPlan — Phase G.2: Security & Privacy Acceptance Audit

**Document Reference:** `ATTENDPLAN_G2_SECURITY_ACCEPTANCE.md`  
**Phase:** G.2 Supervised Friends Beta & Release Hardening  
**Date:** 2026-11-07  
**Build Target:** `AttendPlan-0.1.0-beta.2-Setup.exe`  
**Status:** PASS — ALL SECURITY GATES VERIFIED  

---

## 1. Security Architecture & Threat Model

AttendPlan operates as a local-first application running on the student's personal machine. Its security architecture is governed by five non-negotiable principles:
1. **Loopback Binding Strictness:** The backend service binds exclusively to IPv4 `127.0.0.1` and never to wildcard interfaces (`0.0.0.0`).
2. **Drive-by & Cross-Origin Protection:** Any request to the `/api/` path is inspected for `Origin`, `Referer`, and `Sec-Fetch-Site`. Third-party websites cannot issue drive-by cross-origin requests to trigger local actions.
3. **Host Header Filtering:** `TrustedHostMiddleware` enforces an allowlist of `127.0.0.1`, `localhost`, and `testserver` to prevent DNS rebinding attacks.
4. **Credential Isolation (Zero Knowledge):** Student passwords, OTPs, TOTP seeds, and university portal cookies are never transmitted to any external server or saved in plaintext. Sensitive TOTP seeds are stored exclusively in the Windows Credential Manager (DPAPI-encrypted).
5. **Read-Only Portal Adapter:** AttendPlan never performs automated login form submission without explicit user opt-in, never stores student credentials in code or database, and never modifies attendance records on the university portal.

---

## 2. Hardened Security Controls Implemented in G.2

### 2.1 LocalOriginSecurityMiddleware

In Phase G.2, we implemented `LocalOriginSecurityMiddleware` in `backend/app/main.py`. This middleware evaluates all incoming requests to endpoints prefixed with `/api/`:

```python
class LocalOriginSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if path.startswith("/api/"):
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")
            sec_fetch_site = request.headers.get("sec-fetch-site")

            # 1. Reject explicitly cross-site requests
            if sec_fetch_site and sec_fetch_site == "cross-site":
                return JSONResponse(status_code=403, content={"detail": "Cross-origin request blocked: cross-site access prohibited."})

            # 2. Check Origin header
            if origin:
                parts = urlsplit(origin)
                if parts.hostname not in ALLOWED_LOOPBACK_HOSTS:
                    return JSONResponse(status_code=403, content={"detail": "Cross-origin request blocked: origin not permitted."})

            # 3. Check Referer header
            if referer:
                parts = urlsplit(referer)
                if parts.hostname not in ALLOWED_LOOPBACK_HOSTS:
                    return JSONResponse(status_code=403, content={"detail": "Cross-origin request blocked: referer not permitted."})

        return await call_next(request)
```

### 2.2 Security Verification Test Suite (`test_local_security_origin.py`)

A dedicated automated test suite verifies 5 key scenarios:
1. `test_loopback_origin_allowed`: Requests with `Origin: http://127.0.0.1:5173` or `http://localhost:8000` return 200.
2. `test_external_origin_forbidden`: Requests with `Origin: https://evil-phishing-site.com` return **403 Forbidden**.
3. `test_cross_site_sec_fetch_site_blocked`: Requests with `Sec-Fetch-Site: cross-site` return **403 Forbidden**.
4. `test_external_referer_forbidden`: Requests with `Referer: https://malicious.org/exploit` return **403 Forbidden**.
5. `test_non_api_route_bypasses_check`: Health check and static UI assets remain accessible to local browser contexts.

---

## 3. Privacy & Anti-Tamper Verification

| Security Domain | Specification Requirement | Verification Status |
| :--- | :--- | :--- |
| **No Automated Password Storage** | Passwords must never be stored on disk | VERIFIED — Zero password fields in schema or vault |
| **No External Telemetry** | No network requests to third-party tracking or analytics | VERIFIED — Zero external telemetry endpoints |
| **Local SQLite File Permissions** | Database stored in user profile directory `%LOCALAPPDATA%` | VERIFIED — Accessible only by the local Windows user |
| **Windows DPAPI Vault** | TOTP secrets stored via OS-backed keyring | VERIFIED — DPAPI encryption active via keyring |
| **Read-Only Portal Interaction** | Portal requests limited to GET / navigational evaluation | VERIFIED — Zero POST mutations to university portal |
| **No Hardcoded Student Data** | Zero personal student identifiers in codebase or git tracking | VERIFIED — `test_sanitization.py` passes 100% |

---

## 4. Security Sign-off for Private Friends Beta

Based on rigorous automated testing and static code analysis:
- **Loopback isolation:** CONFIRMED.
- **Drive-by attack vulnerability:** REMEDIATED & PASSING.
- **Data privacy:** 100% LOCAL-FIRST COMPLIANT.

AttendPlan `0.1.0-beta.2` meets all institutional privacy and security criteria for private supervised beta testing.

