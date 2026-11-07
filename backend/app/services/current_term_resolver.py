"""Dynamic current academic term resolver for AttendPlan.

Resolves the verified active enrollment from live portal selections or database state.
Strictly non-hardcoded: never assumes Semester 5 or 2026-2027.
Safely detects new semester rollover, disambiguates multiple classes,
and ensures offline provisional states cannot be misrepresented as live-verified.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlsplit

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.adapters.live_portal_extractor import SUBWISE_URL_PATH, LivePortalExtractor
from app.adapters.portal_safety import (
    PortalSafetyError,
    check_page,
    choose,
    options,
    selected,
)
from app.db.models import AcademicTerm

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedTerm:
    academic_year: str
    semester_number: int
    class_identifier: str
    class_display_label: str
    provenance: str  # "PORTAL_DEFAULT" | "DATABASE_FALLBACK_VERIFIED" | "DYNAMIC_HIGHEST" | "PORTAL_ROLLOVER_DETECTED" | "PROVISIONAL_OFFLINE"
    is_verified: bool = True
    is_provisional: bool = False


def resolve_provisional_term_from_db(db: Session) -> ResolvedTerm:
    """Resolve provisional current term from local database while offline.
    
    Marked as is_provisional=True, is_verified=False. Live operations must not write to it without verified source.
    """
    latest_db_term = db.scalars(
        select(AcademicTerm).order_by(desc(AcademicTerm.academic_year), desc(AcademicTerm.semester_number)).limit(1)
    ).first()
    if not latest_db_term:
        raise PortalSafetyError("NO_SAVED_ACADEMIC_TERMS")
    class_id = latest_db_term.class_identifier or ""
    return ResolvedTerm(
        academic_year=latest_db_term.academic_year,
        semester_number=latest_db_term.semester_number,
        class_identifier=class_id,
        class_display_label=class_id,
        provenance="PROVISIONAL_OFFLINE",
        is_verified=False,
        is_provisional=True,
    )


def resolve_active_term_from_portal(page: Any) -> Optional[ResolvedTerm]:
    """Inspect portal dropdowns for pre-selected active term.
    
    Verifies that the pre-selected term is not an outdated historical default
    when newer years or semesters are selectable in the portal.
    """
    check_page(page)
    try:
        year_val, year_lbl = selected(page, "year")
        sem_val, sem_lbl = selected(page, "semester")
        cls_val, cls_lbl = selected(page, "class")

        if year_val and sem_val and cls_val and sem_val.isdigit():
            # Check if portal options offer higher years or semesters (rollover check)
            try:
                avail_years = [o["value"] for o in options(page, "year") if o.get("value")]
                avail_sems = [int(o["value"]) for o in options(page, "semester") if str(o.get("value", "")).isdigit()]
                is_highest_year = not avail_years or year_val == sorted(avail_years, reverse=True)[0]
                is_highest_sem = not avail_sems or int(sem_val) >= max(avail_sems)

                if not (is_highest_year and is_highest_sem):
                    logger.info(
                        "Portal default %s Sem %s is older than available options; proceeding to full evaluation.",
                        year_val,
                        sem_val,
                    )
                    return None
            except Exception:
                pass

            return ResolvedTerm(
                academic_year=year_val,
                semester_number=int(sem_val),
                class_identifier=cls_val,
                class_display_label=cls_lbl or cls_val,
                provenance="PORTAL_DEFAULT",
                is_verified=True,
                is_provisional=False,
            )
    except PortalSafetyError:
        pass
    return None


def resolve_current_term(
    extractor: LivePortalExtractor,
    db: Session,
    page: Optional[Any] = None,
) -> ResolvedTerm:
    """Resolve the student's current active academic term safely.
    
    1. If portal already has active year/semester/class selected, verify and return.
    2. If portal selections are empty or outdated, evaluate available options in portal.
    3. Detect rollover: if portal options contain higher academic year or semester than local DB.
    4. Disambiguate classes when multiple classes are offered using student's enrollment history.
    5. If ambiguous or unavailable, raise PortalSafetyError.
    """
    def _resolve_with_page(portal_page: Any) -> ResolvedTerm:
        check_page(portal_page)
        if urlsplit(portal_page.url).path != SUBWISE_URL_PATH:
            extractor.navigate_to_view(portal_page, SUBWISE_URL_PATH, "select, #acadyear, #search")

        # 1. Check pre-selected options
        active = resolve_active_term_from_portal(portal_page)
        if active is not None:
            logger.info("Resolved active term from portal defaults: %s Sem %d (%s)",
                        active.academic_year, active.semester_number, active.class_display_label)
            return active

        # 2. Check local database for latest saved term
        latest_db_term = db.scalars(
            select(AcademicTerm).order_by(desc(AcademicTerm.academic_year), desc(AcademicTerm.semester_number)).limit(1)
        ).first()

        available_years = [o["value"] for o in options(portal_page, "year") if o["value"]]
        if not available_years:
            raise PortalSafetyError("CURRENT_TERM_UNVERIFIED")

        target_year: Optional[str] = None
        target_sem: Optional[int] = None
        rollover_detected: bool = False

        highest_portal_year = sorted(available_years, reverse=True)[0]

        if latest_db_term and latest_db_term.academic_year in available_years:
            # Check if a newer academic year has started
            if highest_portal_year > latest_db_term.academic_year:
                target_year = highest_portal_year
                rollover_detected = True
            else:
                target_year = latest_db_term.academic_year

            choose(portal_page, "year", target_year)
            available_sems = [int(o["value"]) for o in options(portal_page, "semester") if o["value"].isdigit()]

            if rollover_detected:
                target_sem = max(available_sems) if available_sems else None
            elif available_sems and max(available_sems) > latest_db_term.semester_number:
                # New semester started within same academic year
                target_sem = max(available_sems)
                rollover_detected = True
            elif latest_db_term.semester_number in available_sems:
                target_sem = latest_db_term.semester_number
            elif available_sems:
                target_sem = max(available_sems)
        else:
            # Pick highest academic year
            target_year = highest_portal_year
            choose(portal_page, "year", target_year)
            available_sems = [int(o["value"]) for o in options(portal_page, "semester") if o["value"].isdigit()]
            if available_sems:
                target_sem = max(available_sems)
            if latest_db_term and (target_year > latest_db_term.academic_year or (target_sem or 0) > latest_db_term.semester_number):
                rollover_detected = True

        if target_year is None or target_sem is None:
            raise PortalSafetyError("CURRENT_TERM_UNVERIFIED")

        choose(portal_page, "semester", str(target_sem))
        available_classes = options(portal_page, "class")
        valid_classes = [c for c in available_classes if c["value"]]
        if not valid_classes:
            raise PortalSafetyError("CURRENT_TERM_UNVERIFIED")

        chosen_class = None
        if len(valid_classes) == 1:
            chosen_class = valid_classes[0]
        else:
            # Multi-class disambiguation: inspect previous student enrollments in db
            previous_terms = db.scalars(
                select(AcademicTerm).order_by(desc(AcademicTerm.academic_year), desc(AcademicTerm.semester_number))
            ).all()

            COMMON_PREFIXES = {
                "b.tech", "btech", "m.tech", "mtech", "b.e", "be", "bca", "mca",
                "b.sc", "bsc", "sem", "semester", "sec", "section", "dept", "department"
            }
            scored_candidates: list[tuple[int, dict[str, str]]] = []
            for candidate in valid_classes:
                lbl = (candidate.get("label", "") or candidate.get("value", "")).lower()
                candidate_tokens = set(re.findall(r"[a-z0-9]+", lbl))
                score = 0
                for prev in previous_terms:
                    prev_label = (prev.class_identifier or "").lower()
                    prev_raw_tokens = [t for t in re.split(r"[\s\-_]+", prev_label) if len(t) >= 2 and not t.isdigit()]
                    meaningful_tokens = [t for t in prev_raw_tokens if t not in COMMON_PREFIXES]
                    for token in meaningful_tokens:
                        if token in lbl or token in candidate_tokens:
                            score += 1
                if score > 0:
                    scored_candidates.append((score, candidate))

            if not scored_candidates:
                raise PortalSafetyError("CURRENT_TERM_AMBIGUOUS_CLASS")

            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            if len(scored_candidates) > 1 and scored_candidates[0][0] == scored_candidates[1][0]:
                raise PortalSafetyError("CURRENT_TERM_AMBIGUOUS_CLASS")
            chosen_class = scored_candidates[0][1]

        choose(portal_page, "class", chosen_class["value"])

        provenance = (
            "PORTAL_ROLLOVER_DETECTED"
            if rollover_detected
            else ("DATABASE_FALLBACK_VERIFIED" if latest_db_term else "DYNAMIC_HIGHEST")
        )

        return ResolvedTerm(
            academic_year=target_year,
            semester_number=target_sem,
            class_identifier=chosen_class["value"],
            class_display_label=chosen_class["label"] or chosen_class["value"],
            provenance=provenance,
            is_verified=True,
            is_provisional=False,
        )

    if page is not None:
        return _resolve_with_page(page)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser, portal_page = extractor._get_portal_page(p)
        try:
            return _resolve_with_page(portal_page)
        finally:
            browser.close()
