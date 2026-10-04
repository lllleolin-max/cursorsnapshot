"""Owned, create-only SQLite roles; no source-file copying or destructive overwrite."""
from contextlib import closing, contextmanager
import os
from pathlib import Path
import sqlite3
from .model import COLUMNS, SnapshotError, order_record

ROLES = {'source': 0x43535331, 'manager': 0x43534D31, 'export': 0x43534531}
SOURCE_SQL = '''CREATE TABLE orders(
 tenant TEXT NOT NULL, order_id INTEGER NOT NULL, priority INTEGER,
 title TEXT NOT NULL, total_cents INTEGER NOT NULL, category TEXT NOT NULL,
 PRIMARY KEY(tenant,order_id)) STRICT;'''
MANAGER_SQL = '''CREATE TABLE snapshots(
 id TEXT PRIMARY KEY, tenant TEXT NOT NULL, query TEXT NOT NULL, sort TEXT NOT NULL,
 schema TEXT NOT NULL, expires INTEGER NOT NULL, row_count INTEGER NOT NULL,
 payload_bytes INTEGER NOT NULL, state TEXT NOT NULL) STRICT;
 CREATE TABLE snapshot_rows(snapshot_id TEXT NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
 tenant TEXT NOT NULL, order_id INTEGER NOT NULL, priority INTEGER, title TEXT NOT NULL,
 total_cents INTEGER NOT NULL, category TEXT NOT NULL, PRIMARY KEY(snapshot_id,order_id)) STRICT;
 CREATE TABLE leases(snapshot_id TEXT NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
 token TEXT PRIMARY KEY, until INTEGER NOT NULL) STRICT;'''
EXPORT_SQL = '''CREATE TABLE progress(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
 endpoint TEXT NOT NULL, tenant TEXT NOT NULL, snapshot TEXT NOT NULL,
 query TEXT NOT NULL, sort TEXT NOT NULL, cursor TEXT, done INTEGER NOT NULL,
 released INTEGER NOT NULL, expected_rows INTEGER NOT NULL) STRICT;
 CREATE TABLE records(tenant TEXT NOT NULL, order_id INTEGER PRIMARY KEY, priority INTEGER,
 title TEXT NOT NULL, total_cents INTEGER NOT NULL, category TEXT NOT NULL) STRICT;'''


def safe_path(path, protected=()):
    path = Path(path).absolute()
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink():
            raise SnapshotError('path_alias')
    if path.exists() and (not path.is_file() or path.stat().st_nlink != 1):
        raise SnapshotError('path_alias')
    for suffix in ('-journal', '-wal', '-shm'):
        sidecar = Path(str(path) + suffix)
        if sidecar.is_symlink() or (sidecar.exists() and (not sidecar.is_file() or sidecar.stat().st_nlink != 1)):
            raise SnapshotError('path_alias')
    for other in protected:
        other = Path(other)
        if path.resolve() == other.resolve() or (path.exists() and other.exists() and os.path.samefile(path, other)):
            raise SnapshotError('path_alias')
    return path


def initialize(path, role):
    if role not in ROLES:
        raise SnapshotError('invalid_role')
    path = safe_path(path)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    except OSError as error:
        raise SnapshotError('create_only') from error
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.executescript({'source': SOURCE_SQL, 'manager': MANAGER_SQL, 'export': EXPORT_SQL}[role])
        connection.execute(f'PRAGMA application_id={ROLES[role]}')
        connection.execute('PRAGMA user_version=1')
    return str(path)


@contextmanager
def connect(path, role=None, readonly=False):
    path = safe_path(path)
    if not path.exists():
        raise SnapshotError('file_missing')
    connection = None
    try:
        connection = sqlite3.connect(path.as_uri() + ('?mode=ro' if readonly else '?mode=rw'), uri=True, timeout=2)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys=ON')
        if not readonly:
            connection.execute('PRAGMA synchronous=FULL')
        if role is not None and (connection.execute('PRAGMA application_id').fetchone()[0] != ROLES[role]
                                 or connection.execute('PRAGMA user_version').fetchone()[0] != 1):
            raise SnapshotError('database_role')
        yield connection
    except sqlite3.Error as error:
        raise SnapshotError('sqlite_failure') from error
    finally:
        if connection is not None:
            connection.close()


def validate_source(connection):
    row = connection.execute("SELECT type FROM sqlite_master WHERE name='orders'").fetchone()
    tables = connection.execute("PRAGMA table_list('orders')").fetchall()
    columns = connection.execute("PRAGMA table_xinfo('orders')").fetchall()
    expected = [('tenant', 'TEXT'), ('order_id', 'INTEGER'), ('priority', 'INTEGER'),
                ('title', 'TEXT'), ('total_cents', 'INTEGER'), ('category', 'TEXT')]
    if row is None or row[0] != 'table' or not any(t['schema'] == 'main' and t['type'] == 'table' for t in tables) or [(c['name'], c['type'].upper()) for c in columns] != expected or any(c['hidden'] for c in columns) or [c['pk'] for c in columns] != [1, 2, 0, 0, 0, 0]:
        raise SnapshotError('source_schema')


def put_order(path, record):
    record = order_record(record)
    with connect(path, 'source') as connection:
        connection.execute('BEGIN IMMEDIATE')
        connection.execute('INSERT INTO orders VALUES(?,?,?,?,?,?) ON CONFLICT(tenant,order_id) DO UPDATE SET '
                           'priority=excluded.priority,title=excluded.title,total_cents=excluded.total_cents,category=excluded.category',
                           [record[name] for name in COLUMNS])
        connection.commit()
