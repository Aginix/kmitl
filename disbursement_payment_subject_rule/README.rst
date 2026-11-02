==================================
Disbursement Payment Subject Rules
==================================

Picks the payment subject (เรื่องที่จ่าย) of a disbursement request automatically.

A rule names a payment subject and, optionally, the payee type, the payment type
(direct / advance / prepaid) and the source, department, fund and activity dimensions
it applies to. An empty criterion matches any value, and a rule on a parent department,
fund or activity covers all of its children. Rules are matched in sequence order and the
first match wins.

The subject is picked whenever the request's payment lines are brought up to date (the
last bill posting, the audit, creating the vouchers), but only for a request that has no
subject yet and no voucher. Setting it re-derives every payee's paying account exactly
as a hand pick does, and the auditor can still change it while it is theirs to choose.

Configure the rules in Finance ▸ Settings ▸ Payment Data ▸ Payment Subject Rules. No
rule is seeded.
