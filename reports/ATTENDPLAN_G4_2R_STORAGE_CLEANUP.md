# AttendPlan — Phase G.4.2R Storage Cleanup & Reclaim Report

**Date:** November 14, 2026  
**Phase:** G.4.2R (Storage Cleanup & Local Optimization)  
**Workspace:** `C:\Users\astra\Desktop\Project\AttendPlan`  

---

## 1. Executive Summary

As authorized in Phase G.4.2R, obsolete and superseded beta installer binaries and regenerable build caches were safely removed to optimize local disk utilization while preserving:
1. Complete cryptographic checksums and build metadata in `release-candidates/RELEASE_MANIFEST.json`.
2. Historical reference installer `beta.4` and `beta.5`.
3. Rollback candidate `beta.6` (`c2d7a5274c72ff79f43a31b702e68eb0bcf96e7dc7417a6a4dd08191057d16cc`).
4. Newly qualified active friends-beta candidate `beta.7` (`31f3a966681297b0959dd4fc9d10e04160a041d363aacc7750d3bbf1ed38c1d4`).
5. Live user database (`%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3`), WAL/SHM journals, and browser profile cookies/vault.

---

## 2. Storage Inventory & Space Reclaimed

### A. Obsolete Binaries Removed
| File Removed | Size (Bytes) | Size (MB) | Reason for Removal | Status in Manifest |
| :--- | :--- | :--- | :--- | :--- |
| `AttendPlan-0.1.0-beta.1-Setup.exe` | 81,630,124 | 77.85 MB | Superseded obsolete prototype | `HISTORICAL_REMOVED` |
| `AttendPlan-0.1.0-beta.2-Setup.exe` | 81,636,792 | 77.85 MB | Superseded obsolete prototype | `HISTORICAL_REMOVED` |
| `AttendPlan-0.1.0-beta.3-Setup.exe` | 81,644,316 | 77.86 MB | Superseded obsolete prototype | `HISTORICAL_REMOVED` |
| **Subtotal Binaries Reclaimed** | **244,911,232** | **233.56 MB** | | |

### B. Regenerable Build Caches Cleaned
| Cache Directory Removed | Size (Bytes) | Size (MB) | Purpose |
| :--- | :--- | :--- | :--- |
| `build/` (PyInstaller workpath) | 40,424,926 | 38.55 MB | Regenerable intermediate CArchive/PKG files |
| **Subtotal Caches Reclaimed** | **40,424,926** | **38.55 MB** | |

### C. Total Space Reclaimed
$$\text{Total Space Reclaimed} = 244,911,232 + 40,424,926 = \mathbf{285,336,158\text{ bytes (272.12 MB)}}$$

---

## 3. Retained Artifacts Status

| Artifact | Size (Bytes) | SHA-256 Hash | Role |
| :--- | :--- | :--- | :--- |
| `AttendPlan-0.1.0-beta.4-Setup.exe` | 81,650,698 | `160664cdb70f068f142c0611398b1f1bb579b38ee47dc2dc7d1bf7bd87df1486` | Historical baseline |
| `AttendPlan-0.1.0-beta.5-Setup.exe` | 81,653,350 | `ca31c1d34e8d902eaffbc0710e94bcdc6afe2baee77fe3611608cabe1e6d6aa8` | Historical baseline |
| `AttendPlan-0.1.0-beta.6-Setup.exe` | 81,653,549 | `c2d7a5274c72ff79f43a31b702e68eb0bcf96e7dc7417a6a4dd08191057d16cc` | Qualified Rollback Candidate |
| `AttendPlan-0.1.0-beta.7-Setup.exe` | 81,704,034 | `31f3a966681297b0959dd4fc9d10e04160a041d363aacc7750d3bbf1ed38c1d4` | Active Qualified Friends Beta Candidate |

---

## 4. Registry Integrity Verification

1. `release-candidates/SHA256SUMS.txt` was refreshed to strictly index physically existing installer binaries (`beta.4`, `beta.5`, `beta.6`, `beta.7`), ensuring deterministic validation without missing-file errors.
2. `release-candidates/RELEASE_MANIFEST.json` preserves all cryptographic hashes and dimensions for removed historical binaries with explicit audit annotations (`HISTORICAL_REMOVED`).
3. Zero student data or database files were touched during this cleanup operation.
