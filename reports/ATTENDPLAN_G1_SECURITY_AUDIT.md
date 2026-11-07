# AttendPlan Phase G.1 — Security, Privacy & Integrity Audit Report

## 1. Audit Scope & Security Boundaries

AttendPlan is engineered under strict local-first, privacy-first invariants. The purpose of this Phase G.1 audit was to ensure that packaging the application for general student release does not introduce data leakage, insecure network bindings, credential disclosure, or unauthorized file access.

The audit examined:
1. **Packaging Cleanliness**: Guarantee that no developer data, personal databases, cookies, or logs are shipped in the release binary.
2. **Localhost Network Binding**: Verification that the packaged server binds strictly to `127.0.0.1` and resists DNS rebinding.
3. **Privilege Scoping**: Assurance that neither the installer nor the application requires administrator rights.
4. **Credential Isolation**: Verification that TOTP secrets utilize Windows DPAPI keyring storage and never persist in plaintext.
5. **Data Provenance**: Preservation of existing multi-semester records across application lifecycles.

---

## 2. Artifact Cleanliness & Anti-Leakage Audit

A comprehensive scan was conducted across all files inside the compiled distribution `dist/AttendPlan` and the final installer `release-candidates/AttendPlan-0.1.0-beta.1-Setup.exe`.

### 2.1 File Extension Audit
```python
forbidden_exts = ['.sqlite3', '.db', '.wal', '.shm', '.key', '.pem', '.env']
```
- **Results**: `0` forbidden files discovered.
- **Verification**: The developer's live database `attendplan.sqlite3` was NOT bundled into the installer.

### 2.2 Student PII & Sensitive String Audit
Text, data, and asset files inside the packaged bundle were scanned for student identification tokens:
- Scanned for roll number prefixes: `2023MRU*`, `2024MRU*`, `2025MRU*`.
- Scanned for developer account identifiers and local usernames.
- **Results**: `0` sensitive entries found across all distribution assets.

---

## 3. Network & Process Isolation Audit

### 3.1 Loopback Interface Enforcement
The desktop launcher (`backend/launcher.py`) and FastAPI entrypoint (`backend/app/main.py`) strictly enforce loopback binding:
- **Binding Address**: `127.0.0.1`
- **Port**: `8000`
- **External Exposure**: The server **never** binds to `0.0.0.0` or broadcast addresses. Remote network machines cannot connect to AttendPlan.

### 3.2 DNS Rebinding Protection
FastAPI enforces `TrustedHostMiddleware`:
```python
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["127.0.0.1", "localhost", "testserver"],
)
```
Any HTTP request with a spoofed or external `Host:` header is rejected at the ASGI layer with HTTP 400 Bad Request before processing.

---

## 4. Privilege & Storage Architecture

### 4.1 Lowest Privilege Execution (`PrivilegesRequired=lowest`)
- The installer runs entirely in standard user space.
- It requires **zero administrator elevation** or UAC prompts.
- It installs to `%LOCALAPPDATA%\AttendPlan\app\`, inside the user's personal profile directory.
- It writes Start Menu shortcuts to `{userprograms}\AttendPlan` without touching system-wide `C:\ProgramData` or `C:\Program Files`.

### 4.2 Credential Protection via Windows DPAPI
TOTP secrets stored via the application vault use Python `keyring` backed by the native Windows Data Protection API (DPAPI):
- Keys are encrypted with the logged-in Windows user's cryptographic master key.
- No other Windows user account on the same machine can decrypt the stored TOTP secret.
- Plaintext secrets are never stored in SQLite, config files, or application logs.

### 4.3 Database Lifecycle & Upgrade Safety
The SQLite database resides strictly outside the application binary directory:
- **Database Location**: `%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3`
- **Application Binary Location**: `%LOCALAPPDATA%\AttendPlan\app\`
- **Impact of Application Updates**: Installing a newer version of AttendPlan overwrites only the binary directory in `app\`, leaving the student's historical attendance records, term mappings, and performance snapshots untouched.
- **Impact of Application Uninstallation**: The uninstaller removes binaries from `app\`, explicitly preserving `%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3` unless the student manually removes it.

---

## 5. Audit Conclusion

The Phase G.1 packaging satisfies all security and privacy criteria:
- **PII Leakage**: `0` leaks.
- **Network Boundaries**: `127.0.0.1` only.
- **Administrator Privileges**: None required.
- **Data Persistence**: Safe, isolated, and immutable across upgrades.

