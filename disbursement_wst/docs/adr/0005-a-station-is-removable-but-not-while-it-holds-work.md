# A station is removable, but not while it holds work

The glossary promises that removing a station is uninstalling its module. The
engine did not keep that promise: `disbursement.step.station_id` was
`ondelete="restrict"`, so one request having ever passed a station was enough to
make its module permanently un-uninstallable.

## Decision

**The journey survives the station.** A step carries its own frozen copy of what
it needs to stay readable — `station_code`, `station_name`, `is_signature` — written
when the step is created, not derived. `station_id` is `ondelete="set null"`: a live
pointer while the station exists, nothing the history depends on. This is disbursement
ADR-0002's snapshot rule (who signed, frozen at signing) carried from *who* to *where*.

**Work in progress blocks the uninstall.** The station module's `uninstall_hook`
counts the steps still `active` at its station and raises with the requests named.
Nothing is skipped on the operator's behalf: clearing them is a human act, done with
the *send to station* button, and it leaves a trail. An uninstall that silently
advanced seventeen requests past a control step would be the kind of thing nobody
discovers until an audit.

**Config dies with the station; history does not.** `disbursement.route.line.station_id`
is `ondelete="cascade"` — a route line naming a station that no longer exists is
meaningless, and leaving it would block the uninstall for no reason.

**Stations are `noupdate="0"`, routes are `noupdate="1"`.** A station is code: nobody
may edit it (the ACL is read-only even for managers), so there is no user edit to
protect and renaming one must actually reach an installed database. A route is
configuration: an admin's ordering must survive an upgrade.

## Considered options

- **Keep the station record alive past uninstall** (seed it from a hook rather than a
  data file) — rejected: it leaves a row with no module behind it, still offered in the
  route editor, and its `group_id` points at a group the uninstall deleted anyway.
- **Let the uninstall skip the parked requests** — rejected above.

## Consequences

- Anything a step must still show after an uninstall has to be denormalised onto it.
  `is_signature` is the easy one to forget: the printed signature block filters on it,
  so leaving it as a reach through `station_id` would quietly drop a signature cell
  from every reprinted ใบขอเบิก.
- Removing a mid-flow station is a two-step operation — move the parked requests on,
  then uninstall — and that is the intended cost.
