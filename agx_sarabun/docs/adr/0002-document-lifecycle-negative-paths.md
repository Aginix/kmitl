# Document lifecycle and negative paths

> **Update (2026-07-19 · [ADR-0006](./0006-recall-split-pullback-vs-cancel-send.md)):** two points below are superseded. (1) **Recall** is split — "recall" now means **ดึงกลับ** (pull back to `returned`, *keep* the number, re-send); the terminal cancel-and-void described here is renamed **ยกเลิกการส่ง**. (2) The ตีกลับ **default** destination is now the *previous stage* (chosen by the returner each time), not back-to-sender. The `returned` / `rejected` states and the voiding of `cancelled`/`rejected` numbers remain current.

The old model had only `draft → sent → completed/cancelled`; a rejected document dead-ended in `sent` forever with no way back, and cancellation was blocked entirely after sending. We defined the full lifecycle: `draft → circulating → completed`, plus **`returned`** (revisable; ตีกลับ sends it back to a chosen earlier point — default back-to-sender with the chain restarted, or resume from a picked step), **`rejected`** (terminal — to proceed you duplicate to a new draft, preserving the audit that *this* document was rejected), and **`cancelled`** (เรียกคืน/recall, permitted **only before any ลงนาม-อนุมัติ step has occurred** — after a signature exists the document is part of the record and must be voided via a cancellation หนังสือ). A registered number whose document is rejected or cancelled is **voided**: a permanent gap, never reissued.

## Consequences

- Numbering must support voiding (gap kept, recorded as ยกเลิก) and must not recycle numbers — driven by ระเบียบงานสารบรรณ (official register numbers are not reusable).
- "Recall" depends on whether a signing step has happened, so the engine must track the strongest verb completed so far, not just the document state.
