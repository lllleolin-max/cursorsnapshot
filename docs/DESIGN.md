# State, identity and costs

Snapshot rows are materialized in an owned SQLite manager, distinct from the
source. A source SELECT read transaction freezes all selected typed fields.
Tenant predicate and optional category predicate apply before extraction. The
manager transaction includes metadata and every frozen row or commits nothing.
A process interrupted while building cannot expose a ready partial snapshot.
The maximum row+1 scan distinguishes quota overflow from a completed exact-limit
snapshot. A VM progress handler aborts excessive source-query work; native sort
memory and wall time are not bounded by this callback.

The source schema and returned values are validated rather than running an
arbitrary caller SQL fragment. SQL identifiers and directions come only from
finite constants; values use parameters. NULL handling is explicit in both the
order and strict suffix predicate. One unique tenant/order_id tie-breaker
establishes a total order, including nonunique priority/title values. The manager
does not serve live source rows after creation.

Cursor payload version1 includes tenant, random snapshot id, normalized query,
normalized sort, orders/v1 schema, expiry and typed last value/order_id. HMAC-SHA256
authenticates its canonical base64url body with a32–64byte key, using constant-time
comparison. Metadata and caller context must match. Cursor opacity is not
confidentiality or authentication. An app must authorize snapshot creation,
paging and release for its authenticated tenant. HTTP here binds only literal
loopback; clients allow trusted HTTPS endpoints or literal-loopback HTTP, disable
environment proxies and redirects, and cap request/response bytes. No deployment
TLS/auth stack or arbitrary remote URL import is provided.

Snapshot states are ready/released; creation is one invisible transaction.
Reader leases have random token and expiry. New leases require an unexpired ready
snapshot; an admitted reader holds its lease while it reads. GC deletes expired
leases and expired snapshots without active leases in one transaction. Manual
release refuses active readers and deletes frozen rows before marking released.
Release is idempotent if metadata is already gone. TTL1–86400s; lease1–60s;
page1–1000rows. Logical limits: per snapshot0–100000rows,0–64MiB canonical row
bytes; all ready snapshots0–256MiB; concurrent snapshots1–128. Zero row/byte
quota admits only an empty selection. These are validation/retention domains,
not benchmarks for maximum throughput.

The exporter obtains one page outside its sink transaction. Its sink transaction
checks unchanged prior progress, inserts all typed rows and changes next cursor
or completion flag together. A failed commit leaves its old progress and rows.
Two competing consumers cannot commit the same prior page twice. A completed
count must match snapshot's expected count. Finish releases the snapshot only
after a complete durable consumer result; release response loss can be retried.
No cursor resume survives its snapshot expiry; partial data stays available for
diagnosis and is not merged into a new snapshot.

Source SQLite isolation and backup capabilities are older primitives. An
ongoing read transaction can already give stable pages while that connection
survives, particularly with WAL. This project pays materialization/storage costs
to persist selected rows across independent requests/processes. It does not
preserve all database history or make a simple static export cheaper. See
[SQLite isolation](https://www.sqlite.org/isolation.html) and
[online backup](https://www.sqlite.org/backup.html) for the underlying facilities;
this project uses selected-row read transactions, not raw main-file copies.

SQLite operations use2second busy timeout, FULL sync and owned role/version checks.
Caller files and sidecars must be ordinary unique files; initialization is
exclusive. The host and directory contents are trusted during operations; this
is not a sandbox against an adversary changing paths concurrently. Disk retained
after deletes requires operator housekeeping, and exported business records are
plaintext. Clock rollback, signing-key compromise, hardware power loss and
Internet exposure are not certified.
