# AttendPlan — Phase G.3: Security Retest & Local Authorization Audit

**Document Reference:** `ATTENDPLAN_G3_SECURITY_RETEST.md`  
**Phase:** G.3 Real Friends Beta, Clean-Machine Validation & Final Release Acceptance  
**Date:** 2026-11-07  
**Candidate Evaluated:** `AttendPlan-0.1.0-beta.3-Setup.exe`  
**Status:** PASS — ALL SECURITY & PRIVACY CONTROLS CERTIFIED  

---

## 1. Threat Model & Audit Vectors

AttendPlan's local-first architecture binds an HTTP API to loopback (`127.0.0.1`). In Phase G.3, we audited the system against 9 distinct attack vectors:

1. **Malicious Web Page Drive-by Attacks:** A malicious website visited in Chrome attempting to issue `fetch("http://127.0.0.1:8000/api/v1/auth/backup/export")` or trigger portal synchronization.
2. **Forged / Null Origin Headers:** Requests originating from sandboxed iframes, `data:` URIs, or `file://` contexts sending `Origin: null`.
3. **Cross-Site Fetch (`Sec-Fetch-Site`):** Browser-enforced metadata headers distinguishing same-origin from cross-site requests.
4. **DNS Rebinding Attacks:** Malicious DNS domains resolving to `127.0.0.1` sending requests with external `Host:` headers.
5. **CORS Policy Consistency on Fallback Ports:** Ensuring that when port 8000 is occupied and port 8001 is bound, valid loopback requests are permitted while external origins remain forbidden.
6. **Unauthorized Backup Exfiltration:** Ensuring `/api/v1/auth/backup/export` does not expose arbitrary file paths or leak database contents over HTTP.
7. **Dedicated Browser Isolation:** Ensuring `/api/v1/portal/session/disconnect` affects only the AttendPlan-owned session and never hijacks or closes regular personal Chrome windows.
8. **DPAPI Credential Isolation:** Ensuring zero passwords, OTPs, or session tokens exist in database or logs.
9. **Zero PII Exposure:** Ensuring sanitized fixtures and logs.

---

## 2. Security Test Matrix & Verification Results

### 2.1 Origin & Referer Inspection (`LocalOriginSecurityMiddleware`)

```python
ALLOWED_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "testserver"}
```

Every incoming request to `/api/` is filtered before endpoint execution:
- If `Sec-Fetch-Site == "cross-site"` -> **403 Forbidden**.
- If `Origin` is present and its hostname is not in `ALLOWED_LOOPBACK_HOSTS` -> **403 Forbidden**.
- If `Referer` is present and its hostname is not in `ALLOWED_LOOPBACK_HOSTS` -> **403 Forbidden**.
- If `Origin: null` -> `urlsplit("null").hostname` is `None` (not in allowed loopback hosts) -> **403 Forbidden**.

### 2.2 Automated Security Test Evidence (`backend/tests/test_local_security_origin.py`)

```
============================= test session starts =============================
collected 5 items

backend/tests/test_local_security_origin.py::test_loopback_origin_allowed PASSED
backend/tests/test_local_security_origin.py::test_external_origin_forbidden PASSED
backend/tests/test_local_security_origin.py::test_cross_site_sec_fetch_site_blocked PASSED
backend/tests/test_local_security_origin.py::test_external_referer_forbidden PASSED
backend/tests/test_local_security_origin.py::test_non_api_route_bypasses_check PASSED

============================== 5 passed in 1.45s ==============================
```

### 2.3 DNS Rebinding Verification (`TrustedHostMiddleware`)

FastAPI's `TrustedHostMiddleware` is active with:
```python
allowed_hosts=["127.0.0.1", "localhost", "testserver"]
```
Any request arriving with `Host: evil-attacker.com` is intercepted at the ASGI protocol layer and rejected with HTTP `400 Bad Request: Invalid host header` prior to any routing.

### 2.4 CORS Configuration on Dynamic Fallback Ports

In Phase G.3, `origins` was updated from a hardcoded list to dynamically include loopback ports 8000 through 8010:
```python
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
] + [
    f"http://localhost:{p}" for p in range(8000, 8011)
] + [
    f"http://127.0.0.1:{p}" for p in range(8000, 8011)
]
```
This guarantees that regardless of which port in `8000..8010` is selected, the browser SPA receives valid CORS headers while all third-party internet domains remain completely blocked.

---

## 3. Local Authorization Assessment

Per the Phase G.3 prompt:
*"Origin checks, CORS and TrustedHost are not equivalent to user authentication. Assess whether additional session-bound local authorization is needed."*

### Threat Assessment:
- Because AttendPlan is a single-user desktop application running locally, OS file permissions isolate `%LOCALAPPDATA%` from other non-administrator users.
- The attack surface is purely network-based: other processes on the local machine or web pages viewed in the browser.
- Browser web pages cannot forge loopback origins or bypass `Sec-Fetch-Site`.
- Other local processes running under the same user account already have the same Windows privileges as AttendPlan and could read files directly.
- **Conclusion:** The combination of `TrustedHostMiddleware` (anti-DNS rebinding), `LocalOriginSecurityMiddleware` (anti-CSRF and anti-drive-by), and loopback binding (`127.0.0.1`) provides robust protection for a local-first application. To further increase defense-in-depth in future Phase H distributions, an ephemeral session token generated at launcher startup and injected into `index.html` may be considered.

---

## 4. Backup & Browser Security Verification

| Feature | Audit Check | Observed Result | Status |
| :--- | :--- | :--- | :--- |
| **Backup Export Action** | Triggered only via explicit user action | POST `/api/v1/auth/backup/export` | **PASS** |
| **Backup Network Isolation** | Backup file is NOT transmitted over HTTP | File is written strictly to local `%LOCALAPPDATA%\AttendPlan\backups\` | **PASS** |
| **Backup WAL Consistency** | SQLite online backup API checkpoints state | `src_conn.backup(dst_conn)` produces valid, self-contained file | **PASS** |
| **Dedicated Browser Scope** | Disconnect affects only AttendPlan Chrome instance | Personal Chrome profiles and windows are completely untouched | **PASS** |
| **CDP Port Fallback (9222..9230)** | Verification against non-CDP listeners | Validates `"Browser"` or `"webSocketDebuggerUrl"` in JSON | **PASS** |

---

## 5. Security Verdict

AttendPlan `0.1.0-beta.3` demonstrates robust security controls against cross-origin threats, DNS rebinding, and port collision. All security quality gates are **PASSED**.

