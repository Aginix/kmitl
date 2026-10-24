# Work Center (ศูนย์งาน)

A cross-cutting way to divide work inside an organisation by the data on the documents
themselves — "เอกสารที่ส่วนงานผู้ขอเป็นภาควิชาไฟฟ้า เป็นงานของศูนย์งานภาคไฟฟ้า". Each
document is stamped with the unit that owns and follows it, and every work area
(ระบบงาน) gets an overview of its work centers with live counters. Borrowed in spirit
from the MRP work center, but **not** a station a document passes through: a document
stays with its ศูนย์งาน for its whole life.

## Language

**ศูนย์งาน (Work Center)**: The unit that **owns and tracks** a document — whose work it
is and who follows it up — e.g. ศูนย์งานภาควิชาไฟฟ้า, ศูนย์งานการเงินกลาง. A document
has at most one, stored on the document. It does **not** say who acts next: each step is
still done by whoever holds the right for that state. _Avoid_: หน่วยงาน (that is the
Operating Unit), ส่วนงาน (the departments dimension), กลุ่มงาน (a formal org sub-unit),
โต๊ะ, station, team

**ระบบงาน (Work Area)**: The line of work a ศูนย์งาน belongs to — งานการเงิน,
งานงบประมาณ … A ศูนย์งาน belongs to exactly one area and may hold several document types
of that area. Each area has its own overview. A ภาควิชา whose ธุรการ does both การเงิน
and งบประมาณ has two ศูนย์งาน, one per area. _Avoid_: module, app (an area may span
several modules)

**Member (สมาชิก)**: A person who follows a ศูนย์งาน — its card shows on their overview
under "ศูนย์งานของฉัน". Membership is focus only: it grants no access and restricts no
action. _Avoid_: assignee, approver, owner

**หน่วยงาน-level / ส่วนกลาง-level**: A ศูนย์งาน with an Operating Unit is
หน่วยงาน-level: it only ever takes documents of that OU. One without an OU is
ส่วนกลาง-level and takes documents of any OU. The two levels are configuration, not two
kinds of object.

**Routing Rule (กฎการจัดเข้าศูนย์งาน)**: A condition on a document type that puts a
**draft** document onto a ศูนย์งาน. Rules of one document type are tried in order; the
first match wins. Once the document leaves draft, rules never move it again. _Avoid_:
assignment rule (that picks a person)

**Pinned (กำหนดเอง)**: A ศูนย์งาน chosen by hand that differs from what the rules would
give. Rules stop touching a pinned document; clearing its ศูนย์งาน un-pins it.

**Counter (ตัวนับ)**: A number on every card of an area — e.g. "เอกสารรอตรวจสอบ" —
counting that ศูนย์งาน's documents matching a condition, with the viewer's own access,
so it always equals the list it opens.

**ยังไม่มีศูนย์งาน (Unassigned)**: The extra card of each area counting documents no
rule matched. Such documents are never blocked; they just wait here until someone sets
their ศูนย์งาน.

## Relationships

- A **ระบบงาน** has many **ศูนย์งาน** and many **Counters**, plus exactly one
  **ยังไม่มีศูนย์งาน** card.
- A **ศูนย์งาน** has many **Routing Rules**, many **Members** and at most one Operating
  Unit.
- A document has at most one **ศูนย์งาน**; a document and the document it spawns are
  routed independently and may land on the same or different ศูนย์งาน.

## Example dialogue

> **Dev:** "When the ธุรการ sends a request for checking, does it move to the budget
> officer's ศูนย์งาน?" **Domain expert:** "No — the request is ภาคไฟฟ้า's work from
> ส่งตรวจ to จองงบ. The budget officer acts on it by right, but ภาคไฟฟ้า keeps following
> it. Only a wrong ศูนย์งาน gets changed, by hand."

## Flagged ambiguities

- "หน่วยงาน" was used for the level of a ศูนย์งาน; in this repo it means the Operating
  Unit — resolved: the level is _named_ after the OU because it is defined by having
  one.
- "work center" in MRP is a station work flows through — resolved: here it is the owning
  unit, not a station.
