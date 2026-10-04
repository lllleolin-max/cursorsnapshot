"""Actual HTTP consumption and atomic page/checkpoint application to SQLite."""
import hashlib
import ipaddress
import json
from urllib import error, request
from urllib.parse import urlsplit
from .model import (COLUMNS, SCHEMA, SnapshotError, canonical, decode_json, identity,
                    integer, order_record, order_sql, query_spec, sort_spec)
from .storage import connect, initialize


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Client:
    def __init__(self, endpoint, tenant):
        identity(tenant)
        try:
            url = urlsplit(endpoint)
            port = url.port
            if url.scheme not in ('http', 'https') or not url.hostname or url.username is not None or url.password is not None or url.query or url.fragment or url.path not in ('', '/'):
                raise SnapshotError('invalid_endpoint')
            if url.scheme == 'http' and not ipaddress.ip_address(url.hostname).is_loopback:
                raise SnapshotError('https_required')
            if port is not None:
                integer(port, 1, 65535)
        except (ValueError, TypeError) as exception:
            raise SnapshotError('invalid_endpoint') from exception
        self.endpoint, self.tenant = endpoint.rstrip('/'), tenant
        self.opener = request.build_opener(request.ProxyHandler({}), NoRedirect())

    def post(self, route, body):
        if route not in ('/snapshots', '/pages', '/orders', '/release'):
            raise SnapshotError('invalid_route')
        raw = canonical(body)
        if len(raw) > 16384:
            raise SnapshotError('invalid_body_size')
        message = request.Request(self.endpoint+route, data=raw,
                                  headers={'X-Tenant': self.tenant, 'Content-Type': 'application/json'}, method='POST')
        try:
            with self.opener.open(message, timeout=5) as response:
                raw = response.read(4*1024*1024+1)
                return decode_json(raw, 4*1024*1024)
        except error.HTTPError as exception:
            # Raw remote body and URL are intentionally not included in local errors.
            raise SnapshotError('remote_http_'+str(exception.code)) from exception
        except (error.URLError, OSError, TimeoutError) as exception:
            raise SnapshotError('network_unknown') from exception


def start_export(client, output, *, query=None, sort=None, ttl_seconds=3600):
    query, sort = query_spec(query), sort_spec(sort)
    integer(ttl_seconds, 1, 86400)
    initialize(output, 'export')
    result = client.post('/snapshots', {'query': query, 'sort': sort, 'ttl_seconds': ttl_seconds})
    if result.get('schema') != SCHEMA or not isinstance(result.get('cursor'), str):
        raise SnapshotError('invalid_remote_snapshot')
    identity(result['snapshot']); integer(result['rows'], 0, 100000)
    with connect(output, 'export') as connection:
        connection.execute('BEGIN IMMEDIATE')
        connection.execute('INSERT INTO progress VALUES(1,?,?,?,?,?,?,0,0,?)',
                           (client.endpoint, client.tenant, result['snapshot'], canonical(query).decode(), canonical(sort).decode(), result['cursor'], result['rows']))
        connection.commit()
    return export_status(output)


def _progress(connection):
    result = connection.execute('SELECT * FROM progress WHERE singleton=1').fetchone()
    if result is None:
        raise SnapshotError('export_uninitialized')
    return dict(result)


def export_status(output):
    with connect(output, 'export', readonly=True) as connection:
        progress = _progress(connection)
        count = connection.execute('SELECT count(*) FROM records').fetchone()[0]
        return {'snapshot': progress['snapshot'], 'records': count, 'expected_rows': progress['expected_rows'],
                'done': bool(progress['done']), 'released': bool(progress['released'])}


def step_export(output, *, size=100, before_commit=None):
    integer(size, 1, 1000)
    with connect(output, 'export', readonly=True) as connection:
        saved = _progress(connection)
    if saved['done']:
        return export_status(output)
    client = Client(saved['endpoint'], saved['tenant'])
    result = client.post('/pages', {'cursor': saved['cursor'], 'query': json.loads(saved['query']),
                                   'sort': json.loads(saved['sort']), 'size': size})
    if result.get('snapshot') != saved['snapshot'] or result.get('schema') != SCHEMA or not isinstance(result.get('records'), list) or len(result['records']) > size:
        raise SnapshotError('invalid_remote_page')
    next_cursor = result.get('next')
    if next_cursor is not None and (not isinstance(next_cursor, str) or not next_cursor or len(next_cursor) > 4096):
        raise SnapshotError('invalid_remote_page')
    records = [order_record(record) for record in result['records']]
    if any(record['tenant'] != saved['tenant'] for record in records):
        raise SnapshotError('invalid_remote_page')
    with connect(output, 'export') as connection:
        connection.execute('BEGIN IMMEDIATE')
        current = _progress(connection)
        if current != saved:
            raise SnapshotError('checkpoint_changed')
        for record in records:
            connection.execute('INSERT INTO records VALUES(?,?,?,?,?,?)', [record[name] for name in COLUMNS])
        count = connection.execute('SELECT count(*) FROM records').fetchone()[0]
        if count > saved['expected_rows'] or (next_cursor is None and count != saved['expected_rows']):
            raise SnapshotError('incomplete_snapshot')
        connection.execute('UPDATE progress SET cursor=?,done=? WHERE singleton=1', (next_cursor, int(next_cursor is None)))
        if before_commit is not None:
            before_commit()
        connection.commit()
    return export_status(output)


def finish_export(output):
    with connect(output, 'export', readonly=True) as connection:
        saved = _progress(connection)
    if not saved['done']:
        raise SnapshotError('export_incomplete')
    if not saved['released']:
        Client(saved['endpoint'], saved['tenant']).post('/release', {'snapshot': saved['snapshot']})
        with connect(output, 'export') as connection:
            connection.execute('UPDATE progress SET released=1 WHERE singleton=1')
            connection.commit()
    return export_status(output)


def export_records(output):
    with connect(output, 'export', readonly=True) as connection:
        saved = _progress(connection)
        if not saved['done']:
            raise SnapshotError('export_incomplete')
        sort = sort_spec(json.loads(saved['sort']))
        for row in connection.execute(f"SELECT {','.join(COLUMNS)} FROM records ORDER BY {order_sql(sort)}"):
            yield dict(row)


def export_digest(output):
    digest = hashlib.sha256()
    for record in export_records(output):
        digest.update(canonical(record)+b'\n')
    return digest.hexdigest()
