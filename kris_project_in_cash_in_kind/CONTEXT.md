# KRIS Project — In Cash / In Kind

Optional add-on for [KRIS Project](../kris_project/CONTEXT.md). When installed, research
projects (`kris.project.category` = งานวิจัย, seed record
`kris_project.project_category_research`) split their contracted value into an actual
cash component and a matching-fund component. Every cash-flow computation is repointed
at the cash component so KRIS does not deduct maintenance fees on money it never
receives.

Non-research projects are untouched; the add-on is a no-op on them.

## Language

**In Cash** (ทุนเงินสด):
The cash portion of a research contract — the money KRIS actually receives from the
client. The anchor for every cash-flow computation on research projects: operating
expense, maintenance deduction, revenue remaining, and the installment-total check all
read this instead of `project_value`. Only meaningful on projects whose category is
งานวิจัย; on other categories the field is hidden and its value is unused.

**In Kind** (ทุนสิ่งของ):
The matching-fund portion of a research contract — equipment, materials, labour or
services contributed by an external party (typically the client or a partner
institution) that never flow through KRIS's cash accounts. Recorded for reporting and
total-value display only; excluded from every cash-flow calculation so KRIS does not
deduct maintenance fees or chase receipts on money it will never see.

**Project Value** (มูลค่าโครงการ):
Redefined here as a stored derivation of `in_cash + in_kind` on research projects; on
non-research projects it stays a plain user input (compute is a no-op, field remains
editable). Installment totals and revenue-remaining checks anchor on `in_cash` for
research and on `project_value` for everything else. Shared definition of the concept
lives in [`../kris_project/CONTEXT.md`](../kris_project/CONTEXT.md).

**Cash Target** (technical):
The internal stored compute `cash_target` that every cash-flow calculation reads. Equals
`in_cash` on research projects and `project_value` on everything else. Introduced so
downstream computes have a single anchor instead of an `if is_research` sprinkled in
each one.
