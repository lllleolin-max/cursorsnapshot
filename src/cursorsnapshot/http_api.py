"""A loopback laboratory application; tenant header is context, not authentication."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
from .model import SnapshotError, canonical, decode_json, identity, integer, validate_key
from .snapshots import create_snapshot, page, release
from .storage import connect, put_order, safe_path, validate_source


def make_server(source, store, key, *, host='127.0.0.1', port=0, quotas=None):
    validate_key(key)
    try:
        if not ipaddress.ip_address(host).is_loopback:
            raise SnapshotError('loopback_server_only')
    except ValueError as error:
        raise SnapshotError('loopback_server_only') from error
    quotas = {} if quotas is None else dict(quotas)
    if set(quotas) - {'max_rows', 'max_payload_bytes', 'max_total_payload_bytes', 'max_active'}:
        raise SnapshotError('invalid_quota')
    for name, value in quotas.items():
        lower, upper = {'max_rows': (0, 100000), 'max_payload_bytes': (0, 64*1024*1024),
                        'max_total_payload_bytes': (0, 256*1024*1024), 'max_active': (1, 128)}[name]
        integer(value, lower, upper)
    integer(port, 0, 65535)
    safe_path(store, (source,))
    with connect(source, readonly=True) as connection:
        validate_source(connection)
    with connect(store, 'manager', readonly=True):
        pass

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_json(self, status, value):
            raw = canonical(value)
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            self.connection.settimeout(2)
            try:
                if self.headers.get('Transfer-Encoding') is not None or len(self.headers.get_all('Content-Length', [])) != 1 or len(self.headers.get_all('X-Tenant', [])) != 1:
                    raise SnapshotError('invalid_headers')
                tenant = identity(self.headers['X-Tenant'])
                length = self.headers['Content-Length']
                if not length.isascii() or not length.isdecimal():
                    raise SnapshotError('invalid_body_size')
                # ASCII 1*DIGIT can contain arbitrarily many leading zeros
                # within the server's header cap. Bound lexically before int(),
                # avoiding Python's digit-limit exception for an oversized value.
                length = length.lstrip('0') or '0'
                if length == '0' or len(length) > 5 or (len(length) == 5 and length > '16384'):
                    raise SnapshotError('invalid_body_size')
                length = int(length)
                if self.headers.get('Content-Type') != 'application/json':
                    raise SnapshotError('invalid_content_type')
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise SnapshotError('truncated_body')
                body = decode_json(raw)
                if self.path == '/snapshots' and not set(body) - {'query', 'sort', 'ttl_seconds'}:
                    result = create_snapshot(source, store, tenant, key, query=body.get('query'), sort=body.get('sort'), ttl_seconds=body.get('ttl_seconds', 3600), **quotas)
                elif self.path == '/pages' and set(body) <= {'cursor', 'query', 'sort', 'size'} and 'cursor' in body:
                    result = page(store, tenant, body['cursor'], key, query=body.get('query'), sort=body.get('sort'), size=body.get('size', 100))
                elif self.path == '/release' and set(body) == {'snapshot'}:
                    result = release(store, tenant, body['snapshot'])
                elif self.path == '/orders':
                    if body.get('tenant') != tenant:
                        raise SnapshotError('tenant_binding')
                    put_order(source, body)
                    result = {'stored': True}
                else:
                    raise SnapshotError('unknown_route_or_fields')
                self.send_json(200, result)
            except SnapshotError as error:
                code = str(error)
                status = 410 if code in ('snapshot_gone', 'snapshot_expired') else 409 if code == 'reader_busy' else 503 if code in ('sqlite_failure', 'file_missing') else 400
                self.send_json(status, {'error': code})
            except (TimeoutError, ConnectionError, OSError):
                self.close_connection = True

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server
