# Official document renders signatures only (per-verb `show_signature`); the drafter need not sign

> **Update (UAT revision):** the non-originator verb *catalogue* was replaced on UAT feedback — the 6 behaviour-derived verbs became the 8 reviewed verbs in *Step verbs* ([CONTEXT.md](../../CONTEXT.md)). The **three-axis model below stands unchanged**; only two incidental statements are superseded: `is_signature` is **no longer unique to ลงนาม-อนุมัติ** (the UAT set has **two** authoritative signs — *ลงนามในใบปะหน้า/เอกสารเพื่อลงนาม* and *อนุมัติ/อนุญาต/เห็นชอบและลงนามกำกับ*; the first to occur closes the recall window), and a pure non-signing *ส่งต่อ* verb was dropped.

**Amends [ADR-0007](./0007-official-pdf-source-embeds-endorsement-block.md) and the *เกษียน trail* / *Step verbs* / *originator* / *Endorsement block* language in [CONTEXT.md](../../CONTEXT.md).** ADR-0007 defined the embedded endorsement block as **เกษียน trail + Signature block(s)**, rendering an endorsement line for every positive-done gating step (เห็นชอบ) and a signature for every ลงนาม-อนุมัติ. Two requirements from real use change this:

1. **The official document shows *only signatures*, never the routing trail.** Who ตรวจสอบ / พิจารณา / ส่งต่อ a หนังสือ is routing history (kept on the steps + chatter for audit, and visible in the Route), **not** something printed on the letter. A signature block appears only where the acting verb is a *signing* verb.
2. **The drafter is not always the signer.** A เจ้าหน้าที่ธุรการ / งานสารบรรณ may **ร่าง** a หนังสือ and start its route **without signing it**, sending it to a หัวหน้าส่วนงาน who reviews and **ลงนามส่งออก**. The drafter must appear in the Route (their name is in the chain) but carry **no signature** on the document.

Both reduce to one missing axis on the verb: **does this verb render a signature on the official document** — independent of whether it gates the chain, and independent of whether it is the authoritative approval-sign.

## Decision

**Three independent verb axes** (the report previously coupled rendering to `gating`):

- `gating` — must be positively completed for its Stage to pass. *(unchanged)*
- `is_signature` — the **authoritative approval-sign**: closes the ดึงกลับ / ยกเลิกการส่ง window (`has_signed`) and requires signing in the step's Position capacity. **Only ลงนาม-อนุมัติ.** *(unchanged meaning; no longer drives rendering)*
- **`show_signature` (new)** — renders a **signature block** (signature image + ชื่อ + ตำแหน่ง + วันที่ พ.ศ. + the signer's ความเห็น) on the official document. This is the admin-configurable **แสดง / ไม่แสดงลายเซ็น** toggle the requirement asks for.

Invariant: `is_signature ⇒ show_signature` (an authoritative sign always shows).

**The official document renders `show_signature` steps only.** `_signature_block_steps()` = positive-done ∧ `show_signature`. The **เกษียน trail is dropped from the document** — non-signing verbs (ตรวจสอบ / พิจารณา / ส่งต่อ, and a non-signing ผู้จัดทำ) appear in the Route / UI and chatter but render **nothing** on the หนังสือ.

**Seeded verbs** (noupdate; admins may add / relabel):

| verb | gating | show_signature | is_signature | role |
|---|:---:|:---:|:---:|---|
| ลงนามผู้จัดทำ (signing originator) | ✗ | ✓ | ✗ | drafter who signs (common case) |
| **จัดทำ / ร่าง (non-signing originator)** *new* | ✗ | ✗ | ✗ | ธุรการ who drafts, does not sign |
| รับทราบ | ✗ | ✗ | ✗ | for-info |
| เห็นชอบ | ✓ | ✓ | ✗ | endorse — shows a signature, not authority |
| **ตรวจสอบ** *new* | ✓ | ✗ | ✗ | verify — name in Route only |
| **พิจารณา** *new* | ✓ | ✗ | ✗ | consider — name in Route only |
| **ส่งต่อ** *new* | ✗ | ✗ | ✗ | forward — name in Route only |
| ลงนาม-อนุมัติ | ✓ | ✓ | ✓ | authoritative sign = ส่งออก |

**A non-signing drafter needs no engine change.** The originator step's **verb is already editable** and `has_signed` already **excludes the originator**, so:

- Originator with a non-signing verb → the drafter's name is row 1 of the Route, auto-completed at send, with **no signature** on the document.
- The หัวหน้าส่วนงาน is an ordinary downstream **gating ลงนาม-อนุมัติ** step (target = Position). Their signature is the one on the document; completing it closes the recall window and completes / freezes the หนังสือ — this *is* "ลงนามส่งออก".
- The drafter (still the sender) keeps ดึงกลับ / ยกเลิกการส่ง until the head signs, because `has_signed` stays False through a non-signing originator + non-signing checks.

**Send is one act with two faces.** "ส่ง" covers both the drafter pressing send (draft → circulating, submit into the Route) and the final ส่งออก (the authoritative sign completes / freezes the หนังสือ). For an internal บันทึกข้อความ these are the same lifecycle — no new state, no external-agency dispatch feature (หนังสือภายนอก stays phase-2).

**Originator verb is a mandatory per-document default.** Every หนังสือ has an originator step whose verb **defaults to the signing ผู้จัดทำ verb** (preserves today's behaviour) and is **overridable on the form** per document. It is **not** a route-template field — the drafter picks signing vs non-signing on the หนังสือ itself.

## Considered options

- **Reuse `is_signature` for rendering (rejected)** — dropping the new flag and rendering only `is_signature` steps would stop เห็นชอบ from showing a signature (Thai practice shows the endorser's sign); and flipping เห็นชอบ to `is_signature` to compensate would wrongly close the recall window at endorsement. Display and authority are genuinely different axes.
- **Keep a name-only เกษียน line under non-signing steps (rejected)** — an earlier option in this consult. The requirement is explicit: the document shows **signatures only**; the trail belongs in the Route / audit.
- **Route-template `originator_signs` flag (rejected)** — richer, but the signs-or-not choice is per-หนังสือ, every document already carries an originator, and a per-document default + form override is simpler and matches "a default every document must have".

## Consequences

- **Amends ADR-0007:** the embedded `sarabun_endorsement_block` renders **signatures only**, not เกษียน + signatures. It stays self-limiting (empty ⇒ nothing shows; a draft prints no block).
- **CONTEXT.md language to update (docs-first):** *เกษียน trail* (audit-only now — no longer "rendered onto the document"), *Endorsement block* (signatures only), *Step verbs* (the three-axis model + `show_signature` + the new verbs), *ผู้จัดทำ/ผู้ส่ง step* ("auto-completed at send; signs only if its verb is `show_signature`").
- **Engine work (not yet done — docs-only decision):** add `show_signature` to `sarabun.verb` (+ an onchange/constraint enforcing `is_signature ⇒ show_signature`); repoint `_signature_block_steps()` to `show_signature`; seed จัดทำ/ร่าง · ตรวจสอบ · พิจารณา · ส่งต่อ and set `show_signature` on the existing four; keep the originator verb editable + defaulted to the signing verb; update the signature-block QWeb (drop the trail rows, keep the signer's ความเห็น under their own block).
- **Tests:** `test_p5_signing` asserts on `_signature_steps()` / `_kasian_trail_steps()`; update to `show_signature` semantics and add a non-signing-drafter case (name present in the Route, absent from `_signature_block_steps()`, recall still open after send).
- **Pre-production** — the whole stack is on the feature branch, not in `origin/16.0`; no migration of frozen copies or seeded verb data.
