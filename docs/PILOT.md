# Real HTTP controls and complete consumers

Builder ordinary-installed8400c98b138802165d1838fafd957588e0c80fe2 ran at UTC
2026-10-04 21:43:22–21:44:33 on Windows/Python3.14.3. Observations are laboratory
evidence, not customer revenue, production throughput or maximum-domain
certification. Independent review and remote CI/publication remain pending.
Current primary source checks:2026-10-04UTC, SQLite isolation/backup/order semantics
and Datasette JSON API. Snapshot isolation and continuation tokens are prior art.

Run `python -I probes/pilot.py --output NEW_DIRECTORY` with an ordinary installed
wheel. It preserves every input, full native SQLite frozen truth, full output
JSONL, content hashes and source/snapshot preparation, startup/restart, workflow
time, requests and disk bytes. The same20orders include NULL, equal priorities
and Unicode/BINARY text; page size4. After the first page the schedule deletes
id2, moves an already consumed row's sort key/content, and inserts id999. All
four modes receive the same schedule. No core pagination helper is used by the
independent native source truth or baseline SQL algorithms.

| Mode | Static frozen truth | Writes, process survives | Writes, real process restart |
|---|---|---|---|
| Live OFFSET | Full agreement | Missing2,17; extra999;1duplicate;1changed occurrence | Same mismatch |
| Correct live keyset | Full agreement | Missing2; extra999;1duplicate;1changed occurrence | Same mismatch |
| Keyset in held SQLite read transaction | Full agreement | Full agreement | Original connection view lost; same mismatch as live keyset |
| Durable selected-row snapshot | Full agreement | Full agreement | Full agreement |

Live consistency is a different contract; those mismatches do not prove that
correct live keyset is broken. A held read transaction already gives the same
frozen answer while its connection survives. The durable snapshot pays material
preparation/storage costs to retain selected rows after process death; it is not
an invention of snapshots, keysets or HMAC tokens.

Static controls all output the same1879bytes/hash
`c99bb1bff18627eb9f245184d8443ab676c97e26a3a7078d0dd126247f47e410`.
Each non-snapshot control uses6HTTP requests and no snapshot database. Snapshot
uses7HTTP requests including creation/release and a28672byte manager. Its observed
creation took approximately0.05s; workflow including writes/restart took0.55s,
versus approximately0.52–0.54s for restarted controls. These are single run
observations with all costs preserved, not a speed benchmark or statistically
established improvement. Source preparation and process startup are separate
fields; full JSON provides unrounded observations. Static/no-kill controls are
the explicit no-benefit/equivalent result, not omitted from the report.

The baseline paging experiment uses the same direct JSON checkpoint for all
modes, including snapshot, to compare paging mechanisms. It does not pretend
that this test sink has the product's atomic SQLite page/next-cursor protocol.
That protocol is separately exercised by installed CLI and actual spilling
transaction kills, whose public recovery occurs before the raw RW oracle.

Run `python -I probes/scale.py --output NEW_DIRECTORY` for actual HTTP order
creation and registered CLI export/partial/resume/dump at100 and1000rows. Native
SQLite truth uses `(priority IS NOT NULL),priority,order_id`, independent of the
product's keyset/order functions. After the first73row page, two real HTTP writes
change/add live data; the real server is killed and restarted on the same port.
The entire result, typed sequence, count, sum and every JSONL byte are consumed.

| Orders | Pages | Frozen sum cents | Full output bytes | Prepared manager bytes | After release bytes | Source writes s | Prepare/first page s | Resume s |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|100|2|5050|9485|45056|45056|1.546|0.555|0.529|
|1000|14|500500|97772|143360|143360|17.019|0.543|1.300|

Complete output hashes are
`0c178195068b897fc91959005eb8dcf13bea1a261a3ef1fe297df538e50e6fb9`
and `f7ccfa63b33d1ab347cdcecf7530b57b60d27b99e9f7a655d380057a7daebe48`.
Freed logical rows do not shrink the manager's physical file: retained freed
pages are visible in the equal before/after file sizes. These sizes exclude
transient journals/RSS, and the API's100000row cap is not a measured throughput
promise. Larger legal2048UTF-8byte titles are fully consumed by the1000row kill
probe:2,139,786bytes, never truncated to a preview or id-only check.

The final handoff supplies exact SHA/commands, complete receipt/log hashes and
ordinary wheel association. Final reruns can have different observed times and
snapshot ids; the quoted8400 observations remain tied to their original packet.
