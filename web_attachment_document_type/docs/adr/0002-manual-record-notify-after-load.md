# Manually call `model.notify()` after `Record.load()` on Odoo 16

After a post-hoc doctype edit we reload the target child record and the parent record so
both the widget badge (`document_type_id` in `fieldsToFetch`) and the chatter
(server-side tracking message from `ir.attachment.write`) reflect the change
immediately. On Odoo 16, `Record.load()` refreshes internal data but does not fire
`model.notify()`, so OWL sees stale references and neither the badge nor the chatter
re-renders until a full page reload.

We call `this.props.record.model.notify()` manually after the two loads to kick the
reactivity system.

## Consequences

- Direct dependency on Odoo 16's reactivity internals; on upgrade to 17+ this line must
  be revisited (may become a no-op or a double-notify).
- The pattern is scoped to `onBadgeClick`; any future flow that mutates an attachment
  out-of-band and expects the widget to refresh must reuse it.
