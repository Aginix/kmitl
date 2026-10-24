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
A DR is at exactly one station at a time. _Avoid_: ศูนย์งาน in its `work_center`
ADR-0001 sense (the unit that owns a document for its whole life — the DR's station
moves), โต๊ะของคน, queue.

**การมอบหมาย (Assignment)**: Choosing **which officer inside a station** handles the
DR, once it has arrived there. A separate concern from routing, with its own rules
(`disbursement.assignment.rule`) — routing picks the station, assignment picks the
person. _Avoid_: routing rule, forward.

**Standard route (เส้นทางมาตรฐาน)**: The ordered chain of stations a DR normally
passes through, configured once by an administrator rather than written in code. It is
read live: it is not copied onto each DR, so editing it moves in-flight requests too.
_Avoid_: workflow (that is the DR's own states), route template per document.

**ส่งต่อ (Forward)**: Handing the DR to the **next station on the standard route**.
_Avoid_: approve, submit (those are acts of authority; forwarding is a hand-off).

**Divert (เบี่ยงเส้นทาง)**: Handing the DR to a station that is **not** the next one on
the standard route. The DR is still expected to rejoin the route afterwards — the next
station is then computed from the last on-route station it visited. _Avoid_: ตีกลับ
(that sends work backwards), reassign (that is Assignment, inside one station).

**สมุดเยี่ยม (Visit log)**: The append-only record of every station the DR has entered —
when it arrived, when it left, who moved it and by which act. It is what answers "who
held this last week" and "where does it rejoin the route after a divert"; neither the
station pointer alone nor work center membership can answer either.
_Avoid_: chatter, tracking (those record field changes, not custody).
