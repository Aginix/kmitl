# Acts are declared in Python and reflected into records

**Status: proposed** — the two exceptions under _Declared exceptions_ need the product
owner's sign-off; the rest is settled.

The acts a station can allow or require — ตรวจสอบ, อนุมัติ, ตั้งหนี้ … — are **declared in
Python** by the capability module that implements each one (`_work_center_acts` on the
document model, with a code, a name, a kind, a role and the declaring module). A sync
step, run after every install or upgrade (and by hand from the Acts list), **reflects**
the declarations into `work.center.act` records, which stations then list as data. A
code nobody declares any more is **archived, never deleted**: visits reference acts as
audit evidence. An entry of `kind='edit'` is a permission to edit a part of the
document, **not an act**: it can never be required and is never recorded as done.

## Why

- **Stations are data and acts are code.** An act is a method with a role behind it;
  adding a station must never need a new act, and adding a kind of act must never be
  a data edit. Declaring in code keeps the two honest.
- **A module that is not installed contributes no act.** The registry follows what the
  code declares, so uninstalling a capability module cannot leave a station requiring
  something nobody can do: missing and offered acts are computed over the codes the
  code returns **now**, not over the rows.
- **The audit trail must outlive the code.** A visit says "Validate was skipped here".
  Deleting the act row would erase what was skipped, so rows are archived.

## Considered options

- **Seed the acts in XML.** Rejected: a field added to a `noupdate` record never reaches
  an installed database, and an act's name could not follow the languages installed
  after the module.
- **A Selection field whose values are the acts.** Rejected: `ir.model.fields.selection`
  is unreadable to `base.group_user`, so a station card could not show its own acts, and
  a capability module cannot add a selection value without a module of its own.
- **Create the rows in a `post_init_hook`.** Rejected: it runs on install only, so an
  upgrade that adds an act would never reach an installed database.

## Declared exceptions

Both bend the plain rule "the role gives the right, the station narrows" and are
recorded here so a reviewer meets them on purpose.

- **(a) A required act the document declares not applicable is not missing.** A
  document may say an act does not concern it (a request that draws no budget has
  nothing to consume). Forwarding then needs no reason for it, and the visit records
  the act in `not_applicable_act_ids` so the log still shows it was set aside, not
  forgotten.
- **(b) Where nobody else is responsible, the Station Administrators are.** A station
  with neither members nor an active holder of any of its acts' roles — in practice the
  Unassigned card — would hold a document nobody may move. For those only, the
  responsible users fall back to the Station Administrators (`responsible_source =
  fallback`) and only they may move the document. There is **no** manager override on
  a station that has members or role holders.

## Consequences

- Every act has a role. An act without one is offered to nobody; the Acts list flags it.
- The sync writes only when something differs, translates names for every installed
  language, takes an advisory lock so concurrent workers do not race, and never aborts
  the registry load: a failing act is logged and skipped.
- A station is only valid if it offers an act or has someone to hand the work to.
