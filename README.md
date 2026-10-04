# CursorSnapshot

Export a fixed SQLite order view across HTTP pages and process restarts. A durable
snapshot keeps the selected rows unchanged while the live order API receives
writes. Signed cursors bind tenant, snapshot, query, sort, schema, expiry and typed
last key. The consumer saves each page and its next cursor in one SQLite
transaction, so an interrupted page can be fetched again without losing rows.

The runnable application is a **laboratory order API**, with public synthetic
orders and keys. Production adoption, paid demand and revenue are unknown. It is
not an authentication service: the loopback API's `X-Tenant` header is trusted
application context for the demonstration. A MAC does not authorize a user. An
actual deployment must supply authentication, tenant authorization and TLS at
its application boundary.

Python3.11+ with SQLite3.37+ is supported. No runtime dependencies. Install an
ordinary wheel and run actual HTTP:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip wheel . --no-deps --wheel-dir dist
.venv/Scripts/python.exe -m pip install --no-deps --find-links dist cursorsnapshot
.venv/Scripts/python.exe -I examples/workflow.py
.venv/Scripts/python.exe -I -m unittest discover -s tests -v
```

The example creates8 orders through HTTP, starts an export, changes a live order,
continues paging and checks the frozen3600cent total before releasing the
snapshot. The installed CLI process test kills/restarts the actual server and
consumes the complete export and JSONL dump against independent expected rows.

For the CLI, create a source and manager with `cursorsnapshot init --database
PATH --role source|manager`. Import one fixed order JSON using `put --database
SOURCE --record FILE`. A key file is `cskey_` followed by padded URL-safe base64
of32–64 random bytes; generate a private deployment key without printing it:

```python
import base64, secrets
from pathlib import Path
Path("cursor-key.txt").write_bytes(b"cskey_" + base64.urlsafe_b64encode(secrets.token_bytes(32)))
```

Protect this file with host permissions and keep it outside source control. The
server commands below return one ready JSON line with the chosen loopback port:

```text
cursorsnapshot serve --source orders.sqlite --store snapshots.sqlite --key-file cursor-key.txt --port 8787
cursorsnapshot export --endpoint http://127.0.0.1:8787 --tenant shop --output export.sqlite --sort priority --direction ASC --nulls FIRST --page-size 100 --max-pages 1
cursorsnapshot resume --output export.sqlite --page-size 100
cursorsnapshot inspect --output export.sqlite
cursorsnapshot dump --output export.sqlite
cursorsnapshot status --store snapshots.sqlite --tenant shop
cursorsnapshot gc --store snapshots.sqlite
```

`export` creates a new sink; `resume` uses its saved endpoint/tenant/query/sort and
cursor. A successful partial run reports `done:false`; only a completed export
may be dumped. `dump` deliberately emits the entire records as JSONL. Summary
commands omit titles and cursor/key material. Both snapshot and export
initialization are create-only. Runtime refusal exits3, argument syntax exits2.
HTTP/network failure preserves existing checkpoint data. Initial snapshot creation
reports bounded allowlisted reasons: `remote_row_quota`/`remote_payload_quota`
mean filter a smaller export or change operator limits; `remote_active_quota`
means release unused snapshots or wait/collect; `remote_snapshot_expired` means
create a new export, preserving the partial sink for diagnosis. Unknown/malformed
remote errors retain only their HTTP status, without body/URL/credential text.
Initial snapshot creation
with a lost response can leave an orphan until expiry; it does not silently start
a new snapshot in an existing export. `export_uninitialized` requires a new sink.

The supported ordinary source table is exactly:

```sql
CREATE TABLE orders(
 tenant TEXT NOT NULL, order_id INTEGER NOT NULL, priority INTEGER,
 title TEXT NOT NULL, total_cents INTEGER NOT NULL, category TEXT NOT NULL,
 PRIMARY KEY(tenant,order_id)) STRICT;
```

Tenant and category are1–64 ASCII letters/digits/underscore/hyphen. Order id is a
positive int64, priority is NULL or int64, total cents0–10^12, title≤512Unicode
characters/2048UTF-8bytes. Imported matching ordinary tables can be read; the
demonstration's write API requires its owned source role. Views, generated
columns, extra columns, arbitrary SQL, custom collations and unknown ordering
semantics are unsupported. Query permits an optional exact category filter.
Tenant/category matching is case-sensitive BINARY, even if an imported source
declares a built-in NOCASE column collation; source collation cannot broaden
cursor identity.
Sort permits priority/title/total_cents/order_id, ASC/DESC, explicit NULL
FIRST/LAST, then unique order_id ASC. Text uses SQLite BINARY semantics without
Unicode normalization; each typed value and duplicate sort key is preserved.

Source rows are streamed within one read transaction into the manager's atomic
snapshot transaction. Whole-copy cost is O(selected rows); a50millionVM-step
scan budget limits query work, not hard CPU/RSS. Defaults:≤10000 rows,8MiB
canonical row bytes per snapshot,64MiB retained active payload,16 active
snapshots, TTL3600s. Configurable supported maxima are documented in
[DESIGN](docs/DESIGN.md). These are **logical content quotas**, not a hard SQLite
file/RSS quota: indexes, pages, journals and retained freed pages cost additional
disk. `gc` reclaims expired logical rows; it does not VACUUM or promise lower file
size.100000rows is an API cap, not a performance certification.

Expiry rejects new page leases at its exact boundary. A previously claimed
reader can finish within its bounded lease; GC and release preserve active
leases. A crashed reader leaves at most its lease duration. Missing source,
manager or export files fail without implicitly recreating them. Host files,
clock and signing key are trusted; external host corruption, unauthorized file
replacement and rollback are outside this guarantee. Symlink/hardlink aliases
and source/manager reuse are rejected at supported API boundaries. Cursors are
signed, **unencrypted** and should not be logged or shared.

Snapshots, keyset pagination and continuation tokens are established prior art.
[SQLite isolation](https://www.sqlite.org/isolation.html) explains transactional
frozen views; [Datasette's JSON API](https://docs.datasette.io/en/stable/json_api.html)
already provides pagination and next tokens. CursorSnapshot tests a local
composition of durable selected rows, cursor identity/lifecycle quotas and an
atomic resumable consumer. It makes no global novelty or incumbent deficiency
claim. [PILOT](docs/PILOT.md) specifies static and concurrent controls, including
correct live keyset and a held read transaction; baseline results remain pending
until actual execution. MIT. Local review/publication status is in
[ITERATIONS](docs/ITERATIONS.md) and [SELF_REVIEW](docs/SELF_REVIEW.md).
