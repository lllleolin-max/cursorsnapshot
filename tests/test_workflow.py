from contextlib import closing
import base64
import hashlib
import hmac
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from cursorsnapshot import (Client, SnapshotError, collect, create_snapshot, export_records,
                            export_status, finish_export, initialize, make_server, page,
                            put_order, release, start_export, status, step_export)
from cursorsnapshot.model import canonical, decode_cursor, decode_json

KEY = b'public-cursorsnapshot-laboratory-key'


def record(number, tenant='shop'):
    return {'tenant': tenant, 'order_id': number, 'priority': [None, 2, 2, -1, 0, None][number % 6],
            'title': ['\u00e9', 'e\u0301', '\u4e2d', '', 'a', 'z'][number % 6],
            'total_cents': number * 100, 'category': 'open' if number % 2 else 'closed'}


class Workflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cursor-', dir=Path(__file__).parent)
        self.root = Path(self.temp.name); self.source = self.root/'source.sqlite'; self.store = self.root/'store.sqlite'
        initialize(self.source, 'source'); initialize(self.store, 'manager')
        for n in range(1, 13):
            put_order(self.source, record(n))
        put_order(self.source, record(100, 'other'))

    def tearDown(self):
        self.temp.cleanup()

    def truth(self, field='priority', direction='ASC', nulls='FIRST', category=None):
        with closing(sqlite3.connect(self.source)) as connection:
            connection.row_factory = sqlite3.Row
            return [dict(r) for r in connection.execute(f'SELECT * FROM orders WHERE tenant=?'+(' AND category=?' if category else '')+
                    f' ORDER BY {field} COLLATE BINARY {direction} NULLS {nulls}, order_id ASC', ['shop']+([category] if category else []))]

    def test_all_typed_orders_match_sqlite_oracle(self):
        for field in ('priority', 'title', 'total_cents', 'order_id'):
            for direction in ('ASC', 'DESC'):
                for nulls in ('FIRST', 'LAST'):
                    sort = {'field': field, 'direction': direction, 'nulls': nulls}
                    snapshot = create_snapshot(self.source, self.store, 'shop', KEY, sort=sort)
                    cursor = snapshot['cursor']; records = []
                    while cursor:
                        result = page(self.store, 'shop', cursor, KEY, sort=sort, size=3)
                        records.extend(result['records']); cursor = result['next']
                    self.assertEqual(records, self.truth(field, direction, nulls))
                    release(self.store, 'shop', snapshot['snapshot'])

    def test_frozen_filter_and_full_content(self):
        expected = self.truth(category='open')
        snapshot = create_snapshot(self.source, self.store, 'shop', KEY, query={'category': 'open'})
        changed = record(1); changed['title'] = 'changed'; put_order(self.source, changed)
        put_order(self.source, record(15))
        result = page(self.store, 'shop', snapshot['cursor'], KEY, query={'category': 'open'})
        self.assertEqual(result['records'], expected)

    def test_external_nocase_cannot_broaden_identity(self):
        external = self.root/'external.sqlite'
        with closing(sqlite3.connect(external)) as connection, connection:
            connection.executescript('CREATE TABLE orders(tenant TEXT COLLATE NOCASE NOT NULL,order_id INTEGER NOT NULL,priority INTEGER,title TEXT NOT NULL,total_cents INTEGER NOT NULL,category TEXT COLLATE NOCASE NOT NULL,PRIMARY KEY(tenant,order_id)) STRICT;')
            rows = [dict(record(1), tenant='SHOP', category='open'), dict(record(2), category='OPEN'), dict(record(3), category='open')]
            connection.executemany('INSERT INTO orders VALUES(?,?,?,?,?,?)', [list(row.values()) for row in rows])
        snapshot = create_snapshot(external, self.store, 'shop', KEY, query={'category': 'open'})
        self.assertEqual(snapshot['rows'], 1)
        result = page(self.store, 'shop', snapshot['cursor'], KEY, query={'category': 'open'})
        self.assertEqual(result['records'], [rows[2]])

    def test_hmac_oracle_and_binding(self):
        snapshot = create_snapshot(self.source, self.store, 'shop', KEY)
        body, signature = snapshot['cursor'].split('.')
        oracle = base64.urlsafe_b64encode(hmac.new(KEY, body.encode(), hashlib.sha256).digest()).rstrip(b'=').decode()
        self.assertEqual(signature, oracle)
        for change in ({'tenant': 'other'}, {'query': {'category': 'open'}}, {'sort': {'direction': 'DESC'}}):
            kwargs = {'tenant': 'shop', 'query': None, 'sort': None}; kwargs.update(change)
            with self.assertRaises(SnapshotError):
                page(self.store, kwargs.pop('tenant'), snapshot['cursor'], KEY, **kwargs)
        with self.assertRaises(SnapshotError):
            page(self.store, 'shop', snapshot['cursor'][:-1]+'!', KEY)

    def test_quotas_exact_and_rollback(self):
        logical = sum(len(canonical(r)) for r in self.truth())
        for kwargs in ({'max_rows': 11}, {'max_payload_bytes': logical-1}, {'max_total_payload_bytes': logical-1}):
            with self.assertRaises(SnapshotError):
                create_snapshot(self.source, self.store, 'shop', KEY, **kwargs)
            self.assertEqual(status(self.store, 'shop'), [])
        result = create_snapshot(self.source, self.store, 'shop', KEY, max_rows=12, max_payload_bytes=logical, max_active=1)
        self.assertEqual(result['payload_bytes'], logical)
        with self.assertRaises(SnapshotError):
            create_snapshot(self.source, self.store, 'shop', KEY, max_active=1)

    def test_expiry_lease_and_collection_boundaries(self):
        snapshot = create_snapshot(self.source, self.store, 'shop', KEY, now=100, ttl_seconds=5)
        def during(token):
            self.assertEqual(collect(self.store, now=105)['collected'], 0)
            with self.assertRaises(SnapshotError):
                release(self.store, 'shop', snapshot['snapshot'], now=105)
        self.assertEqual(len(page(self.store, 'shop', snapshot['cursor'], KEY, now=104, lease_seconds=3, after_lease=during)['records']), 12)
        with self.assertRaises(SnapshotError):
            page(self.store, 'shop', snapshot['cursor'], KEY, now=105)
        self.assertEqual(collect(self.store, now=105)['collected'], 1)
        other = create_snapshot(self.source, self.store, 'shop', KEY, now=200, ttl_seconds=1)
        with self.assertRaises(SnapshotError):
            page(self.store, 'shop', other['cursor'], KEY, now=200, lease_seconds=2,
                 after_lease=lambda _: collect(self.store, now=202))

    def test_materialization_callback_failure_rolls_back(self):
        def failure(count):
            if count == 2:
                raise RuntimeError('lab interruption')
        with self.assertRaises(RuntimeError):
            create_snapshot(self.source, self.store, 'shop', KEY, progress=failure)
        self.assertEqual(status(self.store, 'shop'), [])
        with closing(sqlite3.connect(self.store)) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM snapshot_rows').fetchone()[0], 0)

    def test_input_rejections_preserve_files(self):
        before = self.source.read_bytes()
        for bad in (dict(record(1), order_id=True), dict(record(1), title='\ud800'), dict(record(1), priority=1.5)):
            with self.assertRaises(SnapshotError):
                put_order(self.source, bad)
        with self.assertRaises(SnapshotError):
            initialize(self.source, 'manager')
        with self.assertRaises(SnapshotError):
            create_snapshot(self.source, self.source, 'shop', KEY)
        self.assertEqual(before, self.source.read_bytes())
        for raw in (b'{"a":1,"a":2}', b'[]', b'{"a":NaN}', b'\xff', b'{}'*9000):
            with self.assertRaises(SnapshotError):
                decode_json(raw)

    def test_missing_files_and_wrong_roles(self):
        with self.assertRaises(SnapshotError):
            collect(self.root/'missing.sqlite')
        self.assertFalse((self.root/'missing.sqlite').exists())
        with self.assertRaises(SnapshotError):
            collect(self.source)

    def test_recovery_role_guard_precedes_foreign_sqlite_open(self):
        from cursorsnapshot.storage import connect
        foreign = self.root/'foreign.sqlite'
        with closing(sqlite3.connect(foreign)) as connection, connection:
            connection.execute('CREATE TABLE unrelated(value TEXT)')
            connection.execute("INSERT INTO unrelated VALUES('PUBLIC LAB foreign content')")
        before = foreign.read_bytes()
        journal = Path(str(foreign)+'-journal'); journal.write_bytes(b'PUBLIC LAB unrelated sidecar')
        with self.assertRaises(SnapshotError):
            status(foreign, 'shop')
        self.assertEqual(before, foreign.read_bytes())
        self.assertEqual(journal.read_bytes(), b'PUBLIC LAB unrelated sidecar')
        with self.assertRaises(SnapshotError):
            with connect(self.store, 'manager', readonly=True) as connection:
                connection.execute('DELETE FROM snapshots')

    def test_roles_require_strings(self):
        for value in ([], {}, 1, None):
            target = self.root/('invalid-'+str(type(value).__name__)+'.sqlite')
            with self.assertRaises(SnapshotError):
                initialize(target, value)
            self.assertFalse(target.exists())

    def test_initialize_preserves_orphan_sidecar_namespace(self):
        for role in ('source', 'manager', 'export'):
            for suffix in ('-journal', '-wal', '-shm'):
                folder = self.root/(role+suffix); folder.mkdir()
                database = folder/'fresh.sqlite'; sidecar = Path(str(database)+suffix)
                sentinel = b'PUBLIC LAB unrelated file'
                sidecar.write_bytes(sentinel)
                with self.assertRaises(SnapshotError):
                    initialize(database, role)
                self.assertFalse(database.exists())
                self.assertEqual(sidecar.read_bytes(), sentinel)

    def test_actual_http_export_and_atomic_checkpoint(self):
        server = make_server(self.source, self.store, KEY)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            client = Client(f'http://127.0.0.1:{server.server_port}', 'shop')
            output = self.root/'export.sqlite'; start_export(client, output)
            expected = self.truth()
            with self.assertRaises(RuntimeError):
                step_export(output, size=4, before_commit=lambda: (_ for _ in ()).throw(RuntimeError('lab')))
            self.assertEqual(export_status(output)['records'], 0)
            step_export(output, size=4)
            changed = record(1); changed['title'] = 'late'; client.post('/orders', changed)
            while not export_status(output)['done']:
                step_export(output, size=4)
            self.assertEqual(list(export_records(output)), expected)
            self.assertTrue(finish_export(output)['released'])
        finally:
            server.shutdown(); server.server_close(); thread.join(3)

    def test_actionable_http_quota_reason(self):
        server = make_server(self.source, self.store, KEY, quotas={'max_rows': 0})
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with self.assertRaisesRegex(SnapshotError, '^remote_row_quota$'):
                Client(f'http://127.0.0.1:{server.server_port}', 'shop').post('/snapshots', {})
            self.assertEqual(status(self.store, 'shop'), [])
        finally:
            server.shutdown(); server.server_close(); thread.join(3)

    def test_unknown_remote_error_body_is_not_reflected(self):
        from http.server import BaseHTTPRequestHandler, HTTPServer
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                raw = canonical({'error': 'PUBLIC LAB private-value-must-not-be-reflected'})
                self.send_response(400); self.send_header('Content-Length', str(len(raw))); self.end_headers(); self.wfile.write(raw)
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with self.assertRaisesRegex(SnapshotError, '^remote_http_400$'):
                Client(f'http://127.0.0.1:{server.server_port}', 'shop').post('/snapshots', {})
        finally:
            server.shutdown(); server.server_close(); thread.join(3)


if __name__ == '__main__':
    unittest.main()
