"""Streaming frozen views, signed strict keyset pages and bounded lifecycle."""
import json
import secrets
from .model import (COLUMNS, SCHEMA, MAX_INT, SnapshotError, after_sql, canonical,
                    decode_cursor, encode_cursor, identity, integer, now_seconds,
                    order_record, order_sql, position, query_spec, sort_spec, validate_key)
from .storage import connect, safe_path, validate_source


def _collect(connection, now):
    connection.execute('DELETE FROM leases WHERE until <= ?', (now,))
    removed = connection.execute('DELETE FROM snapshots WHERE expires <= ? AND NOT EXISTS '
                                 '(SELECT 1 FROM leases WHERE leases.snapshot_id=snapshots.id AND until>?)', (now, now)).rowcount
    return removed


def collect(store, *, now=None):
    now = now_seconds(now)
    with connect(store, 'manager') as connection:
        connection.execute('BEGIN IMMEDIATE')
        removed = _collect(connection, now)
        connection.commit()
    return {'collected': removed}


def create_snapshot(source, store, tenant, key, *, query=None, sort=None, ttl_seconds=3600,
                    max_rows=10000, max_payload_bytes=8*1024*1024,
                    max_total_payload_bytes=64*1024*1024, max_active=16,
                    now=None, progress=None):
    identity(tenant); validate_key(key)
    query, sort = query_spec(query), sort_spec(sort)
    now = now_seconds(now); integer(ttl_seconds, 1, 86400)
    expires = integer(now + ttl_seconds)
    integer(max_rows, 0, 100000); integer(max_payload_bytes, 0, 64*1024*1024)
    integer(max_total_payload_bytes, 0, 256*1024*1024); integer(max_active, 1, 128)
    safe_path(store, (source,)); safe_path(source, (store,))
    snapshot_id = secrets.token_hex(16)
    count = payload_bytes = 0
    with connect(source, readonly=True) as origin, connect(store, 'manager') as destination:
        origin.execute('BEGIN')
        validate_source(origin)
        destination.execute('BEGIN IMMEDIATE')
        _collect(destination, now)
        active, retained = destination.execute("SELECT count(*),coalesce(sum(payload_bytes),0) FROM snapshots WHERE state='ready'").fetchone()
        if active >= max_active:
            raise SnapshotError('active_quota')
        destination.execute('INSERT INTO snapshots VALUES(?,?,?,?,?,?,?,?,?)',
                            (snapshot_id, tenant, canonical(query).decode(), canonical(sort).decode(), SCHEMA, expires, 0, 0, 'ready'))
        condition, values = 'tenant COLLATE BINARY=?', [tenant]
        if query['category'] is not None:
            condition += ' AND category COLLATE BINARY=?'; values.append(query['category'])
        # A finite VM budget is a scan budget, not a hard CPU or RSS promise.
        work = [0]
        def budget():
            work[0] += 1000
            return int(work[0] > 50000000)
        origin.set_progress_handler(budget, 1000)
        cursor = origin.execute(f"SELECT {','.join(COLUMNS)} FROM orders WHERE {condition} ORDER BY {order_sql(sort)} LIMIT ?", values + [max_rows+1])
        for row in cursor:
            record = order_record(dict(row))
            if record['tenant'] != tenant or (query['category'] is not None and record['category'] != query['category']):
                raise SnapshotError('source_identity')
            count += 1; payload_bytes += len(canonical(record))
            if count > max_rows:
                raise SnapshotError('row_quota')
            if payload_bytes > max_payload_bytes or retained + payload_bytes > max_total_payload_bytes:
                raise SnapshotError('payload_quota')
            destination.execute('INSERT INTO snapshot_rows VALUES(?,?,?,?,?,?,?)', [snapshot_id]+[record[name] for name in COLUMNS])
            if progress is not None:
                progress(count)
        origin.commit()
        destination.execute('UPDATE snapshots SET row_count=?,payload_bytes=? WHERE id=?', (count, payload_bytes, snapshot_id))
        destination.commit()
    payload = {'v': 1, 'tenant': tenant, 'snapshot': snapshot_id, 'query': query, 'sort': sort,
               'schema': SCHEMA, 'expires': expires, 'last': None}
    return {'snapshot': snapshot_id, 'cursor': encode_cursor(payload, key), 'expires': expires,
            'rows': count, 'payload_bytes': payload_bytes, 'schema': SCHEMA}


def page(store, tenant, cursor, key, *, query=None, sort=None, size=100,
         lease_seconds=30, now=None, after_lease=None):
    identity(tenant); integer(size, 1, 1000); integer(lease_seconds, 1, 60)
    query, sort = query_spec(query), sort_spec(sort)
    current = now_seconds(now); until = integer(current + lease_seconds)
    payload = decode_cursor(cursor, key)
    snapshot_id = identity(payload['snapshot'])
    if payload['tenant'] != tenant or payload['query'] != query or payload['sort'] != sort or payload['schema'] != SCHEMA:
        raise SnapshotError('cursor_binding')
    predicate, values = after_sql(sort, payload['last'])
    token = secrets.token_hex(16)
    with connect(store, 'manager') as connection:
        connection.execute('BEGIN IMMEDIATE')
        metadata = connection.execute('SELECT * FROM snapshots WHERE id=?', (snapshot_id,)).fetchone()
        if metadata is None or metadata['state'] != 'ready':
            raise SnapshotError('snapshot_gone')
        if metadata['expires'] <= current:
            raise SnapshotError('snapshot_expired')
        if metadata['tenant'] != tenant or json.loads(metadata['query']) != query or json.loads(metadata['sort']) != sort or metadata['expires'] != payload['expires'] or metadata['schema'] != payload['schema']:
            raise SnapshotError('cursor_binding')
        connection.execute('INSERT INTO leases VALUES(?,?,?)', (snapshot_id, token, until))
        connection.commit()
    try:
        if after_lease is not None:
            after_lease(token)
        with connect(store, 'manager', readonly=True) as connection:
            connection.execute('BEGIN')
            lease = connection.execute('SELECT until FROM leases WHERE token=? AND snapshot_id=?', (token, snapshot_id)).fetchone()
            if lease is None or lease['until'] <= now_seconds(now):
                raise SnapshotError('reader_lease_expired')
            rows = connection.execute(f"SELECT {','.join(COLUMNS)} FROM snapshot_rows WHERE snapshot_id=? AND {predicate} ORDER BY {order_sql(sort)} LIMIT ?",
                                      [snapshot_id]+values+[size+1]).fetchall()
            has_more = len(rows) > size
            records = [dict(row) for row in rows[:size]]
            next_cursor = None
            if has_more:
                payload['last'] = position(records[-1], sort)
                next_cursor = encode_cursor(payload, key)
            result = {'snapshot': snapshot_id, 'schema': SCHEMA, 'records': records, 'next': next_cursor}
            if until <= now_seconds(now):
                raise SnapshotError('reader_lease_expired')
            connection.commit()
        return result
    finally:
        with connect(store, 'manager') as connection:
            connection.execute('BEGIN IMMEDIATE')
            connection.execute('DELETE FROM leases WHERE token=?', (token,))
            connection.commit()


def release(store, tenant, snapshot_id, *, now=None):
    identity(tenant); identity(snapshot_id); current = now_seconds(now)
    with connect(store, 'manager') as connection:
        connection.execute('BEGIN IMMEDIATE')
        metadata = connection.execute('SELECT tenant,state FROM snapshots WHERE id=?', (snapshot_id,)).fetchone()
        if metadata is None:
            return {'state': 'gone'}
        if metadata['tenant'] != tenant:
            raise SnapshotError('snapshot_identity')
        if connection.execute('SELECT 1 FROM leases WHERE snapshot_id=? AND until>? LIMIT 1', (snapshot_id, current)).fetchone():
            raise SnapshotError('reader_busy')
        connection.execute('DELETE FROM snapshot_rows WHERE snapshot_id=?', (snapshot_id,))
        connection.execute("UPDATE snapshots SET state='released',payload_bytes=0 WHERE id=?", (snapshot_id,))
        connection.commit()
    return {'state': 'released'}


def status(store, tenant):
    identity(tenant)
    with connect(store, 'manager', readonly=True) as connection:
        return [dict(row) for row in connection.execute('SELECT id,expires,row_count,payload_bytes,state,schema FROM snapshots WHERE tenant=? ORDER BY id', (tenant,))]
