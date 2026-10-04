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
retained with accurate attribution. Three real repair cycles are still pending.

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
