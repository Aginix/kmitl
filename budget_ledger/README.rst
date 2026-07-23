=============
Budget Ledger
=============

สมุดรายการเคลื่อนไหวงบประมาณ — a chronological, line-level report over the
**main budget ledger** (``budget.move``) so budget activity can be read at a
glance instead of opening ``budget.move`` / ``budget.commitment`` records one
at a time.

Each row is one ``budget.move.line`` normalised to a single "kind":

* **จัดสรร** (appropriation) — งบที่ได้รับจัดสรร (ต้นปี / เพิ่มเติม)
* **รับโอน / โอนออก** (transfer in / out) — การโอนงบ, แยกทิศตามเครื่องหมาย
* **เบิกจ่าย** (consume) — การใช้จ่ายจริง

Rows carry all six financial dimensions inline as ``[code] complete_name``
chips (code + full hierarchy), a signed amount, a record time, and a running
**งบคงเหลือ (ทางบัญชี)** = งบปัจจุบัน − เบิกจ่ายสะสม. The report covers the
**expense budget only**.

Features
========

* **ControlPanel** — ปีงบประมาณ, รหัสงบประมาณ, ทั้งหกมิติทางบัญชี
  (multi-select, hierarchy-aware), และ checkbox เลือกประเภทรายการ.
* **Summary bar** — งบปัจจุบัน (a) / จอง (b) / เบิกจ่าย (d) / **คงเหลือ (f)**
  reused verbatim from the monitoring dashboard (รายงานตรวจสอบงบประมาณ) so the
  ยอดคงเหลือ that also nets เงินจอง is always exact.
* **Timeline** — grouped by month (collapsible, with subtotals); each row shows
  วันที่/เวลา and expands to เลขที่ใบ, อ้างอิง, หมายเหตุ and the source document.
* **Export Excel** — ส่งออกตามข้อมูลที่เห็นบนหน้าจอ (WYSIWYG) ผ่าน ``report_xlsx``.

Scope & design
==============

This report reads the **main ledger only**. Reservation / obligation
(จอง / ผูกพัน) live in a separate book — the encumbrance register
(``budget.commitment``) — and are **not** shown here; see
``budget/docs/adr/0010-budget-ledger-separate-books.md`` and the *Budget Ledger*
entry in ``budget/CONTEXT.md``. Full design notes: ``docs/DESIGN.md``.

Technical notes
===============

* Read-only ``AbstractModel`` service ``budget.ledger`` (no stored data).
* All aggregation goes through the ORM (never raw SQL), so
  ``budget_operating_unit`` record rules scope rows to the user's operating
  units automatically.
* The running balance is computed server-side over the whole filtered scope,
  ordered by date; draft/review rows (optional) are shown but excluded from it.
