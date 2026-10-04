# Predeclared laboratory comparison

Inputs are synthetic but use the public fixed SQLite order schema and real HTTP
API/consumer. Customer demand, paid adoption and production savings are unknown.
Current primary source checks:2026-10-04UTC, SQLite isolation/backup/order semantics
and Datasette JSON API. Existing snapshot isolation and continuation tokens are
acknowledged, not treated as absent incumbent capabilities.

Use the same seeded records, sort, page size and mutation schedule for OFFSET,
correct live keyset, held SQLite read-transaction/keyset and durable snapshots.
Freeze an independent full SQL sequence before the schedule. Consume all rows,
including NULL, equal priorities, Unicode text and updated content. Report
missing/duplicate/extra identities and full typed sequence agreement, not just
count or ids. Record source/snapshot disk bytes, preparation work, requests,
transactions, complete sink/output hashes and observed time. Differences in
transport/workflow costs must be disclosed rather than compared as universal
speed claims.

In the static case, correct keyset/read transaction should agree with snapshot,
with no materialization disk and potentially lower costs: retain this no-benefit
case. With writes between pages, changing live consistency can miss or repeat
relative to the original frozen truth; this is a consistency distinction, not a
claim that a correctly implemented live keyset is broken. A held read transaction
can remain correct while its process survives. After actual reader/server death,
record whether each approach can resume that frozen version, and account for the
snapshot preparation and logical retention costs. Baseline execution and
independent review remain pending; no fabricated measurements are supplied here.
