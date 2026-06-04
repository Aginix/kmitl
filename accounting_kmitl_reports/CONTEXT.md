# Accounting Reports

Financial-statement reports for KMITL — Trial Balance, Profit and Loss, Balance Sheet and Cash Flow Statement — computed over the standard `account.move.line` ledger and filterable by the KMITL accounting dimensions.

## Language

**Trial Balance (งบทดลอง)**:
A per-account listing, over a date range, of the opening balance, the period movement and the ending balance — each shown as Debit, Credit and Balance. Opens straight from the menu as an OWL client action and prints as a QWeb PDF that shares the same compute.
_Avoid_: trial sheet, TB

**Balance section (หมวด)**:
One of the Trial Balance's three column groups — **Opening** (ยอดยกมา), **During the year** (ระหว่างงวด) and **Ending** (ยอดคงเหลือ). Each section carries a Debit, a Credit and a Balance sub-column. In this report "หมวด" means a balance section — **not** an account category/type (asset/liability/…) and not an account group.
_Avoid_: category, account type, group (those name a chart-of-accounts grouping, not a column section)

**Balance (a section's sub-column)**:
The signed net of a section = Debit − Credit, negative when Credit exceeds Debit. Shown as the third sub-column under each balance section.
_Avoid_: net, total

**Accounting dimension (มิติทางบัญชี)**:
A KMITL analytic plan used to filter the report, selected by `root_plan_id.code`. The Trial Balance filters the four core dimensions — Departments (ส่วนงาน), Sources (แหล่งเงิน), Funds (กองทุน) and Activities (ด้าน/แผนงาน/กิจกรรม) — read from each move line's `analytic_distribution`. Within one dimension the picks are OR-ed (a hierarchical pick also matches its descendants); across dimensions they are AND-ed.
_Avoid_: analytic tag, segment
