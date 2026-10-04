"""The finite orders/v1 schema and typed total order, not an arbitrary SQL API."""
import base64
import hashlib
import hmac
import json
import re
import time

SCHEMA = 'orders/v1'
MAX_INT = 2**63 - 1
COLUMNS = ('tenant', 'order_id', 'priority', 'title', 'total_cents', 'category')
FIELDS = {'order_id': 'integer', 'priority': 'integer', 'title': 'text', 'total_cents': 'integer'}


class SnapshotError(ValueError):
    """A private controlled error code; does not contain paths, tokens or records."""


def integer(value, minimum=0, maximum=MAX_INT):
    if type(value) is not int or not minimum <= value <= maximum:
        raise SnapshotError('invalid_integer')
    return value


def now_seconds(value=None):
    return integer(int(time.time()) if value is None else value)


def identity(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value):
        raise SnapshotError('invalid_identity')
    return value


def canonical(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise SnapshotError('invalid_json') from error


def decode_json(raw, cap=16384):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= cap:
        raise SnapshotError('invalid_body_size')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise SnapshotError('duplicate_json_key')
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(SnapshotError('nonfinite_json')))
    except (UnicodeError, ValueError, RecursionError) as error:
        raise SnapshotError('invalid_json') from error
    if not isinstance(value, dict):
        raise SnapshotError('object_required')
    return value


def query_spec(query=None):
    query = {} if query is None else query
    if not isinstance(query, dict) or set(query) - {'category'}:
        raise SnapshotError('invalid_query')
    category = query.get('category')
    if category is not None:
        identity(category)
    return {'category': category}


def sort_spec(sort=None):
    sort = {} if sort is None else sort
    if not isinstance(sort, dict) or set(sort) - {'field', 'direction', 'nulls'}:
        raise SnapshotError('invalid_sort')
    result = {'field': sort.get('field', 'priority'), 'direction': sort.get('direction', 'ASC'),
              'nulls': sort.get('nulls', 'FIRST')}
    if not isinstance(result['field'], str) or result['field'] not in FIELDS or result['direction'] not in ('ASC', 'DESC') or result['nulls'] not in ('FIRST', 'LAST'):
        raise SnapshotError('invalid_sort')
    return result


def order_record(record):
    if not isinstance(record, dict) or set(record) != set(COLUMNS):
        raise SnapshotError('invalid_order_columns')
    identity(record['tenant']); identity(record['category'])
    integer(record['order_id'], 1)
    if record['priority'] is not None:
        integer(record['priority'], -MAX_INT - 1)
    integer(record['total_cents'], 0, 10**12)
    if not isinstance(record['title'], str) or len(record['title']) > 512:
        raise SnapshotError('invalid_title')
    try:
        if len(record['title'].encode('utf-8')) > 2048:
            raise SnapshotError('invalid_title')
    except UnicodeError as error:
        raise SnapshotError('invalid_title') from error
    return dict(record)


def order_sql(sort):
    return f"{sort['field']} COLLATE BINARY {sort['direction']} NULLS {sort['nulls']}, order_id ASC"


def after_sql(sort, last):
    """Lexicographic strict suffix, including explicit NULL order and id tie."""
    if last is None:
        return '1', []
    if not isinstance(last, list) or len(last) != 3 or last[0] != FIELDS[sort['field']]:
        raise SnapshotError('invalid_position')
    value, order_id = last[1:]
    integer(order_id, 1)
    field = sort['field']
    if value is None:
        if field != 'priority':
            raise SnapshotError('invalid_position')
        prefix = f'{field} IS NOT NULL OR ' if sort['nulls'] == 'FIRST' else ''
        return f'({prefix}({field} IS NULL AND order_id > ?))', [order_id]
    if FIELDS[field] == 'integer':
        integer(value, -MAX_INT - 1)
    elif not isinstance(value, str) or len(value) > 512:
        raise SnapshotError('invalid_position')
    operator = '>' if sort['direction'] == 'ASC' else '<'
    suffix = f' OR {field} IS NULL' if sort['nulls'] == 'LAST' else ''
    return f'({field} {operator} ? OR ({field} = ? AND order_id > ?){suffix})', [value, value, order_id]


def position(record, sort):
    return [FIELDS[sort['field']], record[sort['field']], record['order_id']]


def validate_key(key):
    if not isinstance(key, bytes) or not 32 <= len(key) <= 64:
        raise SnapshotError('invalid_key')
    return key


def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def encode_cursor(payload, key):
    validate_key(key)
    body = _b64(canonical(payload))
    return body + '.' + _b64(hmac.digest(key, body.encode(), 'sha256'))


def decode_cursor(token, key):
    validate_key(key)
    if not isinstance(token, str) or len(token) > 4096 or not re.fullmatch(r'[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', token):
        raise SnapshotError('invalid_cursor')
    body, signature = token.split('.')
    expected = _b64(hmac.digest(key, body.encode(), 'sha256'))
    if not hmac.compare_digest(expected, signature):
        raise SnapshotError('cursor_signature')
    try:
        raw = base64.urlsafe_b64decode(body + '=' * (-len(body) % 4))
        payload = decode_json(raw, 4096)
    except (ValueError, UnicodeError) as error:
        raise SnapshotError('invalid_cursor') from error
    required = {'v', 'tenant', 'snapshot', 'query', 'sort', 'schema', 'expires', 'last'}
    if set(payload) != required or payload['v'] != 1 or payload['schema'] != SCHEMA:
        raise SnapshotError('cursor_schema')
    return payload
