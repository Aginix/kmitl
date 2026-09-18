============================
Receipt KMITL Allocation
============================

Lets a KMITL cash receipt product stay a single line on the receipt while,
at posting time only, fanning its revenue out into several GL accounts and
organizational units (การปันส่วนรายได้) — e.g. a single
ค่าธรรมเนียมการศึกษา line splitting into ค่าบำรุงสถาบัน, ค่าธรรมเนียม
การศึกษา (คณะ/หลักสูตร), and ค่าบริการสำนักทะเบียน.

Configuration
=============

On a product's **การปันส่วนรายได้ (ใบเสร็จ)** tab, add one **Allocation
Bucket** row per target revenue account. Each bucket is either a fixed
amount or a percentage of the remainder (the line amount minus every fixed
bucket); percentage buckets on a product must sum to 100%. Leaving one of
the six analytic dimensions blank on a bucket makes that leg inherit the
receipt's own value for that dimension; filling it in pins the leg to a
fixed unit.

A product with no allocation buckets posts exactly as `receipt_kmitl` does
today — one revenue leg on the line's own income account.

See ``CONTEXT.md`` for the glossary and ``docs/adr/0001-*.md`` for why the
Cash debit stays lumped while only the revenue credit fans out.
