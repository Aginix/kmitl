from odoo import api, fields, models


class IrAttachmentAnnotation(models.Model):
    _inherit = "ir.attachment.annotation"

    # ------------------------------------------------------------------
    # Event log
    # ------------------------------------------------------------------

    def _history_snapshot(self):
        self.ensure_one()
        return {
            "page": self.page,
            "kind": self.kind,
            "geometry": self.geometry,
            "color": self.color,
            "text": self.text or "",
        }

    def _history_event_values(self, operation, before=None, after=None):
        self.ensure_one()
        return {
            "attachment_id": self.attachment_id.id,
            "annotation_id": self.id,
            # Sent by the viewer with every call of one visit.
            "session_key": self.env.context.get("annotation_session"),
            "operation": operation,
            "user_id": self.env.uid,
            "before": before,
            "after": after,
        }

    def _history_log(self, vals_list):
        if vals_list:
            self.env["ir.attachment.annotation.event"].sudo().create(vals_list)

    @api.model_create_multi
    def create(self, vals_list):
        annotations = super().create(vals_list)
        annotations._history_log(
            [
                annotation._history_event_values(
                    "add", after=annotation._history_snapshot()
                )
                for annotation in annotations
            ]
        )
        return annotations

    def write(self, vals):
        before = {annotation.id: annotation._history_snapshot() for annotation in self}
        res = super().write(vals)
        events = []
        for annotation in self:
            after = annotation._history_snapshot()
            if after != before[annotation.id]:
                events.append(
                    annotation._history_event_values(
                        "change", before=before[annotation.id], after=after
                    )
                )
        self._history_log(events)
        return res

    def unlink(self):
        self._history_log(
            [
                annotation._history_event_values(
                    "remove", before=annotation._history_snapshot()
                )
                for annotation in self
            ]
        )
        return super().unlink()

    # ------------------------------------------------------------------
    # RPC used by the photo viewer
    # ------------------------------------------------------------------

    @api.model
    def annotation_history(self, attachment_id):
        """Return the Changes made to the layer of the attachment, oldest
        first; each lists its events in the order they happened."""
        attachment = self._get_readable_attachment(attachment_id)
        events = (
            self.env["ir.attachment.annotation.event"]
            .sudo()
            .search([("attachment_id", "=", attachment.id)])
        )
        changes = {}
        for event in events:
            key = event.session_key or "event-%s" % event.id
            change = changes.setdefault(
                key, {"key": key, "user_name": event.user_id.name, "events": []}
            )
            change["date"] = fields.Datetime.to_string(event.date)
            change["events"].append(
                {
                    "annotation_id": event.annotation_id,
                    "operation": event.operation,
                    "date": fields.Datetime.to_string(event.date),
                    "before": event.before,
                    "after": event.after,
                }
            )
        return sorted(changes.values(), key=lambda change: change["date"])
