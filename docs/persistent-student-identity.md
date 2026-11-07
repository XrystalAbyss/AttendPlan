# AttendPlan Persistent Student Identity & Local Settings (F2-C)

## 1. Overview
The university's Keycloak identity provider (`usermanagement.icloudems.com`) mandates entering a registered 10-digit mobile number as the primary identifier before initiating multi-factor authentication. To prevent redundant manual data entry while maintaining complete student privacy, AttendPlan provides a persistent local identity configuration service.

---

## 2. Storage Architecture & Location

Persistent configuration is saved strictly to the user's local application data folder:
```
%LOCALAPPDATA%\AttendPlan\settings.json
```
(Typically resolving to `C:\Users\<Username>\AppData\Local\AttendPlan\settings.json`).

### Non-Sensitive Settings Schema:
```json
{
  "mobile_number": "9876543210",
  "auto_mobile_autofill": true,
  "auto_login_continuation": true,
  "created_at": "2026-10-19T18:00:00Z",
  "updated_at": "2026-10-19T18:00:00Z"
}
```

---

## 3. Privacy & Security Invariants

1. **Local-Only Boundary**:
   The student's mobile number is strictly stored on the local filesystem. It is never transmitted to any third-party analytics, remote cloud servers, telemetry endpoints, or external APIs.
2. **Dedicated Delivery Target**:
   The stored number is only submitted to the official, verified university Keycloak login form (`https://usermanagement.icloudems.com/auth/realms/...`) during an authorized login sequence.
3. **No Repository Commitment**:
   `settings.json` is located outside the Git repository tree. Even if a local copy is placed in testing roots, all `.gitignore` rules prevent repository tracking.
4. **Safe UI Masking**:
   When returned through API endpoints (`GET /api/settings/public`), the mobile number is masked to protect against shoulder surfing:
   ```json
   {
     "mobile_number": "******3210",
     "is_configured": true,
     "auto_mobile_autofill": true,
     "auto_login_continuation": true
   }
   ```
5. **Full Student Control**:
   The student can inspect, update, or completely clear their saved mobile identity at any time via **Settings > Authentication > Mobile Identity** or via `POST /api/settings` with an empty string.

---

## 4. Input Validation & Normalization

Indian mobile phone numbers conform to the National Numbering Plan (10 digits starting with 6, 7, 8, or 9). AttendPlan enforces deterministic normalization:
- Strips non-digit characters, spaces, and hyphens.
- Strips international prefixes (`+91` or `0`).
- Validates that the normalized string is exactly 10 digits matching regex `^[6-9]\d{9}$`.
- Rejects non-conforming or synthetic dummy numbers that violate format specifications.
