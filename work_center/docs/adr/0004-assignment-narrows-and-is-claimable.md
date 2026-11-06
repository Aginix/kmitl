# Assignment inside a station narrows, and is claimed by pressing a button

**Status: accepted**

A station has several members, and until now a document arriving there reached all of
them: every member got the To-Do and could act or forward, so nobody owned the work. A
station may now name **one assignee** per document (`work_center_assignee_id`), picked
on arrival by the station's **assignment rules** (a domain per document model, like the
routing rules). When there is an assignee, only they act and move the document; any
other responsible person presses **มอบให้ฉัน** (Assign to Me) first, which moves the
arrival To-Do to them and leaves a line in the chatter. A Station Administrator may
hand the document to any responsible person.

## Why

- **Someone must be doing it.** Splitting by ส่วนงาน or fund is how a verification
  section already divides its work; the engine should show who has what instead of
  sending everyone the same To-Do.
- **Work must not get stuck.** Sick leave and absence are routine, so the others can
  take a document over with one press, and nothing is lost: the assignee changes
  hands in the chatter, never silently.
- **Nothing changes where no rule is set.** Without a matching rule there is no
  assignee and the station works as before, so this is a capability of the engine
  every document type gets, not a module to install per document.

## Considered options

- **A fixed lock.** Rejected: the assignee would hold the document even when absent,
  and an administrator would have to step in for every hand-over.
- **A hint only (the To-Do goes to one person, everybody may still act).** Rejected:
  two people can then work on the same document at once and nothing says who has it.
- **A separate module per document type** (the older
  `disbursement_validation_assignment`). Rejected: it assigns when the head signs and
  knows nothing of stations; the engine already knows where the document is.

## Consequences

- Membership says **who may** act; the assignee says **who is** acting. The role gives
  the right, membership narrows it, and the assignee narrows it once more.
- The assignee is cleared whenever the document leaves a station and chosen again on
  the next arrival.
- Only the engine writes the assignee (`_work_center_assign`), as it does the pointer.
- A rule whose person is no longer responsible at the station is skipped, so a change
  of members never leaves a document with someone who cannot act.
