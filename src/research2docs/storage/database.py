"""Fixed database path, short-lived connections and non-destructive checked migrations."""

import hashlib
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from research2docs.core.errors import SchemaError, StorageError
from research2docs.core.models import utc_now
from research2docs.storage.migrations import (
    MIGRATION_1,
    MIGRATION_2,
    MIGRATION_3,
    MIGRATION_4,
    MIGRATION_5,
    SCHEMA_VERSION,
)


class Database:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.path = self.root / "research2docs.sqlite3"
        try:
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.initialize()
        except OSError:
            raise StorageError(
                "Unable to open local storage. Check the storage directory."
            ) from None

    @contextmanager
    def session(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        connection: sqlite3.Connection | None = None
        try:
            if self.path.is_symlink():
                raise StorageError("Storage database must not be a symbolic link.")
            connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
            self.path.chmod(0o600)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=5000")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
            connection.commit()
        except (sqlite3.Error, OSError):
            if connection is not None:
                connection.rollback()
            raise StorageError(
                "Unable to read or save local data. Retry or check local storage."
            ) from None
        except BaseException:
            if connection is not None:
                connection.rollback()
            raise
        finally:
            if connection is not None:
                connection.close()

    def initialize(self) -> None:
        migrations = {
            1: MIGRATION_1,
            2: MIGRATION_2,
            3: MIGRATION_3,
            4: MIGRATION_4,
            5: MIGRATION_5,
        }
        checksums = {
            number: hashlib.sha256("\n".join(sql).encode()).hexdigest()
            for number, sql in migrations.items()
        }
        with self.session(write=True) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            }
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION or version < 0:
                raise SchemaError(
                    "Storage uses an unsupported schema. Use a compatible application."
                )
            if not tables and version == 0:
                connection.execute(
                    "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, "
                    "checksum TEXT NOT NULL, applied_at TEXT NOT NULL)"
                )
            elif version < 1 or "schema_migrations" not in tables:
                raise SchemaError("Unrecognized storage schema. Existing data was not rebuilt.")
            else:
                rows = connection.execute(
                    "SELECT version, checksum FROM schema_migrations ORDER BY version"
                ).fetchall()
                if [(row[0], row[1]) for row in rows] != [
                    (number, checksums[number]) for number in range(1, version + 1)
                ]:
                    raise SchemaError("Storage migration history does not match this application.")
            for number in range(version + 1, SCHEMA_VERSION + 1):
                for statement in migrations[number]:
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations VALUES (?, ?, ?)",
                    (number, checksums[number], utc_now().isoformat()),
                )
                # Internal migration number, never document/user text.
                connection.execute(f"PRAGMA user_version={number}")
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise SchemaError("Storage has inconsistent relationships. Restore a valid backup.")
