# Baseline and real correction history

Builder GPT-6.1-Sol / Ultra. This is a new project with no inherited old-project
cycles. Initial feature implementation is one baseline, not three repairs. It
will be frozen with an exact40characterSHA and ordinary installed test/HTTP
receipt before review. Planned audit routes cover typed/NULL pagination,
checkpoint process interruption and reader/expiry/quota lifecycle, then binding,
aliases and missing/changed files. A route counts only after an actual defect or
measured product insufficiency, substantive source correction and unchanged
original FAIL->PASS probe. No-finding, document edits, test/harness growth and
splitting the initial feature into commits do not count. Independent review
files are never rewritten by the builder; false alarms and harness failures are
retained with accurate attribution. Four actual core corrections now exist;
independent acceptance and public delivery remain pending.

Pre-baseline installation actually found Windows cleanup failures because the
initializer used SQLite's transaction context without explicitly closing its
connection. The initializer now closes its handle. The first11-test failed log,
original wheel and temporary data remain in builder evidence; its corrected
ordinary installation passed11tests. This work predates the initial Git
baseline, so it is not counted as one of the three post-baseline repair cycles.
Source schema validation is inside the read transaction and verifies the unique
tenant/id primary key; a reader checks its lease again after consuming its page.

## Round1 — create-only SQLite sidecar namespace

Before330fbbc598102982dc3ea2ff6d630f88e1d3b28e. Actual unchanged builder probe
`orphan_sidecars.py`, SHA256159e64fb22c13f752d8e48b40f36b8294e4c922b168cd2696f887ab260c17bd5,
created unrelated ordinary files under a fresh target's -journal/-wal/-shm names.
Initialization accepted all9role/suffix cases and physically deleted existing
journal/WAL contents. The main filename's exclusive creation did not protect
SQLite's broader file namespace. Original wheel-installed and exact canonical
before runs both exit1; complete receipts remain in builder evidence. This is a
real file-preservation defect, not a hypothetical symlink attack.

Correction refuses any existing sidecar before creating/opening the new main
file. Existing valid databases still support their legitimate SQLite sidecars
through normal connect operations. The same probe must report controlled refusal,
no main file and identical sidecar bytes for all9cases, exit0. This round's exact
after SHA and ordinary-wheel results will be appended after verification; initial
feature/test growth/document edits do not count as additional rounds.

After3a7cc58c845f00a3c3429cadf9505d83f242dafb, canonical ordinary wheel/fresh
installation passed12tests5.499s, actual HTTP example and all9 unchanged original
sidecar probe cases, exit0. Every foreign sidecar hash is preserved and no main
file is created. Before canonical330f probe exits1. Independent review pending.

## Round2 — source collation must not widen tenant/query identity

Before3a7cc58c845f00a3c3429cadf9505d83f242dafb. Original unchanged builder
`tenant_collation.py` SHA2560a468e48ba17b0b825cc6aa4e22e0285a7165555814cddc61beffc576c511f76
builds a supported ordinary source with built-in NOCASE tenant/category columns.
Native raw SQLite BINARY-filter truth selects one shop/open row. Actual HTTP
snapshot/page selected three rows including other tenant SHOP and category OPEN,
because unqualified predicates inherited the source column collation. MAC binding
alone did not protect the selected data's identity. Canonical installed before
receipt preserves all rows/metadata and exits1; LAB values contain no real data.

Correction explicitly applies BINARY to source tenant/category predicates and
checks each extracted record's exact identities within the read transaction. It
retains the ordinary source adapter and built-in NOCASE source support, rather
than deleting the affected domain. The same actual HTTP/native SQL probe must
select exactly the original one-row truth, exit0. This whole identity/filter
problem is one round, not two fixes counted separately; exact after/results will
be recorded after ordinary installation verification.

After8993a42c2b9cf8e231b3f146314ed08df32e2eca, canonical ordinary wheel/fresh
installed13tests4.749s, actual HTTP example and unchanged original collation probe
all exit0. HTTP now exactly matches the one-row raw SQLite truth. No source/domain
capability was removed. Independent review remains separate.

## Round3 — actionable bounded HTTP refusal mapping

Before8993a42c2b9cf8e231b3f146314ed08df32e2eca. Original unchanged builder
`http_diagnostics.py`, SHA25676ed5798f260b4371899d506e7acf9751796a82c76b70891350645653d114a85,
actually creates three HTTP scenarios. Native server error bodies distinguish
row_quota/active_quota/snapshot_expired, but installed SDK discards them and
reports remote_http_400 for both quotas and remote_http_410 for expiry. Callers
cannot choose filter/limit vs release/collect vs create-new-export from that
public error. Refused states remained intact. This is a measured operational
interface insufficiency (P3), not a new data-loss claim or an invariant P2.

Correction reads/closes HTTPError with1024byte cap and exposes only a finite exact
private-code allowlist. Unknown/malformed/oversized remote bodies remain generic
HTTP codes and are never reflected. The same native-server/SDK probe must now
observe remote_row_quota/remote_active_quota/remote_snapshot_expired, exit0, with
the same refusal state. A privacy control verifies that arbitrary remote values
stay private. This round may be rejected by independent review if judged
insufficiently substantive; three repairs never terminate further core review.
Exact after SHA and installed results will be recorded after verification.

The HTTP pilot script is additional verification, not another repair: static
OFFSET/live keyset/held read transaction/snapshot all match complete SQL truth;
with the same writes a held transaction remains correct; after a real process
kill it loses its frozen view while a durable snapshot continues. Costs and
negative/equal cases remain; mature live pagination is not labeled broken for
having a different consistency contract.

After272b665548cd7744fb7a93b7e8e5d0ce8982bb4a, canonical ordinary/fresh
installation passed15tests5.904s, original three diagnosis scenarios, actual HTTP
example and12-case real HTTP fair controls, all exit0. Independent reviewer
does not count the diagnosis enhancement as a required core correction; it is
retained honestly as operational improvement rather than used to reach three.

## Round4 — actual killed dirty-page transactions must recover publicly

Before272b665548cd7744fb7a93b7e8e5d0ce8982bb4a. Original unchanged builder
`killed_checkpoint.py`, SHA256a96be057ec33cf5be6c056b2561ff277018a48b6be3f1de16af950457af65462,
receives a legal1000row HTTP page with512emoji/2048UTF-8byte titles,2,139,786byte
complete output below the4MiB response cap. A real consumer subprocess is killed
after all SQL inserts and before commit, with13832byte journal. Public
step_export then fails sqlite_failure: its mode=ro progress read cannot perform
SQLite hot-journal rollback. The raw RW oracle is opened only AFTER the product
attempt, verifies0rows/done0 and cannot mask that public recovery failed. Original
canonical wheel probe exits1; no data loss is claimed.

Independent pre-review suggested checking the analogous manager entry point.
Original `killed_materialization.py`, SHA256ace3a6b734cd1b4fb4b1e5e0e027212b08682d2ddd02fefc981866984b111197,
really kills a1000row spilling snapshot build before publication commit, journal
22016bytes. Public status likewise fails sqlite_failure; only then the RW oracle
observes no partial snapshots/rows. This is the same owned-read recovery defect,
grouped as one correction round, not counted twice.

Correction validates a static SQLite header's owned role/version BEFORE allowing
SQLite RW recovery, then enforces SQL query-only for read entry points. Foreign
source extraction remains mode=ro; ownership does not authorize recovery of a
different application's source. Foreign role/sidecar bytes are protected and
query-only writes rejected. Unchanged original probes must publicly resume the
complete1000row consumer without loss/duplicates and allow empty manager status,
GC and a fresh complete snapshot after the killed unpublished transaction. Real
sidecar/tenant/recovery chains are the three required core repairs; operational
diagnostics, initial feature, pilot/tests growth and docs do not substitute.
Exact after/result observations will follow verification; further known P2s
still block acceptance.

Afterc8e81f7202db25ecc8dd5db69842278c75521e3a, canonical ordinary wheel/fresh
installation passed17tests6.648s, actual HTTP example, both original kill probes
and12case fair HTTP pilot, all exit0. Public consumer recovery committed all1000
rows/done1 and exactly matched2,139,786full JSONL bytes; the manager publicly
returned empty status/GC before any raw RW oracle, then built a fresh1000row
snapshot with full content agreement. This verifies three core chains at that
point, without counting the operational diagnosis enhancement.

## Round5 — paired database namespaces must be disjoint

Independent unchanged probe `cursorsnapshot_source_namespace.py`, exact builder
copy SHA2567343baa8500d3c2e10341f2a311976b5325550ecdd9683f98c30d49ffe888288,
found a distinct actual data-loss defect at272b665548cd7744fb7a93b7e8e5d0ce8982bb4a.
Our original-probe ordinary c8e81f7 rerun also exits1: an owned, quiesced WAL source
and a manager named source.sqlite-wal pass the existing distinct-main guard;
actual HTTP creates a ready snapshot and accepts an order write, after which
SQLite removes the manager and paging returns remote_file_missing. The -shm
case rejects setup only after changing manager bytes. The -journal negative
refuses and preserves bytes; its negative result is retained. Both receipts
remain immutable. This is not the prior hot-journal read recovery problem.

Correction compares the source/manager pair's entire main/-journal/-wal/-shm
namespaces, both filename directions and same-file aliases, before opening ANY
SQLite connection at integration boundaries. Standalone create-only initialization
cannot infer a future source/manager pairing; it still protects its own existing
sidecars. No SQL capability or legitimate disjoint source WAL support is removed.
The exact original positional-output probe must now refuse all conflicting pairs
before creating a snapshot or changing either file, exit0. A six-direction
regression covers HTTP setup and direct SDK extraction with byte preservation.
Exact installed after results will be appended after verification.

After8400c98b138802165d1838fafd957588e0c80fe2, canonical ordinary/fresh
installation passed18tests8.478s, actual HTTP example, both unchanged1000row kill
probes, the independent unchanged namespace probe,12-case real HTTP controls
and100/1000row installed CLI whole consumers, all exit0. Each conflicting
namespace refused path_alias and preserved the manager's complete28672bytes.
WAL support for disjoint normal source/store files remains exercised in controls.
The two whole exports contain9485/97772JSONL bytes and exactly match independently
frozen typed SQL rows, sums5050/500500, after post-freeze writes and actual server
death/restart. Four substantive core corrections are retained; round3 remains
an operational P3 and is not counted toward the three-core requirement.

One development command accidentally used the old installed330f local .venv
against later18test files, producing expected old-behavior failures. This was a
runtime association mistake in a development run, not a fifth new defect or a
passing current-version receipt. Current source development checks then passed;
all accepted version claims come from separate canonical fresh wheel packets
with isolated module bytes checked. Original failed history remains retained.

## Round6 — controlled HTTP length refusal (operational P3)

Original frozen0f0a257e95eb148b8d2fdac6257eb3d9b4796e70 and its final ordinary
packet remain retained. Independent unchanged `cursorsnapshot_large_content_length.py`
copy SHA256c457b363ff81c83a047017f1330fabd261ad02d38f774a3d2eddedf3f7c6e973
declares5000ASCII nines within the native65536byte header limit. Python int()
raises its digit-limit ValueError, producing RemoteDisconnected and a traceback
instead of the promised private400. Our original0finstalled rerun exits1 with
1603stderr bytes. Both databases remain byte-identical, zero snapshots, service
continues; no core data-loss/P2 claim and no additional core round is counted.

Root explicitly authorized a narrow successor repair after freeze. Length is
checked as ASCII decimal, leading zeros removed and normalized value compared
lexically with16384 BEFORE bounded int conversion.5000leading zeros plus2 remain
legal, rather than shrinking the supported header domain. One actual HTTP
regression checks the original oversize, long zero-prefixed legal value,
Latin1non-ASCII digit, exact16KiB/one over, zero/negative/empty and duplicate
headers. Exact after SHA and ordinary receipt are supplied by successor handoff;
the original0fQA/CI/version facts are not relabeled as successor execution.

The first successor8d725e3 ordinary suite run found a new regression-harness
mistake: HTTPConnection is not a context manager. It failed before making that
regression's first request; other18tests passed. The failed packet is preserved.
The test now uses contextlib.closing; no product behavior changed in this test
repair, and it is not an extra correction round. Final successor receipt names
the exact new SHA and reruns the unchanged independent original probe.
