"""Deterministic canonical checksum calculation for AttendPlan.

Ensures row-order independent checksums to prevent duplicate ingestion
of identical snapshots or observation batches.
"""

from __future__ import annotations

import hashlib
import json
from typing import Sequence


def compute_snapshot_checksum(rows: Sequence[tuple[str, int, int]]) -> str:
    """Compute deterministic SHA256 checksum for subject-wise snapshot rows.

    Input rows: sequence of (course_code, attended_periods, delivered_periods).
    Sorted canonically so row reordering in HTML does not change checksum.
    """
    sorted_rows = sorted(rows, key=lambda r: r[0].strip().upper())
    canonical_repr = json.dumps(sorted_rows, separators=(",", ":"))
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()


def compute_observation_batch_checksum(
    observations: Sequence[tuple[str, str | None, str | None, str | None, str, int, int]],
) -> str:
    """Compute deterministic SHA256 checksum for observation batch.

    Input observations: sequence of:
    (date_iso, slot_start_time, period_identifier, course_label, status, delivered, attended).
    Sorted canonically so cell/row ordering does not change checksum.
    """
    sorted_obs = sorted(
        observations,
        key=lambda o: (
            o[0],  # date_iso
            o[1] or "",  # slot_start_time
            o[2] or "",  # period_identifier
            o[3] or "",  # course_label
        ),
    )
    canonical_repr = json.dumps(sorted_obs, separators=(",", ":"))
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()
