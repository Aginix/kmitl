# Disbursement Stations (สถานีของใบขอเบิก)

Routing the **work** on a ใบขอเบิก (DR) through a configured chain of desks. The DR's
own state no longer says which step it is at — the **station** does. Decisions
captured during design; this file is a glossary, not a specification.

> **Status: built.** Stations are `work.center` records: the station engine lives in
> `work_center` (its ADR-0002, which supersedes the "owning unit" ADR-0001), and this
> module only plugs the DR into it. The act modules (`disbursement_validation`,
> `disbursement_endorser_director`, `disbursement_approver_rector`,
> `disbursement_budget`, `disbursement_accounting_kmitl`,
> `disbursement_finance_kmitl`) contribute the acts; the terms for every one of them
> are defined here.

## Language

**สถานี (Station)**: A desk the DR sits at while one step of its handling is done —
สถานีหมวดตรวจ, สถานี ผอ.กองคลัง, สถานีตั้งหนี้. A station is at the level of a **step**,
not of a person: "the DR is at สถานีหมวดตรวจ" says nothing about which officer has it.
A DR is at exactly one station at a time. A station is also only ever a place where a person
acts **on the DR**: a step performed on another document is not a station.
_Avoid_: ศูนย์งาน (the old name, which still carries work_center ADR-0001's meaning of
a unit that owns a document for life — a station is passed through), โต๊ะของคน, queue.

**วงจร (Circuit)**: The stretch of a DR's life that stations route, from หมวดตรวจ to
อนุมัติจ่าย. A station exists only where a **person presses something on the DR itself**;
the steps whose act happens on another document (posting the bill, closing the
e-payment file, posting the JV) are outside the circuit and belong to the
ขั้นการชำระ. Leaving the circuit backwards — sending the DR to its maker to fix —
returns it to ฉบับร่าง and is a different act from Divert, which stays inside. When the
maker sends it again it re-enters at the **first station of the route**, without a new
head-of-department signature: a correction is checked again from the start, but is not
circulated through e-Saraban a second time. A desk that only needs something small
fixed should divert to the station that can fix it instead of sending the DR back. Leaving
it forwards — out of the last station — makes the DR **เสร็จสิ้น (done)**: every desk has
done its part. That says nothing about the money, which the ขั้นการชำระ tracks on its
own. _Avoid_: workflow, lifecycle (the DR has more life than the circuit), "done means
paid".

**ขั้นการชำระ (Settlement stage)**: The DR's second axis — none → billed → settled →
booked — saying how far the money has got. It is **derived from the bills and vouchers
that actually exist**, never written by anyone, so it walks back by itself when a bill
is reverted or a cheque is cancelled. The station says who holds the work; the
ขั้นการชำระ says where the money is. _Avoid_: สถานะ / state (that is the DR's own and
no longer tracks progress), pipeline_status (the mirrored field it replaces).

**การกระทำ (Act)**: Something a station's people do to the DR while it sits there —
ตรวจสอบ, เห็นชอบ, อนุมัติ, ตั้งหนี้ … Each act is contributed by the capability that
implements it, not by the station: the station only lists which acts it **allows** (the
ones offered there) and which it **requires** before the DR may be forwarded. A required
act can be skipped by forwarding with a reason. Adding a station never needs a new act;
adding a kind of act does. _Avoid_: method (the developer's word for it), permission
(allowing an act at a station does not give anyone the right to perform it), step.

**ส่วนที่แก้ไขได้ (Editable part)**: A part of the DR a station lets its people edit —
the header, the lines, the attachments, the dimensions, the budget code. It is a
permission, not an act: it is never required before forwarding and never recorded as
done. It closes for good once the money has started (the ขั้นการชำระ is past none).
_Avoid_: Act (nothing is "done" by editing), field-level security.

**แถบสถานี (Station bar)**: The strip under the DR's header that shows where the DR is
on its route (the stations passed, the one holding it, those still to come), who is
responsible there, the acts still to do, and the moves out of the station: ส่งต่อ,
เบี่ยงเส้นทาง, ส่งคืนผู้จัดทำ. Only the area's station people see it (and the visit log):
the members of its stations, the holders of the roles of the acts they allow, and the
station administrators. The maker follows the DR by its state. _Avoid_: กล่องสถานี,
station box.

**The acts** (การกระทำของใบขอเบิก): each is declared by the module that implements it
and stamps who did it.
- **ตรวจสอบ (Validate)** — the officer checks the signed request
  (`disbursement_validation`, `verifier_id`). Not `assigned_to`, who was merely
  assigned the check.
- **เห็นชอบ (ผอ.กองคลัง)** — the Finance Division Director's endorsement; the
  Director holds no authority to approve (`disbursement_endorser_director`).
- **อนุมัติ (ผู้รับมอบอำนาจอธิการบดี)** — the Rector-delegated approver's approval
  (`disbursement_approver_rector`). It touches no budget.
- **ตัดงบประมาณ (Consume budget)** — consumes the linked commitment or, for a direct
  claim, draws on the pool (`disbursement_budget`). A DR that draws no budget does
  not need it: the act is *not applicable* to it.
- **ตั้งหนี้ (Create bill)**, **ตรวจจ่าย (Audit payment)**, **อนุมัติจ่าย (Authorize
  payment)** — the money acts (`disbursement_accounting_kmitl`,
  `disbursement_finance_kmitl`). They act on the DR, while the bill and the payment
  they lead to are other documents: the ขั้นการชำระ follows those.

No act needs another first and none changes the DR's state. The station route says
in which order they are expected, and records what was skipped and why.
_Avoid_: Step, approval state.

**สมาชิกสถานี (Station member)**: Someone who may act on a DR while it sits at that
station — but only the acts their role already entitles them to. Membership **narrows,
never grants**: it says "this DR at this desk is yours", while the role says "you may
approve DRs at all". A station with no members is open to everyone holding the role.
Members are also the people who forward and divert a DR from their station.
_Avoid_: approver (a role), Member in the
`work_center` sense (focus only — see Flagged ambiguities).

**การมอบหมาย (Assignment)**: Choosing **which officer inside a station** handles the
DR, once it has arrived there. A separate concern from routing, with its own rules —
the station's **Assignment Rules** (`work_center`) — routing picks the station,
assignment picks the person, and the other people of the station take the DR over with
**Assign to Me**. _Avoid_: routing rule, forward.

**Standard route (เส้นทางมาตรฐาน)**: The ordered chain of stations a DR normally
passes through, configured once by an administrator rather than written in code.
Stations themselves are configuration too: adding a station is adding a record, not
installing a module. It is
read live: it is not copied onto each DR, so editing it moves in-flight requests too.
_Avoid_: workflow (that is the DR's own states), route template per document.

**ส่งต่อ (Forward)**: Handing the DR to the **next station on the standard route**.
_Avoid_: approve, submit (those are acts of authority; forwarding is a hand-off).

**Divert (เบี่ยงเส้นทาง)**: Handing the DR to a station that is **not** the next one on
the standard route. The DR is still expected to rejoin the route afterwards — the next
station is then computed from the last on-route station it visited. _Avoid_: ตีกลับ
(that sends work backwards), reassign (that is Assignment, inside one station).

**สมุดเยี่ยม (Visit log)**: The append-only record of every station the DR has entered —
when it arrived, when it left, who moved it, by which act, the reason given for any
skipped required act, and **who was responsible when it arrived** (the station's members
at that moment, frozen). Who may act is still decided live, so the person who acted may
be missing from those responsible: that is evidence the station's membership changed
while the DR was there, not a breach. It is what answers "who held this last week" and
"where does it rejoin the route after a divert"; neither the station pointer alone nor
the current membership can answer either.
_Avoid_: chatter, tracking (those record field changes, not custody).

## Flagged ambiguities

- **Member** — resolved: a station member is someone who may *act*, within their role,
  for every document (a station *is* a `work.center`, work_center ADR-0002). The old
  "member follows a ศูนย์งาน" reading is gone from `work_center/CONTEXT.md` too.
