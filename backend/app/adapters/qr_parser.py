"""QR Image Decoder and Authenticator Provisioning Parser.

Supports:
1. Standard RFC 6238 otpauth://totp/ provisioning URIs.
2. Direct Base32 manual secrets.
3. Offline QR images (PNG, JPEG, WebP) using OpenCV QRCodeDetector.
4. Google Authenticator Migration (otpauth-migration://) payloads parsed locally in-memory.
"""

from __future__ import annotations

import base64
import logging
import re
import urllib.parse

import cv2
import numpy as np

from app.domain.totp_models import (
    TotpAccountCandidate,
    TotpEnrollmentError,
    TotpInvalidSecretError,
)

logger = logging.getLogger(__name__)

# Maximum allowed QR image upload size: 5 MB to prevent memory exhaustion
MAX_QR_IMAGE_BYTES = 5 * 1024 * 1024


def clean_base32_secret(raw: str) -> str:
    """Normalize Base32 secret string (remove whitespace/dashes, uppercase, pad if needed)."""
    cleaned = re.sub(r"[\s\-_]", "", raw).upper()
    if not cleaned:
        raise TotpInvalidSecretError("TOTP secret cannot be empty.")

    # Validate Base32 character set (A-Z, 2-7)
    if not re.match(r"^[A-Z2-7]+=*$", cleaned):
        raise TotpInvalidSecretError(
            "Secret contains invalid characters. Base32 secrets must only contain characters A-Z and digits 2-7."
        )

    # Strip existing padding so we can compute exact required RFC 4648 padding
    unpadded = cleaned.rstrip("=")
    missing_padding = (8 - (len(unpadded) % 8)) % 8
    padded = unpadded + ("=" * missing_padding)

    try:
        base64.b32decode(padded, casefold=True)
    except Exception as e:
        raise TotpInvalidSecretError(f"Invalid Base32 secret encoding: {e}") from e

    return unpadded



def decode_varint(data: bytes, offset: int) -> tuple[int, int]:
    """Decode standard Protobuf varint."""
    val = 0
    shift = 0
    while offset < len(data):
        b = data[offset]
        offset += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, offset
        shift += 7
    raise ValueError("Truncated protobuf varint")


def parse_protobuf_otp_parameters(data: bytes) -> TotpAccountCandidate:
    """Parse embedded OtpParameters message inside a Google Authenticator migration payload."""
    offset = 0
    secret_bytes = b""
    name = ""
    issuer = ""
    algo_val = 1
    digits_val = 1

    while offset < len(data):
        tag, offset = decode_varint(data, offset)
        field_num = tag >> 3
        wire_type = tag & 0x07

        if wire_type == 0:  # Varint
            val, offset = decode_varint(data, offset)
            if field_num == 4:
                algo_val = val
            elif field_num == 5:
                digits_val = val
        elif wire_type == 2:  # Length-delimited

            length, offset = decode_varint(data, offset)
            field_data = data[offset : offset + length]
            offset += length
            if field_num == 1:
                secret_bytes = field_data
            elif field_num == 2:
                name = field_data.decode("utf-8", errors="replace")
            elif field_num == 3:
                issuer = field_data.decode("utf-8", errors="replace")
        elif wire_type == 5:  # 32-bit fixed
            offset += 4
        elif wire_type == 1:  # 64-bit fixed
            offset += 8
        else:
            raise ValueError(f"Unsupported protobuf wire type: {wire_type}")

    if not secret_bytes:
        raise TotpInvalidSecretError("No secret bytes found in migration parameter block.")

    secret_b32 = base64.b32encode(secret_bytes).decode("ascii").replace("=", "")
    algo = "SHA256" if algo_val == 2 else ("SHA512" if algo_val == 3 else "SHA1")
    digits = 8 if digits_val == 2 else 6

    return TotpAccountCandidate(
        issuer=issuer or "iCloudEMS",
        account_name=name or "student",
        secret_base32=clean_base32_secret(secret_b32),
        algorithm=algo,
        digits=digits,
        period=30,
        source_type="GOOGLE_MIGRATION",
    )


class QRParserAdapter:
    """Offline decoder and extractor for authenticator QR images and URI payloads."""

    @staticmethod
    def decode_qr_image(image_bytes: bytes) -> str:
        """Decode a QR image buffer offline using OpenCV QRCodeDetector."""
        if len(image_bytes) > MAX_QR_IMAGE_BYTES:
            raise TotpEnrollmentError(f"QR image exceeds maximum allowed size of {MAX_QR_IMAGE_BYTES // (1024*1024)} MB.")

        if not image_bytes:
            raise TotpEnrollmentError("Empty image file provided.")

        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise TotpEnrollmentError("Failed to decode image file. Please provide a valid PNG, JPEG, or WebP image.")

        detector = cv2.QRCodeDetector()
        decoded_text, _, _ = detector.detectAndDecode(img)
        if not decoded_text or not decoded_text.strip():
            # Try with grayscale enhancement
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            decoded_text, _, _ = detector.detectAndDecode(gray)

        if not decoded_text or not decoded_text.strip():
            raise TotpEnrollmentError("Could not locate or decode a valid QR code in the provided image.")

        return decoded_text.strip()

    @classmethod
    def parse_provisioning_input(cls, raw_input: str) -> list[TotpAccountCandidate]:
        """Parse raw user input or decoded QR text into candidate accounts.

        Returns a list of candidate accounts (typically 1 for standard QR, or multiple for migration QR).
        """
        trimmed = raw_input.strip()
        if not trimmed:
            raise TotpEnrollmentError("Provisioning input cannot be empty.")

        # 1. Google Authenticator Migration URI: otpauth-migration://offline?data=...
        if trimmed.startswith("otpauth-migration://"):
            return cls._parse_google_migration_uri(trimmed)

        # 2. Standard RFC 6238 Provisioning URI: otpauth://totp/...
        if trimmed.startswith("otpauth://"):
            return [cls._parse_standard_otpauth_uri(trimmed)]

        # 3. Plain Base32 Secret Key
        cleaned_secret = clean_base32_secret(trimmed)
        return [
            TotpAccountCandidate(
                issuer="iCloudEMS / Keycloak",
                account_name="student_account",
                secret_base32=cleaned_secret,
                algorithm="SHA1",
                digits=6,
                period=30,
                source_type="MANUAL_BASE32",
            )
        ]

    @classmethod
    def _parse_standard_otpauth_uri(cls, uri_str: str) -> TotpAccountCandidate:
        """Parse standard otpauth://totp/Label?secret=... URI."""
        parsed = urllib.parse.urlparse(uri_str)
        if parsed.scheme != "otpauth" or parsed.netloc.lower() not in ["totp", "hotp"]:
            raise TotpEnrollmentError("Unsupported authenticator URI scheme. Only otpauth://totp/ is supported.")

        if parsed.netloc.lower() == "hotp":
            raise TotpEnrollmentError("Counter-based HOTP is not supported for university Keycloak authentication. Time-based TOTP is required.")

        label = urllib.parse.unquote(parsed.path.lstrip("/"))
        issuer_from_label = None
        account_name = label
        if ":" in label:
            parts = label.split(":", 1)
            issuer_from_label = parts[0].strip()
            account_name = parts[1].strip()

        qs = urllib.parse.parse_qs(parsed.query)
        secret_list = qs.get("secret")
        if not secret_list or not secret_list[0]:
            raise TotpInvalidSecretError("Authenticator URI does not contain a 'secret' parameter.")

        raw_secret = secret_list[0]
        cleaned_secret = clean_base32_secret(raw_secret)

        issuer = qs.get("issuer", [issuer_from_label or "iCloudEMS"])[0]
        digits = int(qs.get("digits", ["6"])[0])
        period = int(qs.get("period", ["30"])[0])
        algorithm = qs.get("algorithm", ["SHA1"])[0].upper()

        if digits not in [6, 8]:
            raise TotpEnrollmentError(f"Unsupported TOTP digits: {digits}. Only 6 or 8 digits are supported.")

        if period not in [30, 60]:
            raise TotpEnrollmentError(f"Unsupported TOTP period: {period}s. Only 30s or 60s periods are supported.")

        if algorithm not in ["SHA1", "SHA256", "SHA512"]:
            raise TotpEnrollmentError(f"Unsupported TOTP algorithm: {algorithm}. Supported: SHA1, SHA256, SHA512.")

        return TotpAccountCandidate(
            issuer=issuer,
            account_name=account_name or "student_account",
            secret_base32=cleaned_secret,
            algorithm=algorithm,
            digits=digits,
            period=period,
            source_type="STANDARD_TOTP",
        )

    @classmethod
    def _parse_google_migration_uri(cls, uri_str: str) -> list[TotpAccountCandidate]:
        """Decode Google Authenticator export migration URI."""
        parsed = urllib.parse.urlparse(uri_str)
        if parsed.scheme != "otpauth-migration":
            raise TotpEnrollmentError("Not a valid otpauth-migration URI.")

        qs = urllib.parse.parse_qs(parsed.query)
        data_b64 = qs.get("data", [""])[0]
        if not data_b64:
            raise TotpEnrollmentError("Migration URI contains no data payload.")

        # Ensure valid Base64 padding
        missing_padding = len(data_b64) % 4
        if missing_padding:
            data_b64 += "=" * (4 - missing_padding)

        try:
            raw_proto = base64.b64decode(data_b64)
        except Exception as e:
            raise TotpEnrollmentError(f"Failed to decode migration Base64 payload: {e}") from e

        offset = 0
        accounts: list[TotpAccountCandidate] = []

        while offset < len(raw_proto):
            tag, offset = decode_varint(raw_proto, offset)
            field_num = tag >> 3
            wire_type = tag & 0x07

            if wire_type == 2:  # Length-delimited embedded OtpParameters
                length, offset = decode_varint(raw_proto, offset)
                item_bytes = raw_proto[offset : offset + length]
                offset += length
                if field_num == 1:
                    try:
                        cand = parse_protobuf_otp_parameters(item_bytes)
                        accounts.append(cand)
                    except Exception as err:
                        logger.warning("Skipping unparseable migration parameter entry: %s", err)
            elif wire_type == 0:
                _, offset = decode_varint(raw_proto, offset)
            elif wire_type == 5:
                offset += 4
            elif wire_type == 1:
                offset += 8
            else:
                break

        if not accounts:
            raise TotpEnrollmentError("No valid TOTP accounts found in Google Authenticator migration payload.")

        return accounts
