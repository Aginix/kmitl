from odoo import _, api, models
from odoo.tools import format_date, formatLang


class KrisProjectChildTrackingMixin(models.AbstractModel):
    _name = "kris.project.child.tracking.mixin"
    _description = "Mixin for posting child-line changes to parent project chatter"

    _tracking_parent_field = "project_id"
    _tracking_label = ""
    _tracking_fields = set()
    _tracking_monetary_fields = set()

    def _format_tracking_value(self, field_name, value):
        if field_name in self._tracking_monetary_fields:
            return formatLang(
                self.env, value or 0.0, currency_obj=self.currency_id
            )
        field = self._fields.get(field_name)
        if field and field.type == "date":
            return format_date(self.env, value) if value else ""
        if field and field.type in ("many2one",):
            return value.display_name if value else ""
        return str(value) if value else ""

    def _get_tracking_display_name(self):
        return getattr(self, "name", "") or self.display_name

    def _post_to_parent(self, body):
        parent = getattr(self, self._tracking_parent_field, False)
        if parent:
            parent.message_post(body=body, subtype_xmlid="mail.mt_note")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get("skip_message_post"):
            for rec in records:
                parent = getattr(rec, rec._tracking_parent_field, False)
                if parent:
                    body = _("เพิ่ม%(label)s: %(name)s") % {
                        "label": rec._tracking_label,
                        "name": rec._get_tracking_display_name(),
                    }
                    parent.message_post(
                        body=body, subtype_xmlid="mail.mt_note"
                    )
        return records

    def write(self, vals):
        tracked = set(vals) & self._tracking_fields
        old_values = {}
        if tracked and not self.env.context.get("skip_message_post"):
            for rec in self:
                old_values[rec.id] = {f: rec[f] for f in tracked}
        result = super().write(vals)
        for rec in self:
            if rec.id not in old_values:
                continue
            parent = getattr(rec, rec._tracking_parent_field, False)
            if not parent:
                continue
            changes = []
            for field_name, old_val in old_values[rec.id].items():
                new_val = rec[field_name]
                if old_val != new_val:
                    label = rec._fields[field_name].string
                    changes.append(
                        _("%(label)s: %(old)s → %(new)s")
                        % {
                            "label": label,
                            "old": rec._format_tracking_value(
                                field_name, old_val
                            ),
                            "new": rec._format_tracking_value(
                                field_name, new_val
                            ),
                        }
                    )
            if changes:
                body = _("แก้ไข%(label)s %(name)s") % {
                    "label": rec._tracking_label,
                    "name": rec._get_tracking_display_name(),
                }
                body += "<ul>%s</ul>" % "".join(
                    "<li>%s</li>" % c for c in changes
                )
                parent.message_post(body=body, subtype_xmlid="mail.mt_note")
        return result

    def unlink(self):
        messages = []
        if not self.env.context.get("skip_message_post"):
            for rec in self:
                parent = getattr(rec, rec._tracking_parent_field, False)
                if parent:
                    messages.append(
                        (
                            parent,
                            _("ลบ%(label)s: %(name)s")
                            % {
                                "label": rec._tracking_label,
                                "name": rec._get_tracking_display_name(),
                            },
                        )
                    )
        result = super().unlink()
        for parent, body in messages:
            parent.message_post(body=body, subtype_xmlid="mail.mt_note")
        return result
