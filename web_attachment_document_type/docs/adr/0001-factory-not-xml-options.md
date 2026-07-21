# Classifier binding via a JS factory (superseded by ADR-0002)

**Status**: superseded by [ADR-0002](./0002-patched-many2many-binary.md).

Earlier design: each consumer module registered its own widget class via a JS factory
`registerAttachmentClassifierWidget({widgetName, classifierField, ...})`, then
referenced `widgetName` in XML. The Odoo-idiomatic alternative — a single generic widget
configured via XML `options` — was rejected because `Many2ManyBinaryField.fieldsToFetch`
is a static per-class contract and can't be resolved from per-instance `options` without
breaking reactive badge display.

Superseded because we pivoted away from the "per-consumer widget name" model entirely:
the classifier is now a single shared field on `ir.attachment` with scope + ordering
driven by a Mapping table (`ir.attachment.document.type.rel`), and the
`many2many_binary` standard widget itself is patched via `patch()` so no widget name
change is needed anywhere. See ADR-0002 for the current architecture and why.
