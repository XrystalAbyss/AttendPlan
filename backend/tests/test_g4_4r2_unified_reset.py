"""Tests for AttendPlan Phase G.4.4R2: Unified Safe Reset Engine and Fail-Closed Guarantees."""

import sqlite3
from pathlib import Path
from unittest.mock import patch

from launcher import (
    RESET_EXIT_CODES,
    ResetStatus,
    is_app_or_db_active,
    is_reparse_point_or_symlink,
    perform_safe_app_data_reset,
    perform_safe_backup,
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


class TestHardenedBackupTransactions:
    def test_backup_rejects_overwrite_of_existing_file(self, tmp_path: Path, monkeypatch):
        src_db = tmp_path / "appdata" / "attendplan.sqlite3"
        create_synthetic_test_db(src_db)
        backup_dest = tmp_path / "backups" / "existing_backup.sqlite3"
        backup_dest.parent.mkdir(parents=True, exist_ok=True)
        backup_dest.write_text("already exists", encoding="utf-8")

        monkeypatch.setenv("ATTENDPLAN_ALLOW_CUSTOM_ROOT", "1")
        monkeypatch.setenv("ATTENDPLAN_DB_PATH", str(src_db))

        res = perform_safe_backup(str(backup_dest))
        assert res != 0
        assert res == 1
        # Existing file was not modified
        assert backup_dest.read_text(encoding="utf-8") == "already exists"

    def test_backup_to_directory_creates_timestamped_file(self, tmp_path: Path, monkeypatch):
        src_db = tmp_path / "appdata" / "attendplan.sqlite3"
        create_synthetic_test_db(src_db)
        backup_dir = tmp_path / "backups_dir"
        backup_dir.mkdir(parents=True, exist_ok=True)

        monkeypatch.setenv("ATTENDPLAN_ALLOW_CUSTOM_ROOT", "1")
        monkeypatch.setenv("ATTENDPLAN_DB_PATH", str(src_db))

        res = perform_safe_backup(str(backup_dir))
        assert res == 0
        assert res.path is not None
        assert res.path.exists()
        assert res.path.name.startswith("AttendPlan_Backup_")
        assert res.path.name.endswith(".sqlite3")
        assert res.sha256 is not None
        assert len(res.sha256) == 64

    def test_backup_detects_table_count_mismatch(self, tmp_path: Path, monkeypatch):
        src_db = tmp_path / "appdata" / "attendplan.sqlite3"
        create_synthetic_test_db(src_db)
        backup_dest = tmp_path / "backups" / "target.sqlite3"

        monkeypatch.setenv("ATTENDPLAN_ALLOW_CUSTOM_ROOT", "1")
        monkeypatch.setenv("ATTENDPLAN_DB_PATH", str(src_db))

        # Mock sqlite3.connect to corrupt backup after copying
        orig_connect = sqlite3.connect

        def poisoned_connect(db_str, *args, **kwargs):
            conn = orig_connect(db_str, *args, **kwargs)
            # If opening destination for verification, delete rows
            if str(db_str) == str(backup_dest.resolve()):
                try:
                    conn.execute("DELETE FROM courses")
                    conn.commit()
                except Exception:
                    pass
            return conn

        with patch("sqlite3.connect", side_effect=poisoned_connect):
            res = perform_safe_backup(str(backup_dest))
            assert res != 0


class TestProcessAndLockSafety:
    def test_is_app_or_db_active_when_database_locked(self, tmp_path: Path):
        db_path = tmp_path / "locked.sqlite3"
        create_synthetic_test_db(db_path)

        # Hold exclusive lock on database
        conn = sqlite3.connect(str(db_path))
        conn.execute("BEGIN EXCLUSIVE")

        try:
            active, reason = is_app_or_db_active(db_path)
            assert active is True
            assert "locked" in reason.lower()
        finally:
            conn.rollback()
            conn.close()

    def test_is_app_or_db_active_when_idle(self, tmp_path: Path):
        db_path = tmp_path / "idle.sqlite3"
        create_synthetic_test_db(db_path)

        with patch("launcher.is_server_healthy", return_value=False), patch(
            "launcher.acquire_app_mutex", return_value=(True, False)
        ):
            active, reason = is_app_or_db_active(db_path)
            assert active is False
            assert reason == ""


class TestReparsePointAndSymlinkDetection:
    def test_detects_symlink(self, tmp_path: Path):
        real_file = tmp_path / "real.txt"
        real_file.write_text("hello", encoding="utf-8")
        symlink_file = tmp_path / "link.txt"
        try:
            symlink_file.symlink_to(real_file)
            assert is_reparse_point_or_symlink(symlink_file) is True
        except OSError:
            # On Windows without SeCreateSymbolicLinkPrivilege, skip symlink creation
            pass

        assert is_reparse_point_or_symlink(real_file) is False


class TestUnifiedResetFailClosed:
    def test_reset_rejects_noncanonical_override_in_production(self, tmp_path: Path, monkeypatch):
        # Do NOT set ATTENDPLAN_ALLOW_CUSTOM_ROOT
        monkeypatch.delenv("ATTENDPLAN_ALLOW_CUSTOM_ROOT", raising=False)
        # Set unexpected override outside AppData
        unexpected_db = tmp_path / "external" / "hacked.sqlite3"
        monkeypatch.setenv("ATTENDPLAN_DB_PATH", str(unexpected_db))

        res = perform_safe_app_data_reset("C:/dest/backup.sqlite3", confirm="DELETE")
        assert res == RESET_EXIT_CODES[ResetStatus.INVALID_PATH]

    def test_reset_aborts_when_app_or_db_is_active(self, tmp_path: Path, monkeypatch):
        app_dir = tmp_path / "appdata"
        src_db = app_dir / "attendplan.sqlite3"
        create_synthetic_test_db(src_db)
        backup_dest = tmp_path / "backups" / "pre_reset.sqlite3"

        monkeypatch.setenv("ATTENDPLAN_ALLOW_CUSTOM_ROOT", "1")
        monkeypatch.setenv("ATTENDPLAN_DB_PATH", str(src_db))

        with patch("launcher.is_app_or_db_active", return_value=(True, "Server active on port 8000")):
            res = perform_safe_app_data_reset(str(backup_dest), confirm="DELETE")
            assert res == RESET_EXIT_CODES[ResetStatus.APP_RUNNING]
            # Database must NOT be touched
            assert src_db.exists()

    def test_reset_aborts_before_deletion_if_vault_revocation_fails(
        self, tmp_path: Path, monkeypatch
    ):
        app_dir = tmp_path / "appdata"
        src_db = app_dir / "attendplan.sqlite3"
        create_synthetic_test_db(src_db)
        backup_dest = tmp_path / "backups" / "pre_reset.sqlite3"

        monkeypatch.setenv("ATTENDPLAN_ALLOW_CUSTOM_ROOT", "1")
        monkeypatch.setenv("ATTENDPLAN_DB_PATH", str(src_db))

        with patch("launcher.purge_vault_only", return_value=1):
            res = perform_safe_app_data_reset(str(backup_dest), confirm="DELETE")
            assert res == RESET_EXIT_CODES[ResetStatus.VAULT_FAILED]
            # Database and local data must NOT be touched
            assert src_db.exists()

    def test_reset_reports_deletion_partial_on_locked_or_unremovable_file(
        self, tmp_path: Path, monkeypatch
    ):
        app_dir = tmp_path / "appdata"
        app_dir.mkdir(parents=True, exist_ok=True)
        src_db = app_dir / "attendplan.sqlite3"
        create_synthetic_test_db(src_db)
        backup_dest = tmp_path / "backups" / "pre_reset.sqlite3"

        # Create settings file that cannot be deleted
        locked_settings = app_dir / "settings.json"
        locked_settings.write_text("locked", encoding="utf-8")

        monkeypatch.setenv("ATTENDPLAN_ALLOW_CUSTOM_ROOT", "1")
        monkeypatch.setenv("ATTENDPLAN_DB_PATH", str(src_db))

        # Mock unlink to fail on settings.json
        orig_unlink = Path.unlink

        def mock_unlink(self_path, *args, **kwargs):
            if self_path.name == "settings.json":
                raise PermissionError("Access is denied")
            return orig_unlink(self_path, *args, **kwargs)

        with patch("launcher.purge_vault_only", return_value=0), patch.object(
            Path, "unlink", side_effect=mock_unlink, autospec=True
        ):
            res = perform_safe_app_data_reset(str(backup_dest), confirm="DELETE")
            assert res == RESET_EXIT_CODES[ResetStatus.DELETION_PARTIAL]
            # Verify partial failure is reported, not SUCCESS
            assert locked_settings.exists()
            # Verified backup is still preserved
            assert backup_dest.exists()
