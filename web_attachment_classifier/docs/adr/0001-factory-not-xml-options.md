# Classifier binding is done via a JS factory, not XML `options`

Consumers register a widget by calling
`registerAttachmentClassifierWidget({widgetName, classifierField, ...})`
from their own JS asset, then reference `widgetName` in XML. The
Odoo-idiomatic alternative — a single generic widget configured via XML
`options="{'field': ..., 'model': ...}"` — was rejected because
`Many2ManyBinaryField.fieldsToFetch` is a **static per-class contract**
read once at widget-class registration time. Making it dynamic per
instance (i.e. per view) would drop the classifier field out of the
framework's child-record fetch, breaking reactive display of the badge
without an extra manual `orm.read` per render.

## Consequences

- Every consumer needs an `assets` bundle (some, e.g. the original
  `purchase_request_kmitl`, didn't have one — this adds a small amount
  of boilerplate per consumer).
- Adding a new classifier variant requires editing consumer JS, not just
  a view — this is on-purpose. See CONTEXT.md > Factory.
- The factory returns the concrete subclass so tests and downstream
  extensions can subclass further.
