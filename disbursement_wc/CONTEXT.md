# Disbursement Work Center (สถานีงานใบขอเบิก)

Routing the **work** on a ใบขอเบิก (DR) through a configured chain of desks. The DR's
own state no longer says which step it is at — the **station** does. Decisions
captured during design; this file is a glossary, not a specification.

> **Status: design in progress.** The terms below are settled. The DR's state machine,
> the authority model and the migration are not. This context supersedes
> `work_center` ADR-0001's "owning unit" reading for the DR — that ADR has not been
> rewritten yet.

## Language

**สถานี (Station)**: A desk the DR sits at while one step of its handling is done —
สถานีหมวดตรวจ, สถานี ผอ.กองคลัง, สถานีตั้งหนี้. A station is at the level of a **step**,
not of a person: "the DR is at สถานีหมวดตรวจ" says nothing about which officer has it.
A DR is at exactly one station at a time. A station is also only ever a place where a person
acts **on the DR**: a step performed on another document is not a station.
_Avoid_: ศูนย์งาน in its `work_center` ADR-0001 sense (the unit that owns a document for
its whole life — the DR's station moves), โต๊ะของคน, queue.

**วงจร (Circuit)**: The stretch of a DR's life that stations route, from หมวดตรวจ to
อนุมัติจ่าย. A station exists only where a **person presses something on the DR itself**;
the steps whose act happens on another document (posting the bill, closing the
e-payment file, posting the JV) are outside the circuit and belong to the
ขั้นการชำระ. Leaving the circuit backwards — sending the DR to its maker to fix —
returns it to ฉบับร่าง and is a different act from Divert, which stays inside.
_Avoid_: workflow, lifecycle (the DR has more life than the circuit).

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

**สมาชิกสถานี (Station member)**: Someone who may act on a DR while it sits at that
station — but only the acts their role already entitles them to. Membership **narrows,
never grants**: it says "this DR at this desk is yours", while the role says "you may
approve DRs at all". A station with no members is open to everyone holding the role.
Members are also the people who forward and divert a DR from their station.
_Avoid_: approver (a role), assignee (Assignment picks one member), Member in the
`work_center` sense (focus only — see Flagged ambiguities).

**การมอบหมาย (Assignment)**: Choosing **which officer inside a station** handles the
DR, once it has arrived there. A separate concern from routing, with its own rules
(`disbursement.assignment.rule`) — routing picks the station, assignment picks the
person. _Avoid_: routing rule, forward.

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

- **Member** — `work_center/CONTEXT.md` defines a member as someone who merely
  *follows* a ศูนย์งาน ("grants no access and restricts no action"). Here a station
  member is someone who may *act*, within their role. Resolved for the DR in favour of
  acting; the `work_center` glossary is still to be rewritten.
