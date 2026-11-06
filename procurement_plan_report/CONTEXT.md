# Procurement Plan Report

Report/export layer for แผนจัดซื้อจัดจ้าง. Renders the plan-vs-actual procurement form that KMITL units submit to external agencies, as an on-screen overview and an Excel export.

## Language

**รายงานแผนจัดซื้อจัดจ้าง (Procurement Plan Report)**:
The plan-vs-actual government submission form. Delivered as **three parallel reports — one per form type** — each its own menu, its own OWL screen, and its own Excel workbook. A plan's smart button opens the screen for that plan's own form type, pre-scoped to its ปีงบ + หน่วยงาน. Not a per-plan document: each screen lists every plan of its type in scope.
_Avoid_: dashboard, per-plan report, combined overview

**แผน / ผล (Plan / Actual)**:
Every procurement item is shown as a pair of rows. **แผน** is the planned figures held on the `procurement.plan` itself. **ผล** is what actually happened, derived from the linked execution chain (พ.1 → สัญญา → เบิกจ่าย) and topped up by a few actual-only fields the chain cannot supply.
_Avoid_: budget vs commitment, estimate vs real

**ประเภทฟอร์ม (Form type)**:
Which of the three government form layouts an item prints under. Derived, never stored: **สิ่งก่อสร้าง** (`budget_account_id.is_asset = False`), **ครุภัณฑ์ (งวดเดียว)** (`is_asset = True` and ≤ 1 installment), **ครุภัณฑ์ (หลายงวด)** (`is_asset = True` and > 1 installment).
_Avoid_: category, sheet

**ประเภทครุภัณฑ์ (Equipment category)**:
The equipment-only column, equal to the plan's `budget_account_id` name (e.g. "ค่าครุภัณฑ์การศึกษา"). A leaf under the ครุภัณฑ์ root (5412) in the budget chart.
_Avoid_: asset type, form type

**งวด (Installment)**:
A planned disbursement tranche (`procurement.plan.payment`). Its count decides งวดเดียว vs หลายงวด for equipment. The ผล side of each งวด (actual disbursement date, amount, เลขที่เบิกจ่าย) comes from the disbursement layer.
_Avoid_: payment, period
