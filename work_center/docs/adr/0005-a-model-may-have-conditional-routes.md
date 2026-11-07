# A document model may have conditional routes

**Status: accepted**

A model used to have exactly one active route. A route now carries a **condition** (a
domain on the document model) and a sequence. A document takes the first route, in
sequence, whose condition it matches. The route without a condition is the default, and
a model may have at most one.

## Why

- **Some documents of one model follow another path.** A disbursement request that pays
  no money out (an advance clearing) has nothing to do at the payment audit,
  authorisation and pay-out stations. It needs its own chain of stations, not a
  required act declared "not applicable" at every station it then has to be forwarded
  through by hand.
- **It is still configuration.** The finance office draws the second route in the same
  screen as the first. The condition has the same form as a routing rule's, so there is
  nothing new to learn.

## Considered options

- **One route, acts declared not applicable.** Rejected: every station on the way still
  has to forward a document it has nothing to do with.
- **A route chosen in code per model** (an override of `_work_center_route`). Rejected:
  every new path would need a release.

## Consequences

- The route is still read live and never stored on the document. A document whose
  fields change so that it matches another route continues on that route from the
  station it is at. The conditions should therefore use fields that are frozen once the
  document is in the circuit (a disbursement request's payment type, for instance).
- When conditional routes overlap, sequence decides which one a document takes.
