# A ศูนย์งาน is a station a document passes through

**Supersedes [ADR-0001](0001-work-center-is-a-stamped-owning-unit.md).**

A ศูนย์งาน is a **station**: a desk a document sits at while one step of its handling is
done, and leaves when that desk hands it on. A document is at one station at a time; the
station pointer moves — forward to the next station on a configured **route**, or
**diverted** to another — and every move is written to an append-only **visit log**.
Stations offer **acts** (registered by capability modules) and may require some before
the document leaves. **Members** of a station may act on documents there, but only acts
their role already entitles them to: membership narrows authority, it never grants it.

## Why

- **ADR-0001 was validated against one document, and the first real consumer is a
  relay.** The owning-unit reading came from พ.1, which a ภาควิชา raises and follows to
  the end. A ใบขอเบิก is the opposite: หมวดตรวจ, ผอ.กองคลัง, the Rector's delegate and
  the billing desk each hold it for one step and pass it on. What those desks need is a
  queue of what is on their desk now — the thing ADR-0001 explicitly rejected.
- **Most of the module is already right for stations.** Areas, the kanban of cards with
  counters counted under the viewer's rights, the Unassigned card and ordered rules all
  carry over. Counters fit stations better than owners: "how many are waiting at this
  desk" is the question a counter answers.
- **Two meanings of one word is the worst outcome.** Keeping the owning unit in
  `work_center` and putting stations in the disbursement module would leave the repo
  with two concepts named ศูนย์งาน whose glossaries contradict each other on what a
  member may do.

## Considered options

- **Keep ADR-0001 and build stations inside `disbursement_wc`.** Fastest pilot and
  lets ADR-0001's module merge unchanged. Rejected: the pilot would prove an idea about
  one module, not about work centers, and the two "member" definitions would coexist.
- **Close ADR-0001's module and start a station engine from nothing.** Rejected: throws
  away the area, counter, kanban and rule machinery that stations reuse as they are.
- **Both, on every document: an owner field and a station field.** Deferred, not
  rejected. A document that needs both — พ.1 may — can add an owner later; no consumer
  needs it now.

## Consequences

- The mixin's pointer no longer freezes when the document leaves draft: it moves on
  forward and divert. "Pinned" and "routable while draft" disappear with it.
- `member_ids` changes meaning, from focus only to narrowing authority. A station with
  no members is open to everyone holding the role, so installing the module locks no
  one out.
- Routing rules stop deciding a document's single owner and instead choose **which
  station of a kind** takes it — หมวดตรวจ of ส่วนงาน A or of ส่วนงาน B.
- The route, the visit log, the act registry and forward/divert are new, and belong in
  this module so every document can have stations, not only the DR.
- Still true from ADR-0001: the Unassigned card, counters counted with the viewer's own
  rights, and a station with an operating unit only taking documents of that unit.
- The purchase-request bridges built on ADR-0001 (closed PR #1576) assume the owning
  unit and would have to be redone before they are revived.
