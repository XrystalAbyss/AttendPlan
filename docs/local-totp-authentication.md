# AttendPlan Local TOTP Authentication Architecture (F2-C)

## 1. Overview & Objectives
AttendPlan F2-C implements an offline, local-only Time-Based One-Time Password (TOTP) generation engine conforming strictly to RFC 6238. This allows students to automate the secondary authentication factor (Google Authenticator challenge) presented by the university's Keycloak identity provider without manual phone retrieval or typing.

---

## 2. Security Boundaries & Invariants
1. **Local-Only Secret Storage**: Authenticator secret keys are stored exclusively in the Windows Credential Manager (`WinVaultKeyring`).
2. **Fail-Closed Storage Policy**: If an encrypted OS-level keyring is unavailable (or if keyring attempts to fall back to an unencrypted plaintext store), AttendPlan **fails closed** and refuses to persist or process the secret.
3. **No Database or Disk Secret Leakage**: Secrets are never persisted in SQLite databases, JSON files, configuration files, or environment variables.
4. **No API or Network Exposure**: Secret keys and generated TOTP codes are generated purely in backend memory and are never returned in HTTP responses or exposed to frontend components.
5. **Origin Allowlisting**: Playwright MFA autofill is strictly constrained to explicitly allowlisted university authentication hosts (`usermanagement.icloudems.com`, `mrei.icloudems.com`).

---

## 3. RFC 6238 Engine Invariants
- **Time Step Period**: Default 30 seconds (standard for Google Authenticator).
- **HMAC Algorithms**: SHA-1 (Keycloak default), with SHA-256 and SHA-512 supported.
- **Code Length**: Standard 6 digits (8 digits supported for custom profiles).
- **Latency Safety Window**: If fewer than 4 seconds remain in the active window at the moment of automated generation, AttendPlan briefly delays until the start of the next 30-second window before submitting, preventing latency-induced rejection on university servers.
- **Clock Drift Verification**: Compares system clock against authoritative time intervals; raises `TotpClockSkewError` if local drift exceeds $\pm 60$ seconds.

---

## 4. Provisioning & Ingestion Formats
- **Offline QR Decoding**: Decodes PNG, JPEG, and WebP QR screenshots using OpenCV's `QRCodeDetector` locally in memory (max upload size capped at 5 MB).
- **Standard Provisioning URI**: `otpauth://totp/{Issuer}:{Account}?secret={Base32}&issuer={Issuer}&digits=6&period=30`.
- **Google Authenticator Export Migration**: Decodes and parses `otpauth-migration://offline?data=...` protobuf wire payloads in pure Python without third-party RPC dependencies.
- **Raw Base32 Input**: Normalizes uppercase strings, strips whitespace and hyphens, and validates the RFC 4648 Base32 alphabet `[A-Z2-7]`.
