# The route is the only control: ordering is recorded, not enforced

A ใบขอเบิก is handled by a configured chain of **สถานี**. Which station it is at is a
decision people make — ส่งต่อ to the next station on the standard route, or **divert**
to another one. A station may declare the **method ที่ต้องทำ** before the DR leaves it,
but that check is **overridable with a reason**, which is written to the สมุดเยี่ยม.

There is no second, harder guarantee behind it. Nothing in code prevents a DR from
being approved by ผอ.กองคลัง without ever having been checked by หมวดตรวจ, or from
being billed before it was approved. The route says what normally happens; the visit
log says what actually happened.

## Why

- **The people doing the work need a way out.** A hard ordering guard means a DR can
  reach a state where the only escape is a developer or an administrator with raw
  write access. KMITL's disbursement desks hit that today.
- **Ordering was already soft in practice.** The desk that is supposed to check a DR
  can approve it without reading it; the guarantee that was enforced was only that a
  *button had been pressed*, not that work had been done.
- **The audit answer moves rather than disappears.** What a reviewer needs is "who had
  it, when, and who moved it where" — which the สมุดเยี่ยม answers directly and the
  old state machine never did. An out-of-order DR is visible in the log, with the
  reason its mover typed.

## Considered options

- **Keep the state machine's ordering guard** (`state == 'verified'` before the first
  approval, `approval_state` before the second). This is what the code does today, and
  it is a real guarantee: approving an unchecked DR is impossible, not merely logged.
  Rejected: it is the guard that makes the DR's middle a fixed sequence, and a
  configurable route of stations is the point of this design. Keeping both means the
  route may never disagree with the state machine, which makes the route decorative.
- **Split the two — logistics overridable, authority not** (where the DR sits is a
  decision; the order of approvals is not, enforced through the surviving
  `approval_state`). Rejected: it preserves the ordering guarantee at the cost of
  keeping one workflow in code and one in configuration, and of deciding case by case
  which acts are "authority".
- **Per-method prerequisites declared as data, not overridable.** Rejected for now as
  a second rule engine on top of the route, with no operational experience behind it.

## Consequences

- Every ordering guard written against `state` is removed, not ported. The methods
  keep only the checks that protect their own integrity (a bill cannot be raised
  twice), not the checks that protect their place in a sequence.
- A DR can arrive at a station whose method it is not ready for. The station's people
  handle it by diverting it back — that is the designed flow, not an error.
- The สมุดเยี่ยม becomes evidence, not convenience: if it is incomplete, nothing else
  can reconstruct what happened. It must record the override reason, the mover and the
  act, and it must be append-only.
- Anyone who can press ส่งต่อ can route a DR anywhere the route configuration allows,
  so who may press it is now a real security question, separate from who may approve.
- This is a control the organisation's auditors may ask about. The answer must be the
  log, and the log has to be readable by someone who is not a developer.
