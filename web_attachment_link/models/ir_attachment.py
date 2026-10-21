from urllib.parse import parse_qs, urlsplit

from odoo import api, models
from odoo.exceptions import AccessError


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def get_odoo_link_info(self, url):
        """Describe what an Odoo Link (``/web#…``) points to: ``{name,
        model_label}``, or ``{error: "access" | "missing"}``. The record is read
        with the current user's rights; only the model label is read as sudo,
        since regular users cannot read ``ir.model``."""
        parts = urlsplit(url or "")
        if parts.scheme or parts.netloc or parts.path != "/web":
            return {"error": "missing"}
        params = {key: values[0] for key, values in parse_qs(parts.fragment).items()}
        model = params.get("model")
        if model and (model not in self.env or self.env[model]._abstract):
            return {"error": "missing"}
        model_label = model and self.env["ir.model"]._get(model).sudo().name or ""
        record_id = params.get("id", "")
        if model and record_id.isdigit():
            record = self.env[model].browse(int(record_id)).exists()
            if not record:
                return {"error": "missing"}
            try:
                record.check_access_rights("read")
                record.check_access_rule("read")
                name = record.display_name
            except AccessError:
                return {"error": "access"}
            return {"name": name, "model_label": model_label}
        action = self._get_link_action(params.get("action", ""))
        if not action:
            return {"error": "missing"}
        return {"name": action.name, "model_label": model_label}

    def _get_link_action(self, ref):
        """The action an Odoo Link names by id or by xml id, if any."""
        if ref.isdigit():
            return self.env["ir.actions.actions"].sudo().browse(int(ref)).exists()
        action = ref and self.env.ref(ref, raise_if_not_found=False)
        if action and action._name.startswith("ir.actions."):
            return action.sudo()
        return self.env["ir.actions.actions"]
