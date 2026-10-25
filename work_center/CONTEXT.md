# Work Center (สถานี)

A cross-cutting way to route the work on a document through a configured chain of
desks. A document sits at one **station** at a time while one step of its handling is
done, then is handed on; every hand-over is written to an append-only log. Each work
area (ระบบงาน) gets an overview of its stations with live counters. Borrowed in spirit
from the MRP work center: a station is a place a document is **passed through**, not
a unit that owns it for life (ADR-0002 supersedes the owning-unit ADR-0001). The
technical name stays `work.center`; the canonical Thai word is **สถานี**.

## Language

**สถานี (Station)**: A desk a document sits at while one step of its handling is done —
e.g. สถานีหมวดตรวจ, สถานีตั้งหนี้. A station is at the level of a **step**, not of a
person: "the document is at สถานีหมวดตรวจ" says nothing about which officer has it. A
document is at exactly one station at a time. A station is a `work.center` record:
stations are configuration, adding one is adding a record. _Avoid_: ศูนย์งาน (the old
name, which carried the owning-unit meaning), โต๊ะของคน, queue, team

**ระบบงาน (Work Area)**: The line of work a station belongs to — งานการเงิน,
งานงบประมาณ … A station belongs to exactly one area and may hold several document types
of that area. Each area has its own overview, and a document model belongs to one
area only. _Avoid_: module, app (an area may span several modules)

**สมาชิกสถานี (Station member)**: Someone who may act on the documents at a station,
but only with acts their role already entitles them to. Membership **narrows, never
grants**: it says "this document at this desk is yours", while the role says "you may
do this kind of act at all". A station with no members is open to everyone holding the
role. Members also forward, divert and send back the documents at their station.
_Avoid_: owner, assignee, approver (a role)

**Route (เส้นทางมาตรฐาน) / Route line**: The ordered chain of stations the documents of
one model normally pass through, configured once rather than written in code, and read
live — editing it moves documents in flight too. A **route line** is one position on
it: it names one or more **candidate stations**, and the **routing rules** choose among
them when there are several. A station appears at most once per route. _Avoid_: step
(a route line is a position, not a step performed), workflow

**Routing Rule (กฎการจัดเข้าสถานี)**: A condition on a document type that chooses which
candidate station of a route line takes the document, evaluated when the document
arrives at that line. Rules of one document type are tried in order; the first match
wins. A station with an operating unit only takes documents of that unit. _Avoid_:
assignment rule (that picks a person)

**ส่งต่อ (Forward)**: Handing the document to the **next station on the route**; out of
the last station it leaves the circuit. _Avoid_: approve, submit (those are acts;
forwarding is a hand-off)

**เบี่ยงเส้นทาง (Divert)**: Handing the document to any other station **of the same
area**, with a reason. The document is expected to rejoin the route afterwards: "next"
is then the station after the last *on-route* station it visited. _Avoid_: ตีกลับ
(that is Send back, which leaves the circuit)

**ส่งคืนผู้จัดทำ (Send back)**: Taking the document out of the circuit, to its maker,
with a reason. Different from divert, which stays inside. _Avoid_: ตีกลับ, reject

**สมุดเยี่ยม (Visit log)**: The append-only record of every station a document has
entered — when it arrived and left, who moved it, by which act, the reason given for a
skipped act, a divert or a send-back, and **who was responsible on arrival** (frozen at
that moment). Who may act is decided live, so the person who acted can be missing from
those responsible: that is evidence the membership changed while the document was
there, not a breach. _Avoid_: chatter, tracking (those record field changes, not
custody)

**การกระทำ (Act)**: Something a station's people do to the document while it sits
there — registered by the capability module that implements it, not by the station:
the station only lists which acts it **allows** and which it **requires** before the
document may be forwarded. A required act can be skipped by forwarding with a reason;
one the document declares not applicable to itself is not missing and is logged as
such. Acts are declared in code and reflected into the registry; they are archived,
never deleted (ADR-0003). _Avoid_: permission (allowing an act at a station gives
nobody the right to perform it), step

**ส่วนที่แก้ไขได้ (Editable part)**: A part of the document a station lets its people
edit while the document is there. It is a permission, **not an act**: it can never be
required and is never recorded as done.

**Counter (ตัวนับ)**: A number on every card of an area — e.g. "รอที่สถานีนี้" —
counting that station's documents matching a condition, with the viewer's own access,
so it always equals the list it opens.

**ยังไม่มีสถานี (Unassigned)**: The extra card of each area counting the documents in
the circuit that no routing rule placed at a station. They wait there, held by nobody,
until a Station Administrator diverts them to a station — the only place where nobody
else is responsible.

## Relationships

- A **ระบบงาน** has many **stations**, **routes** and **Counters**, plus exactly one
  **ยังไม่มีสถานี** card.
- A **route** belongs to one area and one document model, and has ordered **lines**; a
  line has one or more candidate **stations**.
- A **station** has many **Members**, **allowed** and **required acts**, **editable
  parts** and **routing rules**, and at most one Operating Unit.
- A document is at one station; each stay is a **visit**.

## Example dialogue

> **Dev:** "When the officer at สถานีหมวดตรวจ is done, does the document stay in their
> section?" **Domain expert:** "No — they press ส่งต่อ and it moves to the next station
> on the route. If the director finds a missing attachment they divert it back to
> สถานีหมวดตรวจ with the reason, and when it is forwarded again it carries on to the
> station after the last one on the route."

## Flagged ambiguities

- "work center" in MRP is a station work flows through; ADR-0001 used the name for a
  unit that owns a document — resolved: it is a station again (ADR-0002) and the word
  ศูนย์งาน is retired.
- "Member" once meant someone who merely follows a station — resolved: a member may
  act within their role, and members move the documents at their station.
