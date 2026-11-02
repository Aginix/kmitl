===============================
Budget Dashboard Pool Tag Items
===============================

Lists the **Pool Tag** items — โครงการ/กิจกรรม and แผนจัดซื้อจัดจ้าง — beneath
each budget code (รหัสงบประมาณ) in the ตรวจสอบงบประมาณ report, so the report
shows which project or plan owns the money on a code.

* Items hang only under the budget code that holds their lines (no roll-up to
  ancestor codes — the ancestors already include them in their own figures).
* Each item row shows the report's full set of columns for its
  (budget code × tag) bucket. A "ไม่ระบุโครงการ/แผน" row carries the untagged
  remainder (e.g. เงินลอย), so the item rows reconcile with the code row.
* Items whose analytic account the user may not read (OU rules) show the
  project / plan name when that document is readable, else a
  "(ไม่มีสิทธิ์ดูรายการ)" label; their figures always stay.
* Item rows come from the same queries and RPC as the code rows (opt-in via
  the ``pool_tag_rows`` context the dashboard sends).
* One checkbox shows/hides every tag together (on by default, client-side, no
  reload), labelled from the registered tags (e.g.
  "แสดงรายการโครงการ/กิจกรรม/แผนจัดซื้อจัดจ้าง"); search also matches item
  code/name;
  clicking an item name opens the project / plan in a new tab.
* The reservation picker is unaffected.

This module is the generic engine and registers no tag by itself. The module
that owns a tag contributes it by overriding ``budget.dashboard._pool_tags``
(see ``kmitl_project_budget_dashboard`` / ``procurement_plan_budget_dashboard``).
