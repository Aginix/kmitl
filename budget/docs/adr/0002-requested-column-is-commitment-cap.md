# "ขอใช้ทั้งหมด" (Requested) is the commitment cap, not the amount used

The dashboard's **Requested total (3)** column sums the commitment **cap** (`budget.commitment.amount` = วงเงินอนุมัติ / approved spending limit) over *active* commitments — it is **not** the amount actually reserved or used.

Remaining (f) is computed as Current Budget (a) − Used (e), where Used (e) = the reserve→obligate→consume pipeline (b + c + d) = `total_reserved`. So the cap column is **informational and deliberately does not enter the remaining calculation**; the gap `(3) − (e)` reads as "approved authority not yet locked into the pipeline".

## Considered options

- **(3) = used total (e)** — rejected: the user wants approved authority shown separately from what has actually entered the pipeline. Making them equal would make the column redundant with (e).
