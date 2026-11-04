from odoo import api, fields, models


class SarabunDocument(models.Model):
    _inherit = "sarabun.document"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        default=lambda self: self._default_operating_unit_id(),
        index=True,
        tracking=True,
        help="Snapshot at creation: the origin record's OU, else the creator's "
        "default OU. Scopes the type-reader access (ADR-0021).",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "operating_unit_id" not in vals and vals.get("origin_model"):
                ou = self._sarabun_origin_operating_unit(
                    vals["origin_model"], vals.get("origin_res_id")
                )
                if ou:
                    vals["operating_unit_id"] = ou.id
        return super().create(vals_list)

    @api.model
    def _default_operating_unit_id(self):
        # the origin smart button's "New" passes the origin via default_* context
        ctx = self.env.context
        return (
            self._sarabun_origin_operating_unit(
                ctx.get("default_origin_model"), ctx.get("default_origin_res_id")
            )
            or self.env["res.users"].operating_unit_default_get()
        )

    @api.model
    def _sarabun_origin_operating_unit(self, model_name, res_id):
        """OU of the origin record, if it carries ``operating_unit_id``. Override
        for origins whose OU lives elsewhere."""
        OperatingUnit = self.env["operating.unit"]
        model = self.env.get(model_name)
        field = model is not None and model._fields.get("operating_unit_id")
        if not (res_id and field and field.comodel_name == "operating.unit"):
            return OperatingUnit
        return model.sudo().browse(res_id).exists().operating_unit_id or OperatingUnit
