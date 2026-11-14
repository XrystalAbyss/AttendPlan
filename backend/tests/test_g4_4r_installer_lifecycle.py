"""Tests for Phase G.4.4R Windows installer lifecycle, backup verification, and data safety."""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

from launcher import (
    acquire_app_mutex,
    inspect_database_file,
    perform_safe_app_data_reset,
    perform_safe_backup,
    purge_vault_only,
    release_app_mutex,
)


def create_synthetic_test_db(db_path: Path) -> None:
    """Create a minimal synthetic SQLite database matching AttendPlan schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE academic_terms (id TEXT PRIMARY KEY, term_name TEXT)"
        )
        cur.execute(
            "CREATE TABLE courses (id TEXT PRIMARY KEY, code TEXT, name TEXT)"
        )
        cur.execute(
            "CREATE TABLE attendance_period_observations (id TEXT PRIMARY KEY, status TEXT)"
        )
        cur.execute(
            "CREATE TABLE performance_snapshots (id TEXT PRIMARY KEY, gpa REAL)"
        )

        cur.execute("INSERT INTO academic_terms VALUES ('term1', 'Semester 1')")
        cur.execute("INSERT INTO courses VALUES ('c1', 'CS101', 'Intro to CS')")
        cur.execute("INSERT INTO courses VALUES ('c2', 'CS102', 'Data Structures')")
        cur.execute("INSERT INTO attendance_period_observations VALUES ('obs1', 'PRESENT')")
        cur.execute("INSERT INTO performance_snapshots VALUES ('snap1', 9.2)")
        conn.commit()
    finally:
        conn.close()


class TestInspectDatabaseFile:
    def test_inspect_valid_database(self, tmp_path: Path):
        db = tmp_path / "test.sqlite3"
        create_synthetic_test_db(db)
        res = inspect_database_file(db)
        assert res == 0

    def test_inspect_nonexistent_file(self, tmp_path: Path):
        nonexistent = tmp_path / "missing.sqlite3"
        res = inspect_database_file(nonexistent)
        assert res == 1

    def test_inspect_corrupt_database(self, tmp_path: Path):
        corrupt = tmp_path / "corrupt.sqlite3"
        corrupt.write_bytes(b"This is not a valid SQLite database header!!")
        res = inspect_database_file(corrupt)
        assert res == 1


class TestPerformSafeBackup:
    def test_safe_backup_success(self, tmp_path: Path, monkeypatch):
        src_db = tmp_path / "appdata" / "attendplan.sqlite3"
        create_synthetic_test_db(src_db)
        backup_dest = tmp_path / "backups" / "safe_backup.sqlite3"

        monkeypatch.setattr("app.db.session.get_default_db_path", lambda: src_db)

        res = perform_safe_backup(str(backup_dest))
        assert res == 0
        assert backup_dest.exists()
        assert backup_dest.stat().st_size > 0

        # Verify integrity and content
        conn = sqlite3.connect(str(backup_dest))
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check")
            assert cur.fetchall() == [("ok",)]
            assert cur.execute("SELECT count(*) FROM courses").fetchone()[0] == 2
            assert cur.execute("SELECT count(*) FROM academic_terms").fetchone()[0] == 1
        finally:
            conn.close()

    def test_safe_backup_missing_source(self, tmp_path: Path, monkeypatch):
        src_db = tmp_path / "appdata" / "missing.sqlite3"
        backup_dest = tmp_path / "backups" / "out.sqlite3"

        monkeypatch.setattr("app.db.session.get_default_db_path", lambda: src_db)
        res = perform_safe_backup(str(backup_dest))
        assert res == 1
        assert not backup_dest.exists()

    def test_safe_backup_path_collision(self, tmp_path: Path, monkeypatch):
        src_db = tmp_path / "appdata" / "attendplan.sqlite3"
        create_synthetic_test_db(src_db)

        monkeypatch.setattr("app.db.session.get_default_db_path", lambda: src_db)
        # Attempt to overwrite the source database
        res = perform_safe_backup(str(src_db))
        assert res == 1


class TestPerformSafeAppDataReset:
    def test_reset_aborts_without_confirm_delete(self, tmp_path: Path):
        res = perform_safe_app_data_reset("C:/dest/backup.sqlite3", confirm=None)
        assert res == 1

        res = perform_safe_app_data_reset("C:/dest/backup.sqlite3", confirm="yes")
        assert res == 1

    def test_reset_aborts_without_backup_dest(self, tmp_path: Path, monkeypatch):
        src_db = tmp_path / "appdata" / "attendplan.sqlite3"
        create_synthetic_test_db(src_db)
        monkeypatch.setattr("app.db.session.get_default_db_path", lambda: src_db)

        res = perform_safe_app_data_reset(None, confirm="DELETE")
        assert res == 1

    def test_reset_aborts_if_backup_dest_inside_deletion_scope(self, tmp_path: Path, monkeypatch):
        app_dir = tmp_path / "appdata"
        src_db = app_dir / "attendplan.sqlite3"
        create_synthetic_test_db(src_db)
        monkeypatch.setattr("app.db.session.get_default_db_path", lambda: src_db)

        # Inside app_dir
        dest_inside = app_dir / "unsafe_backup.sqlite3"
        res = perform_safe_app_data_reset(str(dest_inside), confirm="DELETE")
        assert res == 1

    def test_reset_allowlist_cleanup_and_protected_directory_preservation(
        self, tmp_path: Path, monkeypatch
    ):
        app_dir = tmp_path / "appdata"
        app_dir.mkdir(parents=True, exist_ok=True)
        src_db = app_dir / "attendplan.sqlite3"
        create_synthetic_test_db(src_db)
        monkeypatch.setattr("app.db.session.get_default_db_path", lambda: src_db)

        # Allowlisted files
        settings_file = app_dir / "settings.json"
        settings_file.write_text('{"saved_mobile_number": "123"}', encoding="utf-8")
        startup_file = app_dir / "startup.json"
        startup_file.write_text('{"token": "test"}', encoding="utf-8")

        # Allowlisted dirs
        logs_dir = app_dir / "logs"
        logs_dir.mkdir()
        (logs_dir / "app.log").write_text("log data", encoding="utf-8")

        chrome_dir = app_dir / "chrome-profile"
        chrome_dir.mkdir()
        (chrome_dir / "test.dat").write_text("profile data", encoding="utf-8")

        # Protected dirs
        backups_dir = app_dir / "backups"
        backups_dir.mkdir()
        historical_backup = backups_dir / "old_backup.sqlite3"
        historical_backup.write_text("old backup content", encoding="utf-8")

        evidence_dir = app_dir / "support_evidence"
        evidence_dir.mkdir()
        evidence_file = evidence_dir / "incident_report.txt"
        evidence_file.write_text("sensitive gh support evidence", encoding="utf-8")

        # External backup destination
        backup_dest = tmp_path / "external_backups" / "pre_reset.sqlite3"

        with patch("launcher.purge_vault_only") as mock_purge:
            mock_purge.return_value = 0
            res = perform_safe_app_data_reset(str(backup_dest), confirm="DELETE")
            assert res == 0
            mock_purge.assert_called_once()

        # Check backup was created and verified
        assert backup_dest.exists()
        assert backup_dest.stat().st_size > 0

        # Check allowlisted items were deleted
        assert not src_db.exists()
        assert not settings_file.exists()
        assert not startup_file.exists()
        assert not logs_dir.exists()
        assert not chrome_dir.exists()

        # Check protected directories and files were 100% PRESERVED
        assert backups_dir.exists()
        assert historical_backup.exists()
        assert historical_backup.read_text(encoding="utf-8") == "old backup content"

        assert evidence_dir.exists()
        assert evidence_file.exists()
        assert evidence_file.read_text(encoding="utf-8") == "sensitive gh support evidence"


class TestPurgeVaultOnly:
    def test_purge_vault_when_enrolled(self):
        with patch("app.services.totp_vault_service.TotpVaultService") as mock_cls:
            mock_vault = MagicMock()
            mock_vault.is_enrolled.return_value = True
            mock_cls.return_value = mock_vault

            res = purge_vault_only()
            assert res == 0
            mock_vault.remove_enrollment.assert_called_once()

    def test_purge_vault_when_not_enrolled(self):
        with patch("app.services.totp_vault_service.TotpVaultService") as mock_cls:
            mock_vault = MagicMock()
            mock_vault.is_enrolled.return_value = False
            mock_cls.return_value = mock_vault

            res = purge_vault_only()
            assert res == 0
            mock_vault.remove_enrollment.assert_not_called()


class TestWin32MutexSemantics:
    def test_acquire_and_release_app_mutex_mocked(self):
        with patch("sys.platform", "win32"), patch("ctypes.WinDLL") as mock_windll:
            mock_kernel32 = MagicMock()
            mock_windll.return_value = mock_kernel32

            # Simulate first process: handle returned, GetLastError() == 0
            mock_kernel32.CreateMutexW.return_value = 12345
            mock_kernel32.GetLastError.return_value = 0

            is_owner, already_exists = acquire_app_mutex()
            assert is_owner is True
            assert already_exists is False

            release_app_mutex()
            mock_kernel32.CloseHandle.assert_called_with(12345)

    def test_acquire_app_mutex_already_exists(self):
        with patch("sys.platform", "win32"), patch("ctypes.WinDLL") as mock_windll:
            mock_kernel32 = MagicMock()
            mock_windll.return_value = mock_kernel32

            # Simulate second process: handle returned, GetLastError() == ERROR_ALREADY_EXISTS (183)
            mock_kernel32.CreateMutexW.return_value = 67890
            mock_kernel32.GetLastError.return_value = 183

            is_owner, already_exists = acquire_app_mutex()
            assert is_owner is False
            assert already_exists is True
            # Duplicate handle should have been closed immediately
            mock_kernel32.CloseHandle.assert_called_with(67890)


def python_compare_semantic_versions(v1: str, v2: str) -> int:
    """Python reference implementation of Inno Setup's CompareSemanticVersions function."""
    def parse_semver(ver_str: str) -> tuple[int, int, int, int, str, int]:
        clean = ver_str.strip().lstrip("vV")
        if "-" in clean:
            main_part, pre_part = clean.split("-", 1)
        else:
            main_part, pre_part = clean, ""

        parts = main_part.split(".")
        maj = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
        min_ = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        pat = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0

        # In semver, a release without prerelease tag has higher precedence than prerelease
        if not pre_part:
            return (maj, min_, pat, 1, "", 0)  # 1 means GA (higher than prerelease 0)

        # Prerelease part
        if "." in pre_part:
            pre_tag, pre_num_str = pre_part.split(".", 1)
            pre_num = int(pre_num_str) if pre_num_str.isdigit() else 0
        else:
            pre_tag = pre_part
            pre_num = 0

        return (maj, min_, pat, 0, pre_tag.lower(), pre_num)

    p1 = parse_semver(v1)
    p2 = parse_semver(v2)

    # Compare Major.Minor.Patch
    if (p1[0], p1[1], p1[2]) != (p2[0], p2[1], p2[2]):
        diff = (p1[0], p1[1], p1[2]) > (p2[0], p2[1], p2[2])
        return 1 if diff else -1

    # Compare GA vs prerelease (GA > prerelease)
    if p1[3] != p2[3]:
        return 1 if p1[3] > p2[3] else -1

    # Both are prereleases: compare tag then number
    if p1[4] != p2[4]:
        return 1 if p1[4] > p2[4] else -1

    if p1[5] != p2[5]:
        return 1 if p1[5] > p2[5] else -1

    return 0


class TestSemanticVersionComparison:
    def test_semver_comparisons(self):
        # Equal versions
        assert python_compare_semantic_versions("0.1.0-beta.9", "0.1.0-beta.9") == 0
        assert python_compare_semantic_versions("0.1.0", "0.1.0") == 0

        # Beta progression: beta.8 < beta.9 < beta.10
        assert python_compare_semantic_versions("0.1.0-beta.8", "0.1.0-beta.9") < 0
        assert python_compare_semantic_versions("0.1.0-beta.9", "0.1.0-beta.8") > 0
        assert python_compare_semantic_versions("0.1.0-beta.9", "0.1.0-beta.10") < 0
        assert python_compare_semantic_versions("0.1.0-beta.10", "0.1.0-beta.9") > 0

        # Prerelease vs GA: 0.1.0-beta.9 < 0.1.0
        assert python_compare_semantic_versions("0.1.0-beta.9", "0.1.0") < 0
        assert python_compare_semantic_versions("0.1.0", "0.1.0-beta.9") > 0

        # Minor/Major version steps
        assert python_compare_semantic_versions("0.1.0", "0.2.0") < 0
        assert python_compare_semantic_versions("1.0.0", "0.9.9") > 0
