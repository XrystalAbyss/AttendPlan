# AttendPlan Windows Credential Vault Architecture (F2-C)

## 1. Overview
AttendPlan uses the native Windows Credential Manager to provide hardware-backed and DPAPI-encrypted storage for sensitive student two-factor authentication secrets. By delegating secret persistence to the operating system's native vault, AttendPlan guarantees that zero plain-text secrets are ever written to application log files, SQLite databases, JSON configuration files, or Git repositories.

---

## 2. Vault Implementation & Architecture

### 2.1 Backend Adapter
- **Primary Backend**: `keyring.backends.Windows.WinVaultKeyring`
- **Underlying OS Mechanism**: Windows Data Protection API (DPAPI) via `CredWriteW` / `CredReadW` / `CredDeleteW`.
- **Target Vault Service Name**: `AttendPlan`
- **Primary Credential Key**: `student_totp_secret`

### 2.2 Fail-Closed Security Policy
AttendPlan enforces a strict **fail-closed** policy for credential storage:
```python
def is_secure_keyring_backend(backend: Any) -> bool:
    if backend is None:
        return False
    # Insecure plaintext backends must be rejected immediately
    backend_name = backend.__class__.__name__.lower()
    insecure_names = ("plaintext", "file", "null", "insecure", "unencrypted")
    if any(n in backend_name for n in insecure_names):
        return False
    # Priority check: standard secure platform backends have positive priority
    priority = getattr(backend, "priority", 0)
    return priority > 0
```
If an insecure file-based backend (such as `keyring.backends.file.PlaintextKeyring`) is loaded or if the platform keyring service is unresponsive, AttendPlan raises `SecureVaultUnavailableError` and refuses to persist, retrieve, or process secrets.

---

## 3. Metadata vs. Secret Separation

To maintain strict least-privilege data hygiene, secrets and non-sensitive configuration are strictly separated:

| Data Element | Storage Location | Encryption |
| :--- | :--- | :--- |
| **TOTP Secret Key (Base32)** | Windows Credential Manager | DPAPI Hardware/OS Encrypted |
| **Enrolled Timestamp** | `%LOCALAPPDATA%\AttendPlan\totp_metadata.json` | Plaintext JSON |
| **Account Name / Issuer** | `%LOCALAPPDATA%\AttendPlan\totp_metadata.json` | Plaintext JSON |
| **Algorithm / Digits / Period** | `%LOCALAPPDATA%\AttendPlan\totp_metadata.json` | Plaintext JSON |
| **Verified Status** | `%LOCALAPPDATA%\AttendPlan\totp_metadata.json` | Plaintext JSON |

### Zero-Plaintext Storage Guarantee
- No secret is ever written to `%LOCALAPPDATA%\AttendPlan\totp_metadata.json` or `settings.json`.
- Secrets exist in Python process memory only during the active cryptographic HMAC calculation ($\approx$ microseconds) and are purged immediately.
- Frontend API endpoints (`GET /api/auth/totp/status`) return status metadata, verified flags, and masked account identifiers, but **never** return secret keys or live OTP codes.

---

## 4. Vault Lifecycle Operations

### 4.1 Enrollment (`POST /api/auth/totp/enroll`)
1. Validates the Base32 secret format and algorithm parameters.
2. Performs test calculation using RFC 6238 engine.
3. Securely stores the secret in Windows Credential Manager via `keyring.set_password("AttendPlan", "student_totp_secret", secret)`.
4. Writes non-sensitive metadata to `totp_metadata.json`.

### 4.2 Drift Verification (`POST /api/auth/totp/verify`)
1. Retrieves secret from Windows Credential Manager.
2. Accepts a 6-digit test code supplied by the student from their Google Authenticator app.
3. Computes codes across time steps $T-1, T, T+1$ to verify zero clock skew.
4. Marks `is_verified: true` in metadata upon successful validation.

### 4.3 Inspection (`POST /api/auth/totp/inspect`)
1. Accepts raw Base32, standard `otpauth://`, migration URI `otpauth-migration://`, or uploaded QR screenshot.
2. Parses account candidate metadata in memory without saving to vault.
3. Returns account candidates to UI for student confirmation.

### 4.4 Purge / Deletion (`DELETE /api/auth/totp/enrollment`)
1. Removes `student_totp_secret` from Windows Credential Manager via `keyring.delete_password("AttendPlan", "student_totp_secret")`.
2. Deletes or clears `%LOCALAPPDATA%\AttendPlan\totp_metadata.json`.
