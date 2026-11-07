"""Unit tests for QRParserAdapter, Google migration payloads, and provisioning inputs."""

import base64
import pytest

from app.adapters.qr_parser import (
    QRParserAdapter,
    clean_base32_secret,
)
from app.domain.totp_models import (
    TotpEnrollmentError,
    TotpInvalidSecretError,
)

SYNTHETIC_BASE32 = "JBSWY3DPEHPK3PXP"


def test_clean_base32_secret():
    """Verify normal Base32 cleaning and character set enforcement."""
    # Spaces, dashes, lowercase
    assert clean_base32_secret("jbsw y3dp-ehpk 3pxp") == SYNTHETIC_BASE32
    assert clean_base32_secret("JBSWY3DPEHPK3PXP===") == SYNTHETIC_BASE32

    # Invalid characters (0, 1, 8, 9, punctuation)
    with pytest.raises(TotpInvalidSecretError, match="Base32 secrets must only contain"):
        clean_base32_secret("JBSWY3DPEHPK3PX8")  # '8' is not base32
    with pytest.raises(TotpInvalidSecretError, match="TOTP secret cannot be empty"):
        clean_base32_secret("   ")



def test_parse_standard_otpauth_uri():
    """Verify standard RFC 6238 otpauth://totp/ URI parsing."""
    uri = f"otpauth://totp/iCloudEMS:student123@university?secret={SYNTHETIC_BASE32}&issuer=iCloudEMS&digits=6&period=30&algorithm=SHA1"
    candidates = QRParserAdapter.parse_provisioning_input(uri)
    assert len(candidates) == 1
    c = candidates[0]
    assert c.issuer == "iCloudEMS"
    assert c.account_name == "student123@university"
    assert c.secret_base32 == SYNTHETIC_BASE32
    assert c.digits == 6
    assert c.period == 30
    assert c.algorithm == "SHA1"
    assert c.source_type == "STANDARD_TOTP"
    assert c.masked_account == "st***ty"


def test_parse_manual_base32_secret():
    """Verify raw Base32 input parsing."""
    candidates = QRParserAdapter.parse_provisioning_input(SYNTHETIC_BASE32)
    assert len(candidates) == 1
    c = candidates[0]
    assert c.secret_base32 == SYNTHETIC_BASE32
    assert c.source_type == "MANUAL_BASE32"


def test_parse_google_authenticator_migration_payload():
    """Verify parsing of Google Authenticator export migration protobuf wire payload."""
    # Build a synthetic OtpParameters protobuf message:
    # field 1 (secret): length-delimited bytes -> b"Hello!\xde\xad" (Base32: JBSWY3DPEHPK3PXP)
    # field 2 (name): string -> "student@univ.edu"
    # field 3 (issuer): string -> "iCloudEMS"
    # field 4 (algorithm): varint -> 1 (SHA1)
    # field 5 (digits): varint -> 1 (6 digits)
    # field 6 (type): varint -> 2 (TOTP)
    raw_secret = base64.b32decode(SYNTHETIC_BASE32)
    name_bytes = "student@univ.edu".encode("utf-8")
    issuer_bytes = "iCloudEMS".encode("utf-8")


    param_buf = bytearray()
    # field 1: tag = (1 << 3) | 2 = 10 (0x0A)
    param_buf.append(0x0A)
    param_buf.append(len(raw_secret))
    param_buf.extend(raw_secret)

    # field 2: tag = (2 << 3) | 2 = 18 (0x12)
    param_buf.append(0x12)
    param_buf.append(len(name_bytes))
    param_buf.extend(name_bytes)

    # field 3: tag = (3 << 3) | 2 = 26 (0x1A)
    param_buf.append(0x1A)
    param_buf.append(len(issuer_bytes))
    param_buf.extend(issuer_bytes)

    # field 4 (algo): tag = (4 << 3) | 0 = 32 (0x20), val = 1
    param_buf.append(0x20)
    param_buf.append(0x01)

    # field 5 (digits): tag = (5 << 3) | 0 = 40 (0x28), val = 1
    param_buf.append(0x28)
    param_buf.append(0x01)

    # field 6 (type): tag = (6 << 3) | 0 = 48 (0x30), val = 2
    param_buf.append(0x30)
    param_buf.append(0x02)

    # Wrap in MigrationPayload message:
    # field 1 (otp_parameters): tag = (1 << 3) | 2 = 10 (0x0A)
    msg_buf = bytearray()
    msg_buf.append(0x0A)
    msg_buf.append(len(param_buf))
    msg_buf.extend(param_buf)

    b64_payload = base64.b64encode(msg_buf).decode("ascii")
    migration_uri = f"otpauth-migration://offline?data={b64_payload}"

    candidates = QRParserAdapter.parse_provisioning_input(migration_uri)
    assert len(candidates) == 1
    c = candidates[0]
    assert c.issuer == "iCloudEMS"
    assert c.account_name == "student@univ.edu"
    assert c.secret_base32 == SYNTHETIC_BASE32
    assert c.algorithm == "SHA1"
    assert c.digits == 6
    assert c.source_type == "GOOGLE_MIGRATION"


def test_reject_hotp_scheme():
    """Verify rejection of counter-based HOTP."""
    uri = f"otpauth://hotp/test?secret={SYNTHETIC_BASE32}&counter=1"
    with pytest.raises(TotpEnrollmentError, match="Counter-based HOTP is not supported"):
        QRParserAdapter.parse_provisioning_input(uri)


def test_decode_offline_qr_image():
    """Verify offline QR code image decoding with OpenCV using a synthetic QR image."""
    import cv2
    enc = cv2.QRCodeEncoder_create()
    test_uri = f"otpauth://totp/University:student_test?secret={SYNTHETIC_BASE32}&issuer=University"
    raw_qr = enc.encode(test_uri)
    scaled_qr = cv2.resize(raw_qr, (330, 330), interpolation=cv2.INTER_NEAREST)
    bordered_qr = cv2.copyMakeBorder(scaled_qr, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    _, png_bytes = cv2.imencode(".png", bordered_qr)

    decoded = QRParserAdapter.decode_qr_image(png_bytes.tobytes())
    assert decoded == test_uri
    candidates = QRParserAdapter.parse_provisioning_input(decoded)
    assert len(candidates) == 1
    assert candidates[0].secret_base32 == SYNTHETIC_BASE32
    assert candidates[0].issuer == "University"


def test_parse_multi_account_google_migration_payload():
    """Verify parsing multiple accounts from a single Google Authenticator migration payload."""
    def make_param(secret_b32: str, name: str, issuer: str) -> bytes:
        raw_sec = base64.b32decode(secret_b32)
        buf = bytearray()
        # field 1: secret
        buf.append(0x0A)
        buf.append(len(raw_sec))
        buf.extend(raw_sec)
        # field 2: name
        n_bytes = name.encode("utf-8")
        buf.append(0x12)
        buf.append(len(n_bytes))
        buf.extend(n_bytes)
        # field 3: issuer
        i_bytes = issuer.encode("utf-8")
        buf.append(0x1A)
        buf.append(len(i_bytes))
        buf.extend(i_bytes)
        # field 4: algo = 1 (SHA1)
        buf.append(0x20)
        buf.append(0x01)
        # field 5: digits = 1 (6 digits)
        buf.append(0x28)
        buf.append(0x01)
        # field 6: type = 2 (TOTP)
        buf.append(0x30)
        buf.append(0x02)
        return bytes(buf)

    p1 = make_param(SYNTHETIC_BASE32, "student_primary@univ.edu", "iCloudEMS")
    p2 = make_param("NBSWY3DPEHPK3PXP", "student_secondary@personal.com", "Google")

    msg = bytearray()
    msg.append(0x0A)
    msg.append(len(p1))
    msg.extend(p1)
    msg.append(0x0A)
    msg.append(len(p2))
    msg.extend(p2)

    b64_payload = base64.b64encode(msg).decode("ascii")
    migration_uri = f"otpauth-migration://offline?data={b64_payload}"

    candidates = QRParserAdapter.parse_provisioning_input(migration_uri)
    assert len(candidates) == 2
    assert candidates[0].account_name == "student_primary@univ.edu"
    assert candidates[0].issuer == "iCloudEMS"
    assert candidates[0].masked_account == "st***du"
    assert candidates[1].account_name == "student_secondary@personal.com"
    assert candidates[1].issuer == "Google"
    assert candidates[1].masked_account == "st***om"


def test_reject_malformed_migration_payload():
    """Verify safe rejection of malformed or corrupted migration URIs."""
    # Empty data
    with pytest.raises(TotpEnrollmentError, match="contains no data payload"):
        QRParserAdapter.parse_provisioning_input("otpauth-migration://offline?data=")

    # Corrupt base64 / invalid protobuf
    with pytest.raises(TotpEnrollmentError):
        QRParserAdapter.parse_provisioning_input("otpauth-migration://offline?data=INVALID_NON_BASE64_BYTES!@#")

    # Protobuf message with version only, no accounts
    no_accounts_b64 = base64.b64encode(b"\x10\x01").decode("ascii")
    with pytest.raises(TotpEnrollmentError, match="No valid TOTP accounts found"):
        QRParserAdapter.parse_provisioning_input(f"otpauth-migration://offline?data={no_accounts_b64}")
