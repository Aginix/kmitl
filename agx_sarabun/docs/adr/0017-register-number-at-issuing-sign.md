# ADR-0017 — ลงทะเบียน runs at the issuing sign (ลงนามในใบปะหน้า), not at completion

**Status:** Accepted  
**Date:** 2026-10-15  
**Module:** `agx_sarabun` (+ route templates in `kmitl_project_sarabun`, `budget_transfer_sarabun`)

**Supersedes the numbering timing of [ADR-0010](./0010-register-number-at-completion-not-at-send.md).**

---

## Context

ADR-0010 moved ลงทะเบียน from send to **completion**: the number ran when the *last*
gating step of the Route was positively done, whatever its verb. That matched KMITL's
rule only by coincidence — the shipped templates had a single ลงนามในใบปะหน้า step, so
"last step" and "the sign-out" were the same act.

KMITL's actual rule: **the number is issued the moment the holder of ลงนามในใบปะหน้า
(the คณบดี or whoever holds that right) signs.** A Route can continue after that sign
(e.g. a faculty หนังสือ signed out by the คณบดี and then เสนอ the อธิการบดี for อนุมัติ),
and the number must not wait for those later steps.

## Decision

- **A fourth, independent verb axis `issues_number` (ออกเลขที่หนังสือ).** Completing a
  step whose verb carries it runs `_assign_register_number()`. The built-in
  `verb_sign_approve` (ลงนามในใบปะหน้า) carries it; admins may tick it on other verbs.
  It is deliberately **not** tied to `is_signature`, so a future non-signing
  "ออกเลขที่หนังสือ" verb for ธุรการ/งานสารบรรณ (the phase-2 clerk gate) is configuration
  only.
- **The first issuing act wins.** `_assign_register_number()` stays idempotent, so a
  second issuing signer — or a re-sign after ตีกลับ — reuses the number.
- **Every Route must contain an issuing step**, checked at ส่ง next to the gating check,
  so a หนังสือ can never complete unnumbered. `_complete_document()` keeps its
  (now idempotent) call as a safety net.
- The templates that used only อนุมัติ (`kmitl_project_sarabun`,
  `budget_transfer_sarabun`) now use ลงนามในใบปะหน้า.

## Consequences

- **A circulating หนังสือ may already carry its number** (after the issuing sign). ที่
  stays `/` only until that sign.
- **ปฏิเสธ after the issuing sign voids the number** as a permanent gap (เลขยกเลิก) — the
  number was officially issued and is never reused. Voided numbers are again a normal,
  if rare, outcome (ADR-0010 had made them largely historical).
- **ตีกลับ after the issuing sign keeps the number**; the re-sent หนังสือ re-signs onto the
  same number (as Reset does — ADR-0011).
- Since the built-in issuing verb is also `is_signature`, a numbered หนังสือ is already
  past the ยกเลิกการส่ง window on the normal path.
- **The counter's ปีงบ comes from the issuing sign** instead of completion; the
  "never straddles a fiscal-year boundary" assumption of ADR-0010 still covers it.
- Register order = order of the issuing signs, not of completion.
- The verb data is `noupdate`, so the flag reaches existing databases through the
  `16.0.7.0.0` post-migration. The same migration **backfills** the number on every
  `circulating` หนังสือ already past its ใบปะหน้า sign, in sign order (they take the
  next counters, after any number issued since). Returned/draft ones get theirs at
  the next issuing sign; anything that fails to resolve a register is logged and
  still numbered at completion. The same migration turns the waiting อนุมัติ steps of
  any draft/returned หนังสือ lacking an issuing step into ลงนามในใบปะหน้า, so Routes
  seeded before the change can still be sent.
- Completing the issuing step by **เกษียนสั่งการ** (sign and forward) issues the number
  too — every positive disposition counts, not only ดำเนินการ.
