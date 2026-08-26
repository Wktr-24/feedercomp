"""Tests for the operational hardening added before v0.4.0: DB backup
rotation, strict date validation, and version consistency."""
import sqlite3

import app
from app.main import _BACKUPS_TO_KEEP, _backup_database
from app.utils import parse_strict_iso_date


def _make_db(path):
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE t (x)")
    conn.execute("INSERT INTO t VALUES (42)")
    conn.commit()
    conn.close()


class TestBackupDatabase:
    def test_creates_backup(self, tmp_path):
        db = tmp_path / "data.db"
        _make_db(db)

        _backup_database(db)

        backups = list((tmp_path / "backups").glob("data-*.db"))
        assert len(backups) == 1
        # The backup is a valid database with the same content.
        conn = sqlite3.connect(str(backups[0]))
        assert conn.execute("SELECT x FROM t").fetchone()[0] == 42
        conn.close()

    def test_missing_db_is_noop(self, tmp_path):
        _backup_database(tmp_path / "data.db")
        assert not (tmp_path / "backups").exists()

    def test_rotation_keeps_newest(self, tmp_path):
        db = tmp_path / "data.db"
        _make_db(db)
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        # Fabricate more stamped backups than the retention limit; all with
        # stamps older than anything datetime.now() will produce.
        for i in range(_BACKUPS_TO_KEEP + 5):
            (backup_dir / f"data-20200101-{i:06d}.db").write_bytes(b"old")

        _backup_database(db)

        stamped = sorted(backup_dir.glob("data-????????-??????.db"))
        assert len(stamped) == _BACKUPS_TO_KEEP
        # The newest (just-created, real) backup survived the rotation.
        assert stamped[-1].stat().st_size > len(b"old")
        # The oldest fabricated ones were pruned.
        assert not (backup_dir / "data-20200101-000000.db").exists()

    def test_hand_made_copy_not_rotated(self, tmp_path):
        db = tmp_path / "data.db"
        _make_db(db)
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        keeper = backup_dir / "data-przed-finalem.db"
        keeper.write_bytes(b"precious")
        for i in range(_BACKUPS_TO_KEEP + 5):
            (backup_dir / f"data-20200101-{i:06d}.db").write_bytes(b"old")

        _backup_database(db)

        # The manually named copy does not match the timestamp shape and
        # must never take part in the rotation.
        assert keeper.exists()
        assert keeper.read_bytes() == b"precious"


class TestParseStrictIsoDate:
    def test_canonical_form_accepted(self):
        parsed = parse_strict_iso_date("2026-09-05")
        assert parsed is not None
        assert parsed.isoformat() == "2026-09-05"

    def test_unpadded_rejected(self):
        assert parse_strict_iso_date("2026-9-5") is None

    def test_compact_form_rejected(self):
        # date.fromisoformat on 3.11+ would accept this — the round-trip must not.
        assert parse_strict_iso_date("20260905") is None

    def test_week_date_rejected(self):
        assert parse_strict_iso_date("2026-W36-1") is None

    def test_garbage_rejected(self):
        assert parse_strict_iso_date("wczoraj") is None
        assert parse_strict_iso_date("") is None


class TestVersionConsistency:
    def test_package_version_matches_pyproject(self):
        import tomllib
        from pathlib import Path
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        assert app.__version__ == data["project"]["version"]
