"""Installed application and resumable exporter commands."""
import argparse
import base64
from pathlib import Path
import sys
from .client import Client, export_digest, export_records, export_status, finish_export, start_export, step_export
from .http_api import make_server
from .model import SnapshotError, canonical, decode_json, integer, validate_key
from .snapshots import collect, status
from .storage import initialize, put_order


def load_key(path):
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(129).strip()
        if len(raw) > 128 or not raw.startswith(b'cskey_'):
            raise SnapshotError('invalid_key_file')
        key = base64.b64decode(raw[6:], altchars=b'-_', validate=True)
        return validate_key(key)
    except (OSError, ValueError) as error:
        raise SnapshotError('invalid_key_file') from error


def _run_pages(output, size, max_pages):
    integer(size, 1, 1000); integer(max_pages, 0, 100000)
    result = export_status(output)
    consumed = 0
    while not result['done'] and (not max_pages or consumed < max_pages):
        result = step_export(output, size=size); consumed += 1
    if result['done']:
        result = finish_export(output)
        result['content_sha256'] = export_digest(output)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(prog='cursorsnapshot', description='Persistent bounded SQLite order exports over loopback HTTP')
    subs = parser.add_subparsers(dest='command', required=True)
    p = subs.add_parser('init'); p.add_argument('--database', required=True); p.add_argument('--role', choices=['source','manager'], required=True)
    p = subs.add_parser('put'); p.add_argument('--database', required=True); p.add_argument('--record', required=True)
    p = subs.add_parser('serve'); p.add_argument('--source', required=True); p.add_argument('--store', required=True); p.add_argument('--key-file', required=True)
    p.add_argument('--host', default='127.0.0.1'); p.add_argument('--port', type=int, default=0)
    p.add_argument('--max-rows', type=int, default=10000); p.add_argument('--max-payload-bytes', type=int, default=8*1024*1024)
    p.add_argument('--max-total-payload-bytes', type=int, default=64*1024*1024); p.add_argument('--max-active', type=int, default=16)
    for name in ('export','resume'):
        p = subs.add_parser(name); p.add_argument('--output', required=True); p.add_argument('--page-size', type=int, default=100); p.add_argument('--max-pages', type=int, default=0)
        if name == 'export':
            p.add_argument('--endpoint', required=True); p.add_argument('--tenant', required=True); p.add_argument('--category')
            p.add_argument('--sort', choices=['priority','title','total_cents','order_id'], default='priority')
            p.add_argument('--direction', choices=['ASC','DESC'], default='ASC'); p.add_argument('--nulls', choices=['FIRST','LAST'], default='FIRST')
            p.add_argument('--ttl-seconds', type=int, default=3600)
    for name in ('inspect','dump'):
        p = subs.add_parser(name); p.add_argument('--output', required=True)
    p = subs.add_parser('gc'); p.add_argument('--store', required=True)
    p = subs.add_parser('status'); p.add_argument('--store', required=True); p.add_argument('--tenant', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            initialize(args.database, args.role); result = {'created': True, 'role': args.role}
        elif args.command == 'put':
            with Path(args.record).open('rb') as stream:
                raw = stream.read(16385)
            put_order(args.database, decode_json(raw)); result = {'stored': True}
        elif args.command == 'serve':
            server = make_server(args.source, args.store, load_key(args.key_file), host=args.host, port=args.port,
                                 quotas={'max_rows': args.max_rows, 'max_payload_bytes': args.max_payload_bytes,
                                         'max_total_payload_bytes': args.max_total_payload_bytes, 'max_active': args.max_active})
            sys.stdout.buffer.write(canonical({'ready': True, 'port': server.server_port})+b'\n'); sys.stdout.flush()
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0
        elif args.command in ('export','resume'):
            integer(args.page_size, 1, 1000); integer(args.max_pages, 0, 100000)
            if args.command == 'export':
                start_export(Client(args.endpoint, args.tenant), args.output, query={'category': args.category},
                             sort={'field': args.sort, 'direction': args.direction, 'nulls': args.nulls}, ttl_seconds=args.ttl_seconds)
            result = _run_pages(args.output, args.page_size, args.max_pages)
        elif args.command == 'inspect':
            result = export_status(args.output)
        elif args.command == 'dump':
            for record in export_records(args.output):
                sys.stdout.buffer.write(canonical(record)+b'\n')
            return 0
        elif args.command == 'gc':
            result = collect(args.store)
        else:
            result = status(args.store, args.tenant)
        sys.stdout.buffer.write(canonical(result)+b'\n')
        return 0
    except (SnapshotError, OSError) as error:
        code = str(error) if isinstance(error, SnapshotError) else 'io_failure'
        sys.stderr.buffer.write(canonical({'error': code})+b'\n')
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
