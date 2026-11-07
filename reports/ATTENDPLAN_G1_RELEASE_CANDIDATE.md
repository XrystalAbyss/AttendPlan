# AttendPlan Phase G.1 — Release Candidate Specification & Verification

## 1. Release Candidate Identity

- **Product Name**: AttendPlan
- **Version**: `0.1.0-beta.1`
- **Distribution Stage**: Local Release Candidate (RC1)
- **Target OS**: Windows 10 / Windows 11 (64-bit AMD64 / Intel x86_64)
- **Distribution Scope**: Friends-Beta / Supervised User Validation (Local Only)
- **Build Timestamp**: 2026-11-07T15:48:23Z

---

## 2. Release Artifacts & Checksum Manifest

All release artifacts are compiled and stored in `release-candidates/`:

| Artifact Filename | Type | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| `AttendPlan-0.1.0-beta.1-Setup.exe` | Inno Setup Installer | 81,630,124 (77.8 MB) | `8ca484102a83739165cae2f81c07b0448f987abb6708e47893d13c1d3adbdbcc` |
| `RELEASE_MANIFEST.json` | JSON Metadata | 533 bytes | — |
| `SHA256SUMS.txt` | Checksum File | 101 bytes | — |

---

## 3. System Requirements & Operational Specifications

### 3.1 Minimum System Requirements
- **Operating System**: Windows 10 (Build 19041+) or Windows 11 (64-bit).
- **Processor**: Intel Core i3 / AMD Ryzen 3 or compatible 64-bit processor.
- **Memory (RAM)**: 4 GB minimum (8 GB recommended).
- **Available Disk Space**:
  - Installer download: ~80 MB.
  - Installed application: ~200 MB.
  - Database & logs: ~10 MB.
- **Browser Requirement**: Any modern Chromium-based browser (Google Chrome or Microsoft Edge pre-installed on Windows).
- **Administrative Privileges**: **None** (per-user installation).

### 3.2 Network Requirements
- **Runtime API**: Binds strictly to `127.0.0.1:8000` (loopback only, zero inbound internet exposure).
- **Outbound Connectivity**: Required only when the user explicitly triggers university portal sync (`mrei.icloudems.com` / `usermanagement.icloudems.com`).
- **Telemetry / Cloud Services**: **Zero**. No external analytics, telemetry, or remote servers.

---

## 4. Academic Data Preservation Guarantee

Throughout the development and packaging of Phase G.1, all pre-existing academic records were audited and preserved with zero data loss:

| Scope | Metric | Target | Verified in Main DB | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Academic Terms** | Verified Term Count | 5 terms | 5 terms | **PASSED** |
| **Catalog Courses** | Cumulative Courses | 76 courses | 76 courses | **PASSED** |
| **Attendance Observations** | Day-Wise Periods | 3,544 periods | 3,544 periods | **PASSED** |
| **Performance Snapshots** | Saved Marks Terms | 5 snapshots | 5 snapshots | **PASSED** |
| **Assessment Cells** | Verified Total Cells | 468 cells | 468 cells | **PASSED** |
| **Semester 1 Cells** | 2024–2025 S1 (918) | 66 cells | 66 cells | **PASSED** |
| **Semester 2 Cells** | 2024–2025 S2 (1048) | 108 cells | 108 cells | **PASSED** |
| **Semester 3 Cells** | 2025–2026 S3 (1067) | 117 cells | 117 cells | **PASSED** |
| **Semester 4 Cells** | 2025–2026 S4 (2508) | 165 cells | 165 cells | **PASSED** |
| **Semester 5 Cells** | 2026–2027 S5 (2582) | 12 cells | 12 cells | **PASSED** |
| **Database Integrity** | `PRAGMA integrity_check` | `ok` | `ok` | **PASSED** |
| **Foreign Key Integrity** | `PRAGMA foreign_key_check` | `[]` (empty) | `[]` (empty) | **PASSED** |

---

## 5. Release Candidate Verification Signoff

The AttendPlan Phase G.1 Release Candidate has successfully cleared every automated quality gate:
- **330 Backend Pytest Unit & Domain Tests**: 100% Passed.
- **38 Frontend Vitest Unit & Component Tests**: 100% Passed.
- **SPA Static Frontend Delivery**: Verified (`200 OK`, `index.html` fallback).
- **Silent Installation & Uninstallation**: Verified (`0` exit codes, proper file cleanup).
- **Clean-User Sandbox Cold Launch**: Verified (`4 kB` fresh DB initialization, zero crashes).
- **Security & Privacy Audit**: Verified (`0` PII leaks, `0` bundled private databases).

**Phase G.1 Release Candidate is approved for local beta testing.**

