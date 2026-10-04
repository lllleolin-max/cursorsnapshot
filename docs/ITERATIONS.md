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
